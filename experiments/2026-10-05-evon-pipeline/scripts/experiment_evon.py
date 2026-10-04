"""Controlled experiment: does business context improve Evon's handling of
Bhojpuri customer replies? Prisma is SKIPPED (no real audio for these exact
sentences) — the Bhojpuri text below is used directly as Evon input, standing
in for what would have been Prisma's verbatim transcript.

Condition A: raw transcript only, no system prompt, no context.
Condition B: situational context + exact transcript, no system prompt,
             no language instruction, no translation, no examples.
"""

import json
import time

import requests

EVON_URL = "https://sameer261h--evon-v3-3-serve-serve.modal.run/v1/chat/completions"
EVON_MODEL = "/weights/gnani/gnani-evon-v3.3-30B-A3B"

PHRASES = {
    "1_easy": "हम सोमवार के पैसा जमा कर देब।",
    "2_medium": "अभी पइसा नइखे, सोमारे जमा कर देब।",
    "3_hard": "दू दिन मोहलत दे दीं, तनखा आवे वाला बा।",
}

CONTEXT_TEMPLATE = """A customer has received a phone call from a lender about an EMI payment that is due today. The following is the customer's response as transcribed by speech recognition.

Customer response:

{transcript}

Respond to the customer in this situation."""


def call_evon(content):
    start = time.time()
    resp = requests.post(
        EVON_URL,
        json={"model": EVON_MODEL, "messages": [{"role": "user", "content": content}]},
        timeout=600,
    )
    latency = time.time() - start
    resp.raise_for_status()
    data = resp.json()
    choice = data["choices"][0]
    return {
        "request_content": content,
        "raw_output": choice["message"]["content"],
        "finish_reason": choice["finish_reason"],
        "char_count": len(choice["message"]["content"]),
        "completion_tokens": data.get("usage", {}).get("completion_tokens"),
        "prompt_tokens": data.get("usage", {}).get("prompt_tokens"),
        "latency_sec": round(latency, 2),
    }


def main():
    results = {}
    for key, transcript in PHRASES.items():
        print(f"=== {key} ===")

        print("  Condition A (raw)...")
        results[f"{key}_A"] = call_evon(transcript)
        results[f"{key}_A"]["condition"] = "A_raw"
        results[f"{key}_A"]["transcript"] = transcript
        print(f"    done, {results[f'{key}_A']['char_count']} chars, {results[f'{key}_A']['latency_sec']}s")

        print("  Condition B (context)...")
        context_content = CONTEXT_TEMPLATE.format(transcript=transcript)
        results[f"{key}_B"] = call_evon(context_content)
        results[f"{key}_B"]["condition"] = "B_context"
        results[f"{key}_B"]["transcript"] = transcript
        print(f"    done, {results[f'{key}_B']['char_count']} chars, {results[f'{key}_B']['latency_sec']}s")

    with open("experiment_evon_results.json", "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\nSaved to experiment_evon_results.json")


if __name__ == "__main__":
    main()
