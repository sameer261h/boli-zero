"""Send all 9 experiment-5 replies to Timbre."""

import base64
import json
import time

import modal

app = modal.App("experiment5-timbre")
image = modal.Image.debian_slim(python_version="3.11").pip_install("requests")

TIMBRE_URL = "https://api.vachana.ai/api/v1/tts/inference"


@app.function(image=image, secrets=[modal.Secret.from_name("gnani-api-key")], timeout=400)
def run_all(texts: dict):
    import os

    import requests

    api_key = os.environ["GNANI_API_KEY"]
    out = {}

    for i, (key, text) in enumerate(texts.items()):
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
            print(key, "-> FAILED", resp.status_code, resp.text)

    return out


@app.local_entrypoint()
def main():
    with open("experiment5_results.json") as f:
        data = json.load(f)
    texts = {}
    for phrase_key, v in data.items():
        texts[f"{phrase_key}_baseline"] = v["baseline_reply_fixed"]
        texts[f"{phrase_key}_B_lexicon"] = v["mechanism_B_fixed"]
        texts[f"{phrase_key}_C_fewshot"] = v["mechanism_C_fixed"]
    for k, v in texts.items():
        print(k, ":", v)
    out = run_all.remote(texts)
    with open("experiment5_audio.json", "w") as f:
        json.dump(out, f)
    print("Saved.")
