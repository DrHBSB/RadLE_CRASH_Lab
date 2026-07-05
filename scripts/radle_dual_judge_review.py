#!/usr/bin/env python
"""
RadLE v2 -- dual-judge binary diagnosis scorer with human-authority tier.

Standalone. Does NOT touch scripts/radle_llm_judge.py (the existing single-judge
GLM pipeline in the radle_v2_stats package). This runner implements the
three-tier design agreed for the disagreement-review workflow:

  1. HUMAN AUTHORITY  -- exact (case, normalized-diagnosis) match to the blinded
                         radiologist RSNA key -> take the human 0/1. No API call.
  2. AUTO-ZERO        -- score_required == False (abstained / technical_failure) -> 0.
  3. DUAL JUDGE       -- everything else: score with two OpenRouter models
                         (Gemini 3.1 Pro + GLM 5.2). Agree -> locked.
                         Disagree / parse-error / human-conflict -> NEEDS_REVIEW.

Output: an .xlsx with tabs `scored`, `needs_review`, `summary`.
Judge calls are deduped by (model, case, normalized-diagnosis) and cached to a
JSONL so an interrupted run resumes for free.

Usage:
  python scripts/radle_dual_judge_review.py --verify-key
  python scripts/radle_dual_judge_review.py --dry-run          # tiers 1+2 only, no API
  python scripts/radle_dual_judge_review.py --limit 20         # judge only 20 unique pairs
  python scripts/radle_dual_judge_review.py                    # full run
"""
from __future__ import annotations
import argparse, json, os, re, sys, time, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import requests

# ---------------------------------------------------------------- config -----
PROJECT   = Path(r"C:/Users/thehb/Documents/RadLE v2")
INPUT_CSV = PROJECT / "outputs/radle_v2_stats/long_format_diag_likert_blinded_combined.csv"
CANDIDATE_KEY = PROJECT / "outputs/radle_v2_stats/blinding_key_blinded_combined.csv"
HUMAN_KEY = Path(r"C:/Users/thehb/Documents/RadLE Stats/RadLE_RSNA_Diagnosis_Scoring_key.csv")
ENV_FILE  = PROJECT / "radle_api_keys.env"
OUT_XLSX  = PROJECT / "outputs/radle_v2_stats/radle_v2_dual_judge_scored_combined.xlsx"
# Cache is keyed on (judge_model, case, normalized_diagnosis) -- NOT on candidate label --
# so reusing the same cache file from the 18-model run gives free hits on every AI
# candidate row here (their diagnosis text is unchanged, only relabeled A..R). Only the
# 12 new human-radiologist candidates (S..AD) and remapped rows need fresh judge calls.
CACHE     = PROJECT / "outputs/radle_v2_stats/dual_judge_cache.jsonl"

# OpenRouter model slugs (verified against /api/v1/models)
JUDGES = {
    "gemini": "google/gemini-3.1-pro-preview",
    "glm":    "z-ai/glm-5.2",
}
KEY_NAMES = ["OPENROUTER_API_KEY", "TEST_OPENROUTER_API_KEY"]  # tried in order
OR_BASE   = "https://openrouter.ai/api/v1"
HUMAN_MODEL_COLS = list("ABCDEFGHIJ")  # Diagnosis_Model_A .. Score_Model_J

