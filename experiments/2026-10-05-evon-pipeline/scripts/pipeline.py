"""Bhojpuri audio -> Prisma (STT) -> Evon -> Timbre (TTS) -> spoken response.

Raw passthrough at every step: Prisma's verbatim transcript goes to Evon
untouched, Evon's raw reply goes to Timbre untouched. No prompts, no
language instructions, no post-processing.
"""

import modal

app = modal.App("evon-pipeline")

image = modal.Image.debian_slim(python_version="3.11").pip_install("requests", "fastapi")

EVON_URL = "https://sameer261h--evon-v3-3-serve-serve.modal.run/v1/chat/completions"
EVON_MODEL = "/weights/gnani/gnani-evon-v3.3-30B-A3B"
PRISMA_URL = "https://api.vachana.ai/stt/v3"
TIMBRE_URL = "https://api.vachana.ai/api/v1/tts/inference"

# Bhojpuri has no official Prisma/Timbre language code; hi-IN is the closest
# supported language since Bhojpuri is linguistically close to Hindi.
STT_LANGUAGE_CODE = "hi-IN"
TTS_VOICE = "Nalini"


@app.function(image=image, secrets=[modal.Secret.from_name("gnani-api-key")], timeout=600)
@modal.fastapi_endpoint(method="POST")
async def run_pipeline(item: dict):
    import base64
    import os

    import requests

    api_key = os.environ["GNANI_API_KEY"]

    # body: {"audio_base64": "<base64-encoded audio file>"}
    audio_bytes = base64.b64decode(item["audio_base64"])

    # 1. Prisma: audio -> exact transcript (verbatim, no ITN, no post-processing)
    stt_resp = requests.post(
        PRISMA_URL,
        headers={"X-API-Key-ID": api_key},
        files={"audio_file": ("audio.wav", audio_bytes)},
        data={"language_code": STT_LANGUAGE_CODE, "format": "verbatim"},
        timeout=60,
    )
    stt_resp.raise_for_status()
    transcript = stt_resp.json()["transcript"]

    # 2. Evon: transcript -> raw reply (no system prompt, no language instruction)
    evon_resp = requests.post(
        EVON_URL,
        json={"model": EVON_MODEL, "messages": [{"role": "user", "content": transcript}]},
        timeout=600,
    )
    evon_resp.raise_for_status()
    reply_text = evon_resp.json()["choices"][0]["message"]["content"]

    # 3. Timbre: reply -> spoken audio
    result = {"prisma_transcript": transcript, "evon_reply": reply_text}
    tts_resp = requests.post(
        TIMBRE_URL,
        headers={"X-API-Key-ID": api_key, "Content-Type": "application/json"},
        json={
            "text": reply_text,
            "model": "timbre-v2.5",
            "voice": TTS_VOICE,
            "language": "auto",
            "audio_config": {
                "encoding": "linear_pcm",
                "container": "wav",
                "num_channels": 1,
                "sample_rate": 48000,
                "sample_width": 2,
            },
        },
        timeout=60,
    )
    if tts_resp.ok:
        result["audio_base64"] = base64.b64encode(tts_resp.content).decode()
    else:
        result["tts_error"] = f"{tts_resp.status_code}: {tts_resp.text}"
    return result
