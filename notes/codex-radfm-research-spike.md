# RadFM serving research spike for RadLE medical-VLM benchmark

Date: 2026-07-03 IST

Scope: research only. No RadLE run script, `src/radle_benchmark.py`, notebook, or Ollama recipe script was modified.

## Executive verdict

RadFM is not compatible with the current RadLE Ollama/GGUF recipe as used for LLaVA-Med, OctoMed-7B, InternVL3.5-8B, and Lingshu-32B.

The earlier suspicion is correct: the official `chaoyi-wu/RadFM` implementation is a custom LLaMA-based multimodal model, `MultiLLaMAForCausalLM`, whose custom embedding layer (`my_embedding_layer.py`) converts one or more 2D/3D scans into image-token embeddings and feeds a fused `inputs_embeds` sequence into a Hugging Face `LlamaForCausalLM`. That is materially different from the standard llama.cpp/Ollama multimodal pattern of a supported GGUF language model plus a supported GGUF multimodal projector.

I found no public RadFM GGUF, no Ollama model, no llama.cpp RadFM support, and no standard HF/vLLM/SGLang packaging that would load RadFM without the upstream custom Python code. The practical RadLE path is a RadFM-native Python probe/adapter. A community Flask wrapper (`bkl46/RadFMServer`) exists and exposes a `/v1/chat/completions` route, but it still loads the official custom RadFM code and local `pytorch_model.bin`; it is not evidence of GGUF/Ollama compatibility.

## Sources read

