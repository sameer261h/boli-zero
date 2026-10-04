"""Send the 6 category-coverage REPLY sentences to Timbre."""

import base64
import json
import time

import modal

app = modal.App("tts-categories")
image = modal.Image.debian_slim(python_version="3.11").pip_install("requests")

TIMBRE_URL = "https://api.vachana.ai/api/v1/tts/inference"


@app.function(image=image, secrets=[modal.Secret.from_name("gnani-api-key")], timeout=300)
def run_all(replies: dict):
    import os

    import requests

    api_key = os.environ["GNANI_API_KEY"]
    out = {}

    for i, (key, text) in enumerate(replies.items()):
        if i > 0:
            time.sleep(15)
        resp = requests.post(
            TIMBRE_URL,
            headers={"X-API-Key-ID": api_key, "Content-Type": "application/json"},
            json={
                "text": text,
                "model": "timbre-v2.5",
                "voice": "Nalini",
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
        if resp.ok:
            out[key] = base64.b64encode(resp.content).decode()
            print(key, "-> success")
        else:
            out[key] = None
            print(key, "-> FAILED", resp.status_code)

    return out


@app.local_entrypoint()
def main():
    with open("experiment4_categories_results.json") as f:
        data = json.load(f)
    replies = {k: v["final"].split("REPLY:")[-1].strip() for k, v in data.items()}
    for k, v in replies.items():
        print(k, ":", v)
    out = run_all.remote(replies)
    with open("categories_audio.json", "w") as f:
        json.dump(out, f)
    print("Saved.")