SYSTEM_PROMPT = (
    "You are an expert radiologist adjudicating an AI diagnosis benchmark. For each case you are\n"
    "given a REFERENCE (ground-truth) diagnosis and a CANDIDATE diagnosis produced by a model.\n"
    "Decide whether the candidate is correct: score 1 (match) or 0 (no match). Judge text-to-text\n"
    "only; you are not shown the image. Reward correct identification of the PRINCIPAL diagnosis;\n"
    "be robust to wording, not to meaning.\n\n"
    "Score 1 when the candidate names the same disease/entity as the reference, including when it\n"
    "differs only in:\n"
    "- Synonyms, eponyms, or descriptive equivalents (Kienbock disease = avascular necrosis of the\n"
    "  lunate; Lhermitte-Duclos disease = dysplastic cerebellar gangliocytoma; acromioclavicular\n"
    "  dislocation = AC joint separation; acoustic neuroma = vestibular schwannoma).\n"
    "- Abbreviation vs full form (CCF = carotid cavernous fistula; OPLL = ossification of the\n"
    "  posterior longitudinal ligament).\n"
    "- Spelling, plurals, word order, or minor typos. The REFERENCE itself may contain typos --\n"
    "  interpret the intended diagnosis.\n"
    "- A CORRECT extra qualifier or greater specificity (reference 'osteogenesis imperfecta' vs\n"
    "  candidate 'osteogenesis imperfecta type II'; reference 'SCFE' vs 'left SCFE').\n"
    "- Naming the correct specific subtype when the reference is general, OR the correct general\n"
    "  entity when the reference names a subtype -- provided it is the principal diagnosis\n"
    "  (reference 'jejunal intussusception' vs candidate 'intussusception'; reference 'diabetic\n"
    "  foot with osteomyelitis' vs candidate 'osteomyelitis').\n\n"
    "Score 0 when:\n"
    "- The candidate names a DIFFERENT disease/entity, even in the same organ, system, or imaging\n"
    "  pattern (pectus excavatum vs pectus carinatum -> 0).\n"
    "- The candidate adds an INCORRECT qualifier that makes it factually wrong: wrong laterality,\n"
    "  a wrong 'bilateral', or a wrong subtype (unilateral 'intraosseous lipoma' vs candidate\n"
    "  'bilateral ... lipomas' -> 0).\n"
    "- The candidate is a non-answer: 'I don't know', blank, API_ERROR, PARSE_FAILED, or off-topic.\n"
    "- The candidate captures only a secondary/incidental part of a compound reference and misses\n"
    "  the principal diagnosis.\n\n"
    "Principal-diagnosis rule: if the reference lists several findings, identify the single\n"
    "principal pathology the case turns on, and score 1 only if the candidate captures THAT.\n\n"
    "Calibration and self-flagging: be decisive, but set 'confidence':'low' and\n"
    "'flag_for_review':true when the reference is vague or finding-level rather than a specific\n"
    "diagnosis (e.g. 'abdominal trauma', 'hypoxic injury'), when equivalence hinges on specialist\n"
    "knowledge you are unsure of, or when it is a genuine near-miss. Do not reward verbosity or\n"
    "hedging -- judge the diagnostic content only.\n\n"
    "Output ONLY a JSON object, no prose:\n"
    '{"score": 0 or 1, "matched_entity": "<reference entity you judged against>", '
    '"reason": "<=25 words", "confidence": "high|medium|low", "flag_for_review": true|false}'
)

# ------------------------------------------------------------- utilities -----
def norm(s) -> str:
    if pd.isna(s):
        return ""
    s = str(s).lower().strip().replace("-", " ")
    s = re.sub(r"[^a-z0-9 ]", "", s)
    return re.sub(r"\s+", " ", s).strip()

def load_env() -> dict:
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    for k in KEY_NAMES:
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env

def get_key(env: dict):
    for k in KEY_NAMES:
        if env.get(k):
            return env[k]
    return None

def verify_key(key: str) -> bool:
    try:
        r = requests.get(f"{OR_BASE}/key", headers={"Authorization": f"Bearer {key}"}, timeout=30)
    except Exception as e:
        print(f"  key check failed: {e}")
        return False
    print(f"  /key status {r.status_code}: {r.text[:150]}")
    return r.status_code == 200

def extract_json(text: str):
    if not text:
        return None
    t = text.strip()
    t = re.sub(r"^```(?:json)?", "", t, flags=re.IGNORECASE).strip()
    t = re.sub(r"```$", "", t).strip()
    i, j = t.find("{"), t.rfind("}")
    if i == -1 or j == -1 or j < i:
        return None
    try:
        return json.loads(t[i : j + 1])
    except Exception:
        return None

def coerce_verdict(d):
    if not isinstance(d, dict):
        return {"score": None, "matched_entity": "", "reason": "parse_error",
                "confidence": "low", "flag_for_review": True}
    sc = d.get("score")
    try:
        sc = 1 if int(sc) == 1 else 0
    except Exception:
        sc = None
    return {
        "score": sc,
        "matched_entity": str(d.get("matched_entity", ""))[:200],
        "reason": str(d.get("reason", ""))[:300],
        "confidence": str(d.get("confidence", "")).lower()[:10],
        "flag_for_review": bool(d.get("flag_for_review", False)),
    }