- Official RadFM repo: `chaoyi-wu/RadFM`, upstream HEAD `8d798c554ca0f40cd4a409f0335cc8512cc9d7cf`.
- Official paper records:
  - [Towards Generalist Foundation Model for Radiology](https://consensus.app/papers/towards-generalist-foundation-model-for-radiology-wu-zhang/70157bec1cc3595b9946dfd9f9169944/?utm_source=chatgpt), Wu et al., 2023, arXiv `2308.02463`, Consensus citation count 231, DOI [10.48550/arXiv.2308.02463](https://doi.org/10.48550/arXiv.2308.02463).
  - [Towards generalist foundation model for radiology by leveraging web-scale 2D&3D medical data](https://consensus.app/papers/towards-generalist-foundation-model-for-radiology-by-wu-zhang/5b490977ec625c6d9df83b18f02c64d6/?utm_source=chatgpt), Wu et al., 2025, Nature Communications, Consensus citation count 237, DOI [10.1038/s41467-025-62385-7](https://doi.org/10.1038/s41467-025-62385-7).
- Nature article page: [s41467-025-62385-7](https://www.nature.com/articles/s41467-025-62385-7).
- Official HF model repo: [chaoyi-wu/RadFM](https://huggingface.co/chaoyi-wu/RadFM).
- Local RadLE source: `src/radle_benchmark.py`, especially `PROMPT` and `build_content_array()`.
- Local RadLE reference probe: `scripts/llava_med_hf_probe.py`.
- llama.cpp multimodal docs: [docs/multimodal.md](https://raw.githubusercontent.com/ggml-org/llama.cpp/master/docs/multimodal.md).
- Ollama import docs: [docs.ollama.com/import](https://docs.ollama.com/import).
- Community wrapper counterexample: [bkl46/RadFMServer](https://github.com/bkl46/RadFMServer), HEAD `c951d2647f9f566214ffccd0735ea46775046967`.

## 1. Architecture

The official repo confirms `MultiLLaMAForCausalLM`.

- `src/Model/RadFM/multimodality_model.py` defines `class MultiLLaMAForCausalLM(nn.Module)` and imports `LlamaForCausalLM` from `transformers.models.llama`. The constructor loads `LlamaForCausalLM.from_pretrained(lang_model_path)`, creates `MyEmbedding()`, and ties `MyEmbedding.weight` to the LLaMA input embeddings. See upstream [`multimodality_model.py#L1-L42`](https://github.com/chaoyi-wu/RadFM/blob/8d798c554ca0f40cd4a409f0335cc8512cc9d7cf/src/Model/RadFM/multimodality_model.py#L1-L42).
- The forward path calls `self.embedding_layer(lang_x, vision_x, key_words_query)` and feeds the resulting mixed embeddings into the language model as `inputs_embeds`. Generation does the same before calling `self.lang_model.generate(...)`. See [`multimodality_model.py#L44-L67`](https://github.com/chaoyi-wu/RadFM/blob/8d798c554ca0f40cd4a409f0335cc8512cc9d7cf/src/Model/RadFM/multimodality_model.py#L44-L67) and [`#L119-L144`](https://github.com/chaoyi-wu/RadFM/blob/8d798c554ca0f40cd4a409f0335cc8512cc9d7cf/src/Model/RadFM/multimodality_model.py#L119-L144).

Base LM:

- The quick demo `Language_files/config.json` is a LLaMA-13B-shaped config: `model_type: llama`, `architectures: ["LlamaForCausalLM"]`, hidden size 5120, 40 layers, 40 heads, vocab size 32000, max sequence length 2048. See [`Quick_demo/Language_files/config.json`](https://github.com/chaoyi-wu/RadFM/blob/8d798c554ca0f40cd4a409f0335cc8512cc9d7cf/Quick_demo/Language_files/config.json).
- The Nature paper states that the LLM is initialized from MedLLaMA-13B introduced by PMC-LLaMA, itself further fine-tuned from LLaMA-13B, and that the final model has 14B parameters. See Nature lines 399-402 in the opened article: [Nature implementation section](https://www.nature.com/articles/s41467-025-62385-7).
- The repo's `src/train.py` / `src/test.py` defaults point at local author paths such as `Book_mix_2048_13B_full/checkpoint-45800`; I could not verify from public repo files alone whether the released checkpoint's LM component is exactly vanilla LLaMA-13B, MedLLaMA-13B, or another intermediate local derivative. The paper is the stronger source for MedLLaMA-13B initialization.

Vision encoder and fusion:

- `MyEmbedding` instantiates a 3D ViT with `image_size=512`, `frames=512`, image patch size 32, frame patch size 4, feature dim 768, depth 12, heads 8. See [`my_embedding_layer.py#L22-L67`](https://github.com/chaoyi-wu/RadFM/blob/8d798c554ca0f40cd4a409f0335cc8512cc9d7cf/src/Model/RadFM/my_embedding_layer.py#L22-L67).
- `MyEmbedding.forward()` expects `vision_x` as `[B, S, C, H, W, D]`, reshapes to `(B*S)`, runs the 3D ViT, uses a Perceiver resampler, projects visual features from 768 to 5120, and produces `[B, S*32, 5120]` image-token embeddings. See [`my_embedding_layer.py#L100-L201`](https://github.com/chaoyi-wu/RadFM/blob/8d798c554ca0f40cd4a409f0335cc8512cc9d7cf/src/Model/RadFM/my_embedding_layer.py#L100-L201).
- It concatenates the text embedding weights, two learned figure-token weights, and the per-sample visual embeddings into an expanded embedding table. Then it one-hot encodes token IDs over that expanded table and multiplies them into final mixed embeddings. See [`my_embedding_layer.py#L203-L210`](https://github.com/chaoyi-wu/RadFM/blob/8d798c554ca0f40cd4a409f0335cc8512cc9d7cf/src/Model/RadFM/my_embedding_layer.py#L203-L210).
- The README says the same at a higher level: `RadFM/multimodality_model.py` defines `MultiLLaMAForCausalLM`; `RadFM/my_embedding_layer.py` processes vision input through a 3D ViT and Perceiver; each image/scan gets 32 visual tokens; those tokens are appended to the language embedding layer and referenced by special placeholder token IDs. See [`README.md#L96-L114`](https://github.com/chaoyi-wu/RadFM/blob/8d798c554ca0f40cd4a409f0335cc8512cc9d7cf/README.md#L96-L114).

This corrects one nuance in the prompt: the architecture is not merely a generic "LLaMA-based LM with a custom embedding layer"; the paper identifies the LLM initialization as MedLLaMA-13B / PMC-LLaMA, and the active vision encoder is a 12-layer 3D ViT plus a Perceiver module that reduces each scan to 32 LLM-dimension tokens.

## 2. Serving path and GGUF/Ollama viability

I found no RadFM GGUF and no Ollama model.

- HF API for `chaoyi-wu/RadFM` shows only `.gitattributes`, `RadFM.z01` to `RadFM.z04`, `RadFM.zip`, and `pytorch_model.zip`. There is no `.gguf`, no `safetensors`, no standard sharded HF checkpoint, and no model card. The page also says the model is not deployed by an inference provider: [HF model page](https://huggingface.co/chaoyi-wu/RadFM).
- HF searches for `RadFM GGUF` and `RadFM ggml` returned no RadFM GGUF model. The HF `search=RadFM` result includes the official repo and a few empty/mirror/fine-tuning-like repos, but not a usable GGUF conversion.
- GitHub search for `RadFM GGUF`, `RadFM Ollama`, `MultiLLaMAForCausalLM GGUF`, and `MultiLLaMAForCausalLM Ollama` did not find a public GGUF/Ollama conversion.
- Ollama search did not surface a RadFM library model; `/library/radfm` was treated as absent by the serving agent.

llama.cpp/Ollama support does not cover RadFM's fusion mechanism.

- llama.cpp multimodal support exists through `libmtmd` and a model plus `mmproj` pattern. Its documented pre-quantized vision families include Gemma, SmolVLM, Pixtral, Qwen2/Qwen2.5-VL, InternVL2.5/3, Llama 4 Scout, and Moondream2, not RadFM. See [llama.cpp multimodal docs](https://raw.githubusercontent.com/ggml-org/llama.cpp/master/docs/multimodal.md).
- Ollama supports importing GGUF files and a finite set of safetensors model architectures; the public import docs list common Llama/Mistral/Gemma/Phi-style model imports and GGUF imports, not arbitrary Python `inputs_embeds` fusion graphs. See [Ollama import docs](https://docs.ollama.com/import).
- I searched `ggml-org/llama.cpp` and `ollama/ollama` code for `RadFM` and `MultiLLaMA`; no matches were found.

Native Transformers inference is the only confirmed official path. The official demo imports `MultiLLaMAForCausalLM`, initializes it from `./Language_files`, `torch.load()`s `pytorch_model.bin`, and calls `model.generate(lang_x, vision_x)`. See [`Quick_demo/test.py#L136-L170`](https://github.com/chaoyi-wu/RadFM/blob/8d798c554ca0f40cd4a409f0335cc8512cc9d7cf/Quick_demo/test.py#L136-L170). That is not `AutoModel.from_pretrained()` and not an OpenAI-compatible server by default.

Community wrapper nuance:

- `bkl46/RadFMServer` exists and exposes `/v1/chat/completions` and `/v1/models`. Its README says it runs locally on port 8000 and should be given image paths relative to the server working directory. See [RadFMServer README](https://github.com/bkl46/RadFMServer).
- The root `radfmserver.py` still loads `MultiLLaMAForCausalLM`, `./Language_files/pytorch_model.bin`, and local image paths via PIL. Its `/v1/chat/completions` handler reads nonstandard message fields and is not RadLE-drop-in. See [`radfmserver.py`](https://github.com/bkl46/RadFMServer/blob/main/radfmserver.py).
- `etc/mserver.py` is closer to RadLE's base64 OpenAI content shape: it extracts `image_url` blocks from the last user message, decodes base64, preprocesses to `[1, 3, 512, 512, 4]`, stacks images, inserts one leading `<image>...tokens...</image>` block, and calls `model.generate(lang_x, vision_x)`. See [`etc/mserver.py#L90-L168`](https://github.com/bkl46/RadFMServer/blob/main/etc/mserver.py#L90-L168) and [`#L272-L379`](https://github.com/bkl46/RadFMServer/blob/main/etc/mserver.py#L272-L379).
- This is useful evidence that a RadFM-native OpenAI-shaped adapter is plausible, but it is still a custom Python adapter over the official RadFM code, not an Ollama/GGUF route. It also appears to insert only the first image placeholder sequence in text, even while stacking multiple images; that would need validation before any RadLE use.

Hardware requirements:

- The official README says to avoid CPU and says to ensure at least one NVIDIA A100 80GB for inference, otherwise inference will be so slow that results may not be obtained. It also says test inference batch size defaults to 1. See [`README.md#L92-L94`](https://github.com/chaoyi-wu/RadFM/blob/8d798c554ca0f40cd4a409f0335cc8512cc9d7cf/README.md#L92-L94).
- Nature reports training on 32 NVIDIA A100 80GB GPUs with FSDP, AMP, and gradient checkpointing. See Nature lines 401-402: [Nature implementation section](https://www.nature.com/articles/s41467-025-62385-7).

## 3. Input format and RadLE compatibility

RadFM input format:

- The tokenizer adds `<image>`, `</image>`, and 32 image-token placeholders per image: `<image0>`, `<image1>`, etc. See [`Quick_demo/test.py#L14-L57`](https://github.com/chaoyi-wu/RadFM/blob/8d798c554ca0f40cd4a409f0335cc8512cc9d7cf/Quick_demo/test.py#L14-L57) and [`src/Dataset/multi_dataset.py#L120-L163`](https://github.com/chaoyi-wu/RadFM/blob/8d798c554ca0f40cd4a409f0335cc8512cc9d7cf/src/Dataset/multi_dataset.py#L120-L163).
- Each image is inserted into the text at a character position as `<image>` plus that image's 32 placeholder tokens plus `</image>`. See [`multi_dataset.py#L434-L500`](https://github.com/chaoyi-wu/RadFM/blob/8d798c554ca0f40cd4a409f0335cc8512cc9d7cf/src/Dataset/multi_dataset.py#L434-L500).
- The demo's `combine_and_preprocess()` loads each image path via PIL, converts it to RGB, applies `RandomResizedCrop([512, 512])`, converts to tensor, adds a singleton depth dimension, interpolates to depth 4, stacks images as `[1, S, 3, 512, 512, 4]`, and returns the text plus `vision_x`. See [`Quick_demo/test.py#L59-L107`](https://github.com/chaoyi-wu/RadFM/blob/8d798c554ca0f40cd4a409f0335cc8512cc9d7cf/Quick_demo/test.py#L59-L107).
- The paper says 2D images are expanded into pseudo-3D by adding a depth dimension of size 4; all images are processed by a 3D ViT, then compressed to 32 visual tokens using the Perceiver. See Nature lines 394-399: [Nature implementation section](https://www.nature.com/articles/s41467-025-62385-7).
- For 3D, the paper says depth is resized to the nearest multiple of 4 and capped at 64. See Nature lines 394-395.

RadLE payload shape:

- `src/radle_benchmark.py` defines `build_content_array(case_id, image_index, prompt=PROMPT)` at lines 1412-1428. It returns one OpenAI-style content array: first `{"type": "text", "text": prompt}`, then one `{"type": "image_url", "image_url": {"url": "data:<mime>;base64,<encoded>"}}` block per image path.
- `build_image_index()` groups all images by case ID, so multi-image cases are one prompt plus multiple `image_url` blocks, not multiple model calls.
- The Ollama probes/runners send this exact content array in a single OpenAI chat message: `messages=[{"role": "user", "content": content_array}]`.
- Local RadLE docs require identical prompt and payload parity across models. `Documents/execplan_medical_vlm_ollama_runtime.md` says the shared `PROMPT` and `build_content_array()` payload are identical for every model and should not be special-cased.

Compatibility answer:

- RadLE's 2D image set can fit RadFM's image assumptions in principle. RadFM explicitly supports 2D images by converting them to pseudo-3D depth-4 tensors, and the official demo uses a 2D chest X-ray.
- The transport and entrypoint do not fit. RadLE gives OpenAI-compatible endpoints a base64 `image_url` content array; official RadFM wants local tensors plus image placeholder tokens in the text stream. A RadFM-native adapter would have to decode RadLE's base64 image blocks, preprocess them into `vision_x`, inject the RadFM image placeholder tokens into the text, tokenize, and call `model.generate(lang_x, vision_x)`.
- Preserving the RadLE prompt text verbatim appears possible if the adapter prepends or appends RadFM image placeholder token runs outside the prompt text, or inserts them at a fixed boundary before the prompt, without altering any prompt wording. However, this must be treated as a parity decision: the model would no longer receive the exact OpenAI `content` object, but it could receive the exact RadLE prompt string plus a model-required image-placeholder wrapper.
- Multi-image handling needs special care. RadFM supports multi-image input with `S` images and 32 tokens per image. The official dataset code can insert separate image placeholder runs at chosen text positions. A RadLE adapter should insert one placeholder run per image in a deterministic location while preserving the RadLE prompt words. The `bkl46/RadFMServer` base64 side variant appears to stack multiple images but insert only the first image placeholder sequence into text; that is not sufficient evidence that multi-image RadLE cases are handled correctly.

## 4. Weights and license

Weights are downloadable.

- Official HF repo `chaoyi-wu/RadFM` is public and ungated. HF API reported `private: false`, `gated: false`, and a total storage footprint of about 99.7 GB.
- Files:
  - `pytorch_model.zip`, size 49,878,277,768 bytes. The README says decompressing it gives `pytorch_model.bin`.
  - `RadFM.z01` to `RadFM.z04`, each 10,737,418,240 bytes.
  - `RadFM.zip`, size 6,880,598,149 bytes.
- The official README also links a Baidu Netdisk checkpoint. I did not verify Baidu download behavior beyond the public link.
- I found no Google Drive checkpoint. Zenodo appears to have a code archive, not the 50 GB weights.

Checkpoint layout:

- This is not a normal HF model folder. There is no model card, no `config.json` at the HF model root, no `safetensors`, no HF shard index, and no `auto_map`.
- Official loading is `torch.load('./pytorch_model.bin')` followed by `model.load_state_dict(ckpt)`. See [`Quick_demo/test.py#L136-L144`](https://github.com/chaoyi-wu/RadFM/blob/8d798c554ca0f40cd4a409f0335cc8512cc9d7cf/Quick_demo/test.py#L136-L144).

Licensing:

- The GitHub code repository is MIT-licensed. `gh repo view` reported `licenseInfo: MIT License`, and the repo contains `LICENSE`.
- The Nature article is open access under CC BY-NC-ND 4.0; that applies to the article, not clearly to model weights.
- The HF model page has no model card and no license metadata. I found no explicit weight license or benchmark-use terms.
- Practical benchmark implication: non-commercial/internal research evaluation is technically possible from public weights, but public/commercial benchmark comparison rights are not explicitly documented. For a manuscript-facing RadLE comparison, the safest report wording is: "weights are public, but weight license terms are unspecified upstream."

## 5. Native RadFM probe design, research-level only

If RadLE includes RadFM, the probe should be closer to `scripts/llava_med_hf_probe.py` than to the Ollama runners, but it cannot use `LlavaForConditionalGeneration`, `AutoProcessor`, or `.chat.completions.create`.

At a high level, a RadFM-native probe would need to:

1. Load the upstream RadFM code (`MultiLLaMAForCausalLM`) plus `Quick_demo/Language_files` tokenizer/config artifacts.
2. Download/decompress the official checkpoint to `pytorch_model.bin`; load it with `torch.load(..., map_location='cpu')`; instantiate `MultiLLaMAForCausalLM(lang_model_path='./Language_files')`; `load_state_dict()`; move to CUDA; `eval()`.
3. Reuse RadLE's case/image indexing logic to select real RadLE cases and preserve the exact `radle_benchmark.PROMPT` string.
4. Convert each RadLE image into RadFM's expected tensor shape:
   - Open image as RGB.
   - Apply the RadFM transform or a deterministic variant if parity/reproducibility demands replacing `RandomResizedCrop`.
   - Produce `[1, 3, 512, 512, 4]` per 2D image.
   - Stack to `[1, S, 3, 512, 512, 4]`.
5. Build the model text by adding RadFM image placeholders (`<image>` + 32 tokens + `</image>` per image) at a deterministic boundary while leaving the RadLE prompt words unchanged.
6. Tokenize with the RadFM/LLaMA tokenizer at max length 2048.
7. Call `model.generate(lang_x, vision_x)`, not OpenAI chat completions.
8. Decode with the RadFM tokenizer and compare outputs across visually different RadLE cases, including at least one multi-image case if the adapter is meant to support the full benchmark.

Important probe risks:

- `RandomResizedCrop` is stochastic in the official demo; a benchmark probe should decide whether to set seeds or use deterministic resize/crop. That would be an implementation decision needing documentation because the official preprocessing is random.
- RadFM's max token length is 2048. RadLE's prompt plus placeholder tokens must fit within that budget, especially multi-image cases: each image costs 32 special image tokens plus wrapper tokens.
- A community OpenAI-shaped wrapper exists, but it is not sufficient as-is for manuscript parity. It changes prompt construction and has uncertain multi-image placeholder behavior.

## Final recommendation

Do not try to force RadFM through the current Ollama recipe.

For RadLE, treat RadFM as an adapter-only, RadFM-native benchmark candidate:

- use the public official weights if license risk is acceptable,
- require at least A100 80GB-class inference hardware unless a separate validated optimization exists,
- write a read-only native probe first,
- prove image conditioning on multiple visually distinct RadLE cases,
- prove multi-image handling,
- document that RadFM's serving path is not directly comparable operationally to the Ollama/GGUF medical VLMs even if the prompt text and case set are kept identical.

Unknowns to keep explicit:

- No explicit weight license was found.
- No public Nature-2025-specific replacement checkpoint was found; the public HF checkpoint appears to be the 2023 release.
- No validated RadLE-specific RadFM adapter exists in this repo at this time.
- No public GGUF/Ollama conversion or llama.cpp support for RadFM's custom 3D ViT + Perceiver + expanded-embedding-table fusion was found.

## Round 2

Round 2 scope: research only. No run script, `src/radle_benchmark.py`, notebook, Ollama recipe, or runtime code was modified. This section closes the decision blockers for an INCLUDE vs. EXCLUDE-with-footnote manuscript call.

### Round 2 sources read

- Local RadLE benchmark contract: `src/radle_benchmark.py`, especially `PROMPT`, JSON/prose extraction, repair status logic, public export, `build_image_index()`, and `build_content_array()`.
- Official RadFM code and docs:
  - [`README.md`](https://github.com/chaoyi-wu/RadFM/blob/8d798c554ca0f40cd4a409f0335cc8512cc9d7cf/README.md)
  - [`Quick_demo/test.py`](https://github.com/chaoyi-wu/RadFM/blob/8d798c554ca0f40cd4a409f0335cc8512cc9d7cf/Quick_demo/test.py)
  - [`src/Model/RadFM/multimodality_model.py`](https://github.com/chaoyi-wu/RadFM/blob/8d798c554ca0f40cd4a409f0335cc8512cc9d7cf/src/Model/RadFM/multimodality_model.py)
  - [`src/Model/RadFM/my_embedding_layer.py`](https://github.com/chaoyi-wu/RadFM/blob/8d798c554ca0f40cd4a409f0335cc8512cc9d7cf/src/Model/RadFM/my_embedding_layer.py)
  - [`src/Dataset/multi_dataset.py`](https://github.com/chaoyi-wu/RadFM/blob/8d798c554ca0f40cd4a409f0335cc8512cc9d7cf/src/Dataset/multi_dataset.py)
  - prompt/output examples under `src/Dataset/dataset/` and `src/output_csv_example/`.
- Official issue/community evidence: RadFM GitHub issues [#9](https://github.com/chaoyi-wu/RadFM/issues/9), [#11](https://github.com/chaoyi-wu/RadFM/issues/11), [#18](https://github.com/chaoyi-wu/RadFM/issues/18), [#30](https://github.com/chaoyi-wu/RadFM/issues/30), [#31](https://github.com/chaoyi-wu/RadFM/issues/31), [#42](https://github.com/chaoyi-wu/RadFM/issues/42), and targeted issue/code searches for license, checkpoint, device_map, `load_checkpoint_and_dispatch`, bitsandbytes, quantization, and memory.
- Official model/paper surfaces:
  - [HF model repo `chaoyi-wu/RadFM`](https://huggingface.co/chaoyi-wu/RadFM) and [files/history view](https://huggingface.co/chaoyi-wu/RadFM/tree/main).
  - [HF discussions](https://huggingface.co/chaoyi-wu/RadFM/discussions).
  - Consensus record for [Towards generalist foundation model for radiology by leveraging web-scale 2D&3D medical data](https://consensus.app/papers/towards-generalist-foundation-model-for-radiology-by-wu-zhang/5b490977ec625c6d9df83b18f02c64d6/?utm_source=chatgpt), Wu et al., 2025, Nature Communications.
  - Nature Communications article [10.1038/s41467-025-62385-7](https://www.nature.com/articles/s41467-025-62385-7).
  - arXiv record [2308.02463](https://arxiv.org/abs/2308.02463).
- Community wrapper/fork nuance: [`bkl46/RadFMServer`](https://github.com/bkl46/RadFMServer), especially `radfmserver.py`, `etc/mserver.py`, and `etc/server.py`.

### 1. Hardware feasibility: 4x L4 and A100-40GB

Verdict: unknown for 4x L4 sharding, not evidence-backed for A100-40GB, and needs 80GB-class single-card as the only upstream-supported baseline.

Evidence:

- The official inference demo is single-device: instantiate `MultiLLaMAForCausalLM`, load `pytorch_model.bin`, call `model.to('cuda')`, move `lang_x` and `vision_x` to CUDA, then call `model.generate(lang_x, vision_x)`. See [`Quick_demo/test.py#L142-L162`](https://github.com/chaoyi-wu/RadFM/blob/8d798c554ca0f40cd4a409f0335cc8512cc9d7cf/Quick_demo/test.py#L142-L162).
- The official README explicitly asks for at least one NVIDIA A100 80GB for inference, and says the test inference batch size defaults to one. See [`README.md#L92-L94`](https://github.com/chaoyi-wu/RadFM/blob/8d798c554ca0f40cd4a409f0335cc8512cc9d7cf/README.md#L92-L94).
- The Nature article says the final model has 14B parameters, max token length is 2048, and training used FSDP, AMP, gradient checkpointing, and 32 NVIDIA A100 80GB GPUs. See [Nature lines 399-402](https://www.nature.com/articles/s41467-025-62385-7).
- On paper, a pure fp16 14B language model is about 28 GB decimal before the vision encoder, Perceiver, projector, expanded embedding table, KV cache, CUDA workspaces, and activations. At batch 1 and 2048 tokens, a LLaMA-13B-shaped KV cache is roughly another 1.6 GiB. The official/user evidence is worse than this optimistic math: the maintainer wrote in issue #9 that the model itself takes around 50GB GPU memory without model parallelism, and a user OOMed on 4x and 8x RTX 3090 because the demo still used GPU0 only. See [issue #9 maintainer reply](https://github.com/chaoyi-wu/RadFM/issues/9#issuecomment-1713119301).
- A later issue #9 commenter reported that GPU0 with 48GB was not enough and that trying to pass `device_map` did not use GPU1. See [issue #9 follow-up](https://github.com/chaoyi-wu/RadFM/issues/9#issuecomment-1807761377).
- There is one thin positive datapoint: a 2025 commenter in issue #18 says `accelerate.load_checkpoint_and_dispatch` solved multi-GPU loading. The comment does not provide hardware, code, correctness proof, image-conditioning proof, or L4 evidence. See [issue #18 comment](https://github.com/chaoyi-wu/RadFM/issues/18#issuecomment-2897612876).
- I found no public RadFM code implementing `device_map`, `load_checkpoint_and_dispatch`, bitsandbytes, or a working quantized/offloaded path. GitHub code search for RadFM plus these terms returned no working public implementation. `bkl46/RadFMServer` still uses custom RadFM loading and `model.to('cuda')`; one file has a commented `load_checkpoint_and_dispatch(... device_map="balanced" ...)` experiment, not a working proof. See [`bkl46/RadFMServer/etc/server.py#L172-L187`](https://github.com/bkl46/RadFMServer/blob/main/etc/server.py#L172-L187).

The critical adapter risk is not `inputs_embeds` by itself. Transformers generation can handle decoder-only `inputs_embeds` on the first generation step. The risk is the custom pre-LLM fusion graph: `MyEmbedding` builds visual tokens through the 3D ViT and Perceiver, concatenates `self.weight`, `figure_token_weight`, and `vision_x`, then one-hot multiplies the full expanded embedding table. See [`my_embedding_layer.py#L193-L210`](https://github.com/chaoyi-wu/RadFM/blob/8d798c554ca0f40cd4a409f0335cc8512cc9d7cf/src/Model/RadFM/my_embedding_layer.py#L193-L210). Under LLaMA layer sharding, a correct adapter must keep `embedding_layer.weight`, wrapper-token weights, vision outputs, and the final `inputs_embeds` device-consistent while handing the resulting embeddings to a sharded `lang_model.generate()`.

Hardware read:

- 4x L4, 96 GB aggregate, no NVLink: plausible as an engineering target only if the custom RadFM wrapper is explicitly sharded with Accelerate/FSDP-style big-model inference. It is not proven upstream. PCIe/no NVLink should mostly hurt latency at batch 1, not correctness, if the graph is correctly sharded.
- Single A100-SXM4-40GB: not evidence-backed. The optimistic fp16 arithmetic might look close, but official/user evidence points to about 50GB GPU memory and a failed 48GB single-GPU attempt. I found no public 8-bit, 4-bit, or CPU-offload RadFM success report.
- Evidence-backed baseline: one 80GB-class GPU.

### 2. Likert emission and scoreability

Verdict: no public evidence that RadFM emits a RadLE-compatible 0-4 Likert under the identical prompt; this is the decisive blocker.

Local RadLE contract:

- `src/radle_benchmark.py:110-139` defines the shared prompt and requires final JSON with `{"diagnosis": "...", "likert_score": <0-4 or null>}`.
- `src/radle_benchmark.py:240-352` can recover malformed JSON, VQA-style numbered answers, and some prose diagnoses.
- `src/radle_benchmark.py:993-1003` treats a diagnosis with invalid or missing Likert as `invalid_or_missing_likert_with_diagnosis`, requiring repair and eventually repair exhaustion.
- `src/radle_benchmark.py:2430-2452` exports `likert_score` only if it is valid, and keeps `score_likert` as a first-class public metric field.
- `src/radle_benchmark.py:2609-2626` builds the scorer view from diagnosis and Likert columns.

RadFM behavior evidence:

- The official quick demo asks about cardiomegaly and documents output as a plain `yes`, not JSON and not confidence. See [`README.md` quick-start and `Quick_demo/test.py`](https://github.com/chaoyi-wu/RadFM/blob/8d798c554ca0f40cd4a409f0335cc8512cc9d7cf/Quick_demo/test.py).
- Official diagnosis prompts are free-form questions such as "What is the diagnosis for this chest X-ray?" and differential-diagnosis variants. I found no confidence or JSON constraint in the official prompt files.
- Official report prompts request findings/impression prose, and the sample output CSV uses `Question`, `Ground Truth`, `Pred`, and `belong_to`; there is no confidence column. The official `src/test.py` writes decoded `Pred` text, not structured confidence.
- The Nature article frames RadFM outputs as medical VQA, report generation, and rationale diagnosis, with qualitative examples of free-form text generation. See [Nature lines 183-202](https://www.nature.com/articles/s41467-025-62385-7).
- A community wrapper can post-process into its own JSON-like schema, but that is wrapper-generated and not RadFM self-reporting a RadLE `likert_score` 0-4 under the identical prompt.

Consequence: if RadFM returns only a diagnosis phrase, yes/no answer, or report prose, RadLE may recover a diagnosis for qualitative review, but it is not Likert-weight-scoreable on equal footing with the other models. Prompt parity forbids adding a separate confidence-elicitation scaffold. This alone supports EXCLUDE unless a live, read-only RadFM-native smoke test proves valid 0-4 Likert emission under the exact existing `PROMPT`.

### 3. Checkpoint provenance: 2023 public checkpoint vs Nature-2025

Verdict: the public HF checkpoint appears to be the 2023 checkpoint; exact Nature-2025 parity is undocumented upstream.

Evidence:

- The Nature Communications article was published on 2025-08-23 and its code availability section points to the GitHub repo, but does not provide a checkpoint URL, weight hash, HF commit, or evaluated-checkpoint identifier. See [Nature data/code availability](https://www.nature.com/articles/s41467-025-62385-7).
- The HF model repo files/history show `pytorch_model.zip` uploaded almost three years ago, with the file view showing commit `bd5e695` and date around 2023-08-31. The repo has 4 commits and a total model repo footprint of about 99.7 GB. See [HF files view](https://huggingface.co/chaoyi-wu/RadFM/tree/main).
- The arXiv paper was submitted in 2023 and already promised public code, data, and checkpoint. That timing matches the 2023 HF artifact, not a 2025 replacement checkpoint.
- GitHub issues from 2023 already reference downloading the same `pytorch_model.zip` and placing `pytorch_model.bin` under `Quick_demo/`.

Manuscript caveat if RadFM is mentioned: "We use the public RadFM checkpoint distributed via `chaoyi-wu/RadFM` on Hugging Face. Upstream documentation does not provide a checkpoint hash or explicit statement confirming that this artifact is byte-identical to the model evaluated in the Nature Communications 2025 article; therefore, results should be described as using the public 2023 RadFM checkpoint rather than confirmed Nature-2025 checkpoint parity."

### 4. Weight license

Verdict: genuinely silent for the model weights.

Evidence:

- The GitHub code repository is MIT-licensed. That license covers the software repository, not clearly the HF checkpoint weights.
- The HF model repo has no model card and no visible license metadata. See [HF model repo](https://huggingface.co/chaoyi-wu/RadFM) and [files view](https://huggingface.co/chaoyi-wu/RadFM/tree/main).
- HF discussions did not surface weight-license guidance; the visible discussion surface is not a license clarification.
- The Nature article is CC BY-NC-ND 4.0, which applies to the article, not automatically to model weights. See [Nature rights and permissions](https://www.nature.com/articles/s41467-025-62385-7).
- The Nature data availability section says most datasets can be used for non-commercial purposes and that RP3D/MPx have licensing restrictions requiring external approval. See [Nature data availability](https://www.nature.com/articles/s41467-025-62385-7).

Safest manuscript wording: "RadFM's code is MIT-licensed and its checkpoint is publicly downloadable, but the Hugging Face checkpoint repository does not specify a separate weight license. We therefore treat the weights as public for non-commercial academic inspection only and do not assume commercial reuse, redistribution, or deployment rights."

### 5. Multi-image placeholder construction

Verdict: the official pattern is one placeholder span per image, in image-list order; a correct RadLE adapter must replicate that rather than copying the community wrapper's single-placeholder shortcut.

Official construction:

- The tokenizer constructs 32 placeholder tokens per image index: image `i` uses `<image{32*i}>` through `<image{32*i+31}>`, wrapped by `<image>` and `</image>`. See [`multi_dataset.py#L120-L163`](https://github.com/chaoyi-wu/RadFM/blob/8d798c554ca0f40cd4a409f0335cc8512cc9d7cf/src/Dataset/multi_dataset.py#L120-L163).
- Official `text_add_image()` inserts each image's placeholder span at the image metadata position using the image's list index. Distinct text positions are not guaranteed; if several images share a position, spans are adjacent there. The core invariant is image-list index alignment. See [`multi_dataset.py#L434-L502`](https://github.com/chaoyi-wu/RadFM/blob/8d798c554ca0f40cd4a409f0335cc8512cc9d7cf/src/Dataset/multi_dataset.py#L434-L502).
- Official image preprocessing stacks images in list order into `[S, 3, 512, 512, D]`, then the model expects `[B, S, C, H, W, D]`. `MyEmbedding` flattens the resulting visual tokens as `S * 32` in order. See [`my_embedding_layer.py#L100-L118`](https://github.com/chaoyi-wu/RadFM/blob/8d798c554ca0f40cd4a409f0335cc8512cc9d7cf/src/Model/RadFM/my_embedding_layer.py#L100-L118) and [`#L193-L210`](https://github.com/chaoyi-wu/RadFM/blob/8d798c554ca0f40cd4a409f0335cc8512cc9d7cf/src/Model/RadFM/my_embedding_layer.py#L193-L210).
- The quick demo shows the same single-image placeholder idea, but its `torch.cat(images, dim=1).unsqueeze(0)` is safe only for `S=1`; copied literally for multi-image input it would not yield `[1, S, 3, 512, 512, 4]`.
- `bkl46/RadFMServer/etc/mserver.py` stacks multiple base64 images but inserts only `image_padding_tokens[0]` once. That is not the official multi-image pattern.

Correct RadLE adapter shape:

1. Preserve RadLE's ordered `image_url` blocks from `src/radle_benchmark.py:1412-1428`.
2. Decode and preprocess each 2D image into `[1, 3, 512, 512, 4]`.
3. Build `vision_x = torch.cat(image_tensors, dim=0).unsqueeze(0)` to get `[1, S, 3, 512, 512, 4]`.
4. Insert one span per image in the same order, for example:

```text
<image><image0>...<image31></image>
<image><image32>...<image63></image>
...
<RadLE prompt text unchanged>
```

Token budget: intended cost is 34 special tokens per image: 32 image placeholders plus `<image>` and `</image>`. With max length 2048, the safe budget is `prompt_tokens + 34*S <= 2048`.

### 6. Image-fidelity concern

Verdict: material validity risk for hard, detail-dependent RadLE diagnoses, especially if an adapter follows the stochastic quick-demo crop instead of the paper's deterministic resize description.

Evidence:

- The official quick demo uses `transforms.RandomResizedCrop([512, 512], scale=(0.8, 1.0), interpolation=BICUBIC)` before tensor conversion. See [`Quick_demo/test.py#L59-L107`](https://github.com/chaoyi-wu/RadFM/blob/8d798c554ca0f40cd4a409f0335cc8512cc9d7cf/Quick_demo/test.py#L59-L107). For a benchmark, that is a reproducibility and lesion-cropping risk unless seeds or deterministic preprocessing are specified.
- The Nature methods describe min-max normalization and `torchvision.transforms.Resize`, with 2D images resized to 512 x 512 and 2D inputs expanded into pseudo-3D depth 4. See [Nature lines 393-397](https://www.nature.com/articles/s41467-025-62385-7). That is more benchmark-suitable than the quick-demo random crop, but the public demo does not implement it.
- The paper says visual tokens are compressed to a fixed length of 32 using the Perceiver and each image becomes a 32 x 5120 embedding. See [Nature lines 397-399](https://www.nature.com/articles/s41467-025-62385-7) and [`README.md#L329-L336`](https://github.com/chaoyi-wu/RadFM/blob/8d798c554ca0f40cd4a409f0335cc8512cc9d7cf/README.md#L329-L336).
- The paper's own ablations say larger patch sizes than 32 degrade performance, while smaller patch sizes might be better but were too expensive. See [Nature lines 129-134](https://www.nature.com/articles/s41467-025-62385-7). That supports the idea that spatial granularity is a real tradeoff.
- The qualitative section notes fine-grained failures: one challenging abnormality-type example is misidentified, generated reports may lack left/right location information, and rationale output can be general rather than input-specific. See [Nature lines 183-202](https://www.nature.com/articles/s41467-025-62385-7).

A reproducible RadLE adapter should use the paper's deterministic resize-style preprocessing or explicitly document any deviation. Even then, 512 x 512 -> pseudo-depth-4 -> 3D ViT -> 32 visual tokens per image is a real compression path for subtle radiographic details.

### Decision block

(a) Can RadFM emit a Likert 0-4 under the identical RadLE prompt so it is Likert-weight-scoreable like the other four models?

No evidence. Public RadFM examples, prompts, and output code show yes/no, short QA/diagnosis text, and report/rationale prose, not a self-reported 0-4 Likert. Because RadLE scoring treats missing/invalid Likert as a repair/exhaustion condition, this alone likely forces EXCLUDE unless a live RadFM-native smoke test proves valid Likert emission under the exact prompt.

(b) Can it run on the 4x L4 box or, if not, one A100-40GB?

4x L4 sharding is unknown and unproven. It may be technically possible with a custom Accelerate/FSDP-style adapter, but no upstream code or public fork proves correct sharded inference. One A100-40GB is not evidence-backed; official/user evidence points to about 50GB GPU memory and one 80GB-class GPU as the supported inference baseline.

(c) Is it license-clear for a manuscript?

Not fully. Code is MIT and weights are public, but the weight license is genuinely silent. Data/paper surfaces include non-commercial/restricted terms. The safest position is non-commercial academic inspection only, without assuming redistribution/commercial/deployment rights.

(d) Recommendation.

EXCLUDE, with a footnote if RadFM is discussed: "RadFM was considered but excluded because no public evidence shows it can self-report the required 0-4 Likert confidence under the identical RadLE prompt; additionally, available hardware does not meet the upstream 80GB-class inference baseline, public 4x L4 sharding is unproven, weight licensing is unspecified, and the public checkpoint appears to be the 2023 release rather than confirmed Nature-2025 parity."

(e) If INCLUDE were still pursued, minimal read-only probe scope before any real run.

Only after accepting the license and hardware caveats: run a load-only, single-case RadFM-native smoke on the intended hardware; prove image conditioning with two visually distinct RadLE cases; prove exact-prompt output includes parseable `{"diagnosis": ..., "likert_score": 0-4}` without any extra prompt scaffold; include one multi-image case to verify per-image placeholder alignment; log device map, peak VRAM per GPU, raw decoded output, parsed diagnosis/Likert, branch/commit, checkpoint hash, and preprocessing path. If Likert is missing in this smoke, stop and keep EXCLUDE.
