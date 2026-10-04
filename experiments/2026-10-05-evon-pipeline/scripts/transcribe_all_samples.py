"""Transcribe all 5 Vaani Bhojpuri samples via Prisma (hi-IN, verbatim)."""

import modal

app = modal.App("transcribe-vaani-samples")
image = modal.Image.debian_slim(python_version="3.11").pip_install("requests")

volume = modal.Volume.from_name("vaani-samples", create_if_missing=True)
SAMPLES_DIR = "/samples"


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("gnani-api-key")],
    volumes={SAMPLES_DIR: volume},
    timeout=300,
)
def transcribe_all():
    import os

    import requests

    api_key = os.environ["GNANI_API_KEY"]
    out = {}
    for i in range(5):
        path = f"{SAMPLES_DIR}/sample_{i}.wav"
        with open(path, "rb") as f:
            audio_bytes = f.read()
        resp = requests.post(
            "https://api.vachana.ai/stt/v3",
            headers={"X-API-Key-ID": api_key},
            files={"audio_file": ("audio.wav", audio_bytes)},
            data={"language_code": "hi-IN", "format": "verbatim"},
            timeout=60,
        )
        if resp.ok:
            out[f"sample_{i}"] = resp.json()["transcript"]
        else:
            out[f"sample_{i}"] = f"ERROR {resp.status_code}: {resp.text}"
        print(f"sample_{i}: {out[f'sample_{i}']}")
    return out