# --------------------------------------------------------------- judging -----
class Judge:
    def __init__(self, key: str, max_retries=6, timeout=90):
        self.key, self.max_retries, self.timeout = key, max_retries, timeout
        self.lock = threading.Lock()
        self.cache = {}
        if CACHE.exists():
            for line in CACHE.read_text(encoding="utf-8").splitlines():
                try:
                    r = json.loads(line)
                    self.cache[(r["model"], r["case"], r["nd"])] = r["verdict"]
                except Exception:
                    pass

    def _persist(self, model, case, nd, verdict):
        with self.lock:
            self.cache[(model, case, nd)] = verdict
            with open(CACHE, "a", encoding="utf-8") as f:
                f.write(json.dumps({"model": model, "case": int(case),
                                    "nd": nd, "verdict": verdict}) + "\n")

    def _post(self, model, user, use_json=True):
        body = {"model": model, "temperature": 0,
                "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                             {"role": "user", "content": user}]}
        if use_json:
            body["response_format"] = {"type": "json_object"}
        return requests.post(f"{OR_BASE}/chat/completions",
                             headers={"Authorization": f"Bearer {self.key}",
                                      "Content-Type": "application/json"},
                             json=body, timeout=self.timeout)

    def score_pair(self, model, case, nd, gt, diagnosis):
        hit = self.cache.get((model, case, nd))
        if hit is not None:
            return hit
        user = (f"REFERENCE diagnosis: {gt}\nCANDIDATE diagnosis: {diagnosis}\n"
                "Return the JSON verdict.")
        use_json = True
        for attempt in range(self.max_retries):
            try:
                r = self._post(model, user, use_json)
                if r.status_code == 200:
                    content = r.json()["choices"][0]["message"]["content"]
                    verdict = coerce_verdict(extract_json(content))
                    if verdict["score"] is None and use_json:
                        use_json = False
                        continue
                    self._persist(model, case, nd, verdict)
                    return verdict
                if r.status_code == 400 and "response_format" in r.text.lower():
                    use_json = False
                    continue
                if r.status_code in (408, 429) or r.status_code >= 500:
                    time.sleep(2 ** attempt)
                    continue
                raise RuntimeError(f"{model} HTTP {r.status_code}: {r.text[:200]}")
            except requests.RequestException:
                time.sleep(2 ** attempt)
        v = {"score": None, "matched_entity": "", "reason": "api_failed",
             "confidence": "low", "flag_for_review": True}
        self._persist(model, case, nd, v)
        return v

# ----------------------------------------------------------- human lookup ----
def build_human_lut() -> dict:
    key = pd.read_csv(HUMAN_KEY, encoding="latin-1")
    triples = []
    for m in HUMAN_MODEL_COLS:
        dc, sc = f"Diagnosis_Model_{m}", f"Score_Model_{m}"
        if dc in key.columns and sc in key.columns:
            t = key[["Master_Case_ID", dc, sc]].copy()
            t.columns = ["case", "diagnosis", "hscore"]
            triples.append(t)
    h = pd.concat(triples, ignore_index=True)
    h["nd"] = h["diagnosis"].map(norm)
    h = h[(h["nd"] != "") & h["hscore"].notna()]
    lut = {}
    for (case, nd), grp in h.groupby(["case", "nd"]):
        vals = set(int(x) for x in grp["hscore"])
        lut[(int(case), nd)] = {"score": next(iter(vals)), "conflict": len(vals) > 1}
    return lut

# ----------------------------------------------------------------- main ------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="tiers 1+2 only, no API calls")
    ap.add_argument("--verify-key", action="store_true", help="check the OpenRouter key and exit")
    ap.add_argument("--limit", type=int, default=0, help="judge at most N unique pairs (smoke test)")
    ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--review-on-flag", action="store_true",
                    help="also route agreeing rows to review if either judge flagged")
    args = ap.parse_args()

    env = load_env()
    key = get_key(env)

    if args.verify_key:
        if not key:
            print("No OpenRouter key found in env."); sys.exit(1)
        sys.exit(0 if verify_key(key) else 2)

    df = pd.read_csv(INPUT_CSV)
    df["nd"] = df["diagnosis"].map(norm)
    if CANDIDATE_KEY.exists():
        ckey = pd.read_csv(CANDIDATE_KEY)[["model_blinded", "model_key", "provider"]]
        df = df.merge(ckey, on="model_blinded", how="left")
    lut = build_human_lut()
    print(f"[load] {len(df)} rows | human LUT {len(lut)} pairs "
          f"({sum(v['conflict'] for v in lut.values())} conflicting)")

    def human_hit(row):
        return lut.get((int(row["Master_Case_ID"]), row["nd"]))

    df["human_match"] = df.apply(lambda r: human_hit(r) is not None, axis=1)
    df["human_score_lookup"] = df.apply(lambda r: (human_hit(r) or {}).get("score"), axis=1)
    df["human_conflict"] = df.apply(lambda r: (human_hit(r) or {}).get("conflict", False), axis=1)

    needs_judge = df[(df["score_required"] == True) & (~df["human_match"])].copy()
    uniq = (needs_judge[["Master_Case_ID", "nd", "Ground_Truth_Diagnosis", "diagnosis"]]
            .drop_duplicates(subset=["Master_Case_ID", "nd"]))
    if args.limit:
        uniq = uniq.head(args.limit)
    print(f"[tiers] human={int(df['human_match'].sum())} "
          f"auto_zero={int((df['score_required']==False).sum())} "
          f"judge_rows={len(needs_judge)} unique_pairs={len(uniq)}")

    verdicts = {}
    if not args.dry_run and len(uniq):
        if not key:
            print("ERROR: no OpenRouter key; cannot run judges. Use --dry-run or add a key.")
            sys.exit(1)
        if not verify_key(key):
            print("ERROR: OpenRouter key rejected (see status above). Aborting.")
            sys.exit(2)
        judge = Judge(key)
        tasks = []
        for _, r in uniq.iterrows():
            for name, slug in JUDGES.items():
                tasks.append((name, slug, int(r["Master_Case_ID"]), r["nd"],
                              r["Ground_Truth_Diagnosis"], r["diagnosis"]))
        done = 0
        with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
            fut = {ex.submit(judge.score_pair, slug, case, nd, gt, dg): (name, case, nd)
                   for (name, slug, case, nd, gt, dg) in tasks}
            for f in as_completed(fut):
                name, case, nd = fut[f]
                verdicts.setdefault((case, nd), {})[name] = f.result()
                done += 1
                if done % 50 == 0 or done == len(tasks):
                    print(f"  judged {done}/{len(tasks)} calls", flush=True)

    def adjudicate(row):
        cols = ["gemini_score","gemini_matched_entity","gemini_reason","gemini_confidence","gemini_flag",
                "glm_score","glm_matched_entity","glm_reason","glm_confidence","glm_flag",
                "agreement","final_score","review_status","review_reason","final_resolved"]
        out = {c: "" for c in cols}
        if row["score_required"] != True:
            out.update(final_score=0, review_status="LOCKED (auto)",
                       review_reason="auto_zero", final_resolved=0)
            return pd.Series(out)
        if row["human_match"]:
            if row["human_conflict"]:
                out.update(review_status="NEEDS_REVIEW", review_reason="human_conflict")
            else:
                hs = int(row["human_score_lookup"])
                out.update(final_score=hs, review_status="LOCKED (human)",
                           review_reason="human_match", final_resolved=hs)
            return pd.Series(out)
        v = verdicts.get((int(row["Master_Case_ID"]), row["nd"]), {})
        g, x = v.get("gemini"), v.get("glm")
        if g:
            out.update(gemini_score=g["score"], gemini_matched_entity=g["matched_entity"],
                       gemini_reason=g["reason"], gemini_confidence=g["confidence"],
                       gemini_flag=g["flag_for_review"])
        if x:
            out.update(glm_score=x["score"], glm_matched_entity=x["matched_entity"],
                       glm_reason=x["reason"], glm_confidence=x["confidence"],
                       glm_flag=x["flag_for_review"])
        if not g or not x:
            out.update(review_status="NEEDS_REVIEW", review_reason="not_judged")
            return pd.Series(out)
        gs, xs = g["score"], x["score"]
        agree = gs is not None and gs == xs
        out["agreement"] = bool(agree)
        flagged = bool(g["flag_for_review"] or x["flag_for_review"])
        if gs is None or xs is None:
            out.update(review_status="NEEDS_REVIEW", review_reason="judge_error")
        elif agree and not (args.review_on_flag and flagged):
            out.update(final_score=gs, review_status="LOCKED",
                       review_reason="judges_agree", final_resolved=gs)
        elif agree and flagged:
            out.update(review_status="NEEDS_REVIEW", review_reason="agree_but_flagged")
        else:
            out.update(review_status="NEEDS_REVIEW", review_reason="judges_disagree")
        return pd.Series(out)

    adj = df.apply(adjudicate, axis=1)
    df["human_score"] = ""  # blank column for you to fill on NEEDS_REVIEW rows
    scored = pd.concat([df.drop(columns=["nd"]), adj], axis=1)

    def resolve(r):
        if str(r["final_resolved"]).strip() not in ("", "None"):
            return r["final_resolved"]
        return r["human_score"] if str(r["human_score"]).strip() != "" else ""
    scored["final_resolved"] = scored.apply(resolve, axis=1)

    col_order = ["run_id","Master_Case_ID","Associated_Images","model_blinded",
                 "model_key","provider",
                 "Ground_Truth_Diagnosis","diagnosis","likert","response_valid",
                 "abstained","technical_failure","score_required",
                 "human_match","human_score_lookup","human_conflict",
                 "gemini_score","gemini_matched_entity","gemini_reason","gemini_confidence","gemini_flag",
                 "glm_score","glm_matched_entity","glm_reason","glm_confidence","glm_flag",
                 "agreement","final_score","review_status","review_reason",
                 "human_score","final_resolved"]
    scored = scored[[c for c in col_order if c in scored.columns]]
    review = scored[scored["review_status"] == "NEEDS_REVIEW"].copy()

    def summarize(g):
        locked = g[g["final_resolved"].apply(lambda x: str(x).strip() in ("0", "1"))]
        correct = locked[locked["final_resolved"].astype(str).str.strip() == "1"]
        return pd.Series({
            "n_rows": len(g),
            "locked_n": len(locked),
            "locked_correct": len(correct),
            "locked_accuracy": round(len(correct) / len(locked), 4) if len(locked) else None,
            "needs_review_n": int((g["review_status"] == "NEEDS_REVIEW").sum()),
        })
    summary = scored.groupby("model_blinded", as_index=False).apply(
        summarize, include_groups=False)
    if "model_key" in scored.columns:
        meta = scored[["model_blinded", "model_key", "provider"]].drop_duplicates()
        summary = summary.merge(meta, on="model_blinded", how="left")
        front = ["model_blinded", "model_key", "provider"]
        summary = summary[front + [c for c in summary.columns if c not in front]]

    summary_by_provider = pd.DataFrame()
    if "provider" in scored.columns:
        summary_by_provider = scored.groupby("provider", as_index=False).apply(
            summarize, include_groups=False)

    OUT_XLSX.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(OUT_XLSX, engine="openpyxl") as xw:
        scored.to_excel(xw, sheet_name="scored", index=False)
        review.to_excel(xw, sheet_name="needs_review", index=False)
        summary.to_excel(xw, sheet_name="summary", index=False)
        if len(summary_by_provider):
            summary_by_provider.to_excel(xw, sheet_name="summary_by_provider", index=False)
        for ws in xw.book.worksheets:
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions

    print(f"\n[done] wrote {OUT_XLSX}")
    print(f"  scored={len(scored)}  needs_review={len(review)}  "
          f"locked={int((scored['review_status']!='NEEDS_REVIEW').sum())}")
    if len(review):
        print("  review_reason breakdown:")
        print(review["review_reason"].value_counts().to_string())


if __name__ == "__main__":
    main()
