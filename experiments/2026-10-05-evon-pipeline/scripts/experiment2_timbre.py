"""Send each of the 10 extracted REPLY sentences to Timbre, with spacing to avoid rate limits."""

import base64
import json
import time

import modal

app = modal.App("evon-experiment2-timbre")
image = modal.Image.debian_slim(python_version="3.11").pip_install("requests")

TIMBRE_URL = "https://api.vachana.ai/api/v1/tts/inference"


@app.function(image=image, secrets=[modal.Secret.from_name("gnani-api-key")], timeout=400)
def run_all(evon_results: dict):
    import os

    import requests

    api_key = os.environ["GNANI_API_KEY"]
    out = {}

    for i, (key, entry) in enumerate(evon_results.items()):
        if i > 0:
            time.sleep(15)
        text = entry["reply_extracted_fixed"]
        start = time.time()
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
        latency = time.time() - start
        result = {"text": text, "status_code": resp.status_code, "latency_sec": round(latency, 2)}
        if resp.ok:
            result["success"] = True
            result["audio_base64"] = base64.b64encode(resp.content).decode()
            result["audio_bytes"] = len(resp.content)
        else:
            result["success"] = False
            result["error"] = resp.text
        out[key] = result
        print(key, "->", result.get("success"), result.get("status_code"))

    return out


@app.local_entrypoint()
def main():
    with open("experiment2_evon_results.json") as f:
        evon_results = json.load(f)
    out = run_all.remote(evon_results)
    with open("experiment2_timbre_results.json", "w") as f:
        json.dump(out, f, indent=2)
    print("Saved to experiment2_timbre_results.json")
