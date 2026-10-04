"""Send each of the 6 Evon experiment outputs to Timbre, unmodified."""

import base64
import json
import time

import modal

app = modal.App("evon-experiment-timbre")
image = modal.Image.debian_slim(python_version="3.11").pip_install("requests")

TIMBRE_URL = "https://api.vachana.ai/api/v1/tts/inference"


@app.function(image=image, secrets=[modal.Secret.from_name("gnani-api-key")], timeout=300)
def run_all(evon_results: dict):
    import os

    import requests

    api_key = os.environ["GNANI_API_KEY"]
    out = {}

    for i, (key, entry) in enumerate(evon_results.items()):
        if i > 0:
            time.sleep(15)
        text = entry["raw_output"]
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
        result = {"status_code": resp.status_code, "latency_sec": round(latency, 2)}
        if resp.ok:
            result["success"] = True
            result["audio_base64"] = base64.b64encode(resp.content).decode()
            result["audio_bytes"] = len(resp.content)
            # 48000 Hz, 16-bit mono WAV -> approx duration
            result["approx_duration_sec"] = round((len(resp.content) - 44) / (48000 * 2), 2)
        else:
            result["success"] = False
            result["error"] = resp.text
        out[key] = result
        print(key, "->", result.get("success"), result.get("status_code"))

    return out


@app.local_entrypoint()
def main():
    with open("experiment_evon_results.json") as f:
        evon_results = json.load(f)
    out = run_all.remote(evon_results)
    with open("experiment_timbre_results.json", "w") as f:
        json.dump(out, f, indent=2)
    print("Saved to experiment_timbre_results.json")
