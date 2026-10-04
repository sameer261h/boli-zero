# Context for Codex: Bhojpuri voice pipeline (Evon + Prisma + Timbre) — findings and open problems

## What's deployed and working

A full voice pipeline is live on Modal (serverless GPU/CPU platform):

- **Evon v3.3 (30B-A3B, BF16, NemotronH architecture)** — gnani/gnani-evon-v3.3-30B-A3B, served via vLLM on an A100 80GB.
  Endpoint: `https://sameer261h--evon-v3-3-serve-serve.modal.run/v1/chat/completions` (OpenAI-compatible, no auth).
  No system prompt, no language instruction, raw output only.
- **Prisma (Gnani's hosted STT API)** — `https://api.vachana.ai/stt/v3`. Transcribes audio, `format=verbatim` (no ITN/post-processing).
- **Timbre (Gnani's hosted TTS API)** — `https://api.vachana.ai/api/v1/tts/inference`, model `timbre-v2.5`.
- **Orchestration endpoint** chaining all three: `https://sameer261h--evon-pipeline-run-pipeline.modal.run`
  Takes `{"audio_base64": "..."}`, returns `{"prisma_transcript", "evon_reply", "audio_base64" | "tts_error"}`.

Code lives in `~/evon-test/evon_serve.py` (Evon) and `~/evon-test/pipeline.py` (orchestration).

## Key constraint

**Neither Prisma nor Timbre officially support Bhojpuri.** Supported languages are Bengali, English, Gujarati, Hindi, Kannada, Malayalam, Marathi, Punjabi, Tamil, Telugu (+ Hinglish and auto-detect on Timbre). We've been passing Bhojpuri audio to Prisma tagged as `hi-IN` (Hindi) as the closest linguistic match, since Bhojpuri isn't in the supported list at all.

## Test data

Pulled 5 real Bhojpuri audio samples from the `ARTPARK-IISc/Vaani` dataset (Hugging Face, gated, access granted) — a genuine Indian-languages speech corpus. Female speaker, Jamtara district, Jharkhand, fluent in Hindi and Bhojpuri. One sample has a human-verified ground-truth transcript.

## Findings so far

### 1. Prisma handles Bhojpuri-as-Hindi surprisingly well
On the one sample with a ground-truth transcript, Prisma's verbatim output was essentially word-for-word identical to the human transcription — despite Bhojpuri not being a supported language. This suggests treating Bhojpuri as Hindi for STT is a workable stopgap, at least for this speaker/accent.

### 2. Evon over-reasons on any non-question input, in long unbounded chains
Tested 3 scenarios:
- Clear English question ("Hello, how are you?") → short, normal reply.
- Clear Hindi factual question ("भारत की राजधानी क्या है?" / "What is the capital of India?") → ~1,135 character reply (mostly chain-of-thought reasoning, ending in a short correct answer "नई दिल्ली").
- Vague Bhojpuri-derived statements (e.g., a scene description: "there's a function with many girls in white and red, a couple boys too, looks like a women's welfare home event") → **4,300–6,244 character replies**, with Evon treating a plain description as a riddle to solve, speculating at length about what occasion is being described (landed on "probably Christmas" based on red/white colors — confidently wrong/unfounded given Evon has no retrieval or grounding).

Pattern: **the problem isn't Bhojpuri or short/long input — it's that any non-question statement sent to Evon with zero system prompt triggers extended unbounded reasoning.** This will keep happening with real conversational audio, which is mostly statements, not questions.

### 3. Timbre has an undocumented text-length limit that breaks the pipeline
- 240 characters → 200 OK.
- 1,135 characters → 200 OK.
- 4,300+ and 6,244 characters → both failed with a generic `{"success":false,"message":"We are facing technical difficulties. Please try again later.","status_code":500}` from Gnani's own server.
- The exact threshold between ~1,135 and ~4,300 chars is unknown — not bisected yet.
- This is undocumented in Gnani's API docs (no stated max length for the `text` field on TTS REST).

### 4. Evon's reply language is inconsistent and mostly defaults to English
- Internal reasoning trace: **always English**, regardless of input language (Hindi or Bhojpuri-as-Hindi).
- Final answer: sometimes in the input's language (Hindi question → Hindi final answer), but on both Bhojpuri-derived inputs, the **entire reply including the final answer stayed in English**.
- This breaks the actual product goal: a Bhojpuri speaker should get a Bhojpuri/Hindi spoken reply back, not English. Right now that's not reliably happening.

## Open problems for brainstorming

1. **How to bound Evon's output without violating "raw output, no system prompt" constraints?**
   Options to weigh: a `max_tokens` cap (truncates mid-thought, not elegant but simple), some kind of two-pass approach (let it reason, then extract/re-synthesize just the final answer — but that's post-processing, which was explicitly ruled out), or accepting the tradeoff and prompting it differently (which was also ruled out — no system prompt allowed per original constraints). Is there a middle ground?

2. **How to get Evon to reliably reply in the input's language?**
   No system prompt is allowed, so we can't just say "reply in Bhojpuri." Is this a sampling/temperature issue, a training artifact of the base NemotronH model, or does the 30B-A3B MoE routing behave differently per language in ways we don't have visibility into? Worth testing: does reply language correlate with input length, question-vs-statement framing, or something else?

3. **What's Timbre's actual character/token limit, and is there a way around it?**
   Should bisect the exact threshold. Also worth checking: does chunking a long reply into multiple TTS calls and concatenating audio work as a workaround, or does Gnani's API have a batch/streaming mode better suited to long text (their docs mention TTS Streaming and TTS Realtime as alternatives to TTS REST)?

4. **Cold-start economics**: Evon's A100 80GB container takes ~3-4 minutes to cold-boot (model load + vLLM graph capture + Mamba kernel warmup) and currently sleeps after 1 hour idle. Is there a cheaper way to keep it warm for a demo window without paying for 24/7 A100 time? (Currently on Modal, $30/month free credit, ~$22 remaining after testing so far.)

## What NOT to touch (per original project constraints)
- No system prompt to Evon, ever.
- No instruction to Evon about what language to reply in.
- No translation, normalization, or enrichment of Prisma's transcript before it reaches Evon.
- No post-processing of Evon's reply before it's spoken by Timbre (any fix must work within the actual model behavior, not paper over it after the fact) — though note finding #1 above means this constraint may need revisiting if it's fundamentally incompatible with Timbre's length limit.
