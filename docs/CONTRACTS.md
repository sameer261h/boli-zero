> Design notes written on 2026-10-02 while the data and experiment tooling was being split between two contributors. Kept as a record; the README describes current status.

# Contracts between the application side and the experiment/evaluation side

Status: **proposal v0 for review**. Fields marked `proposed` are not in the code yet; everything else is
implemented and tested in `src/boli_zero/`.

## 1. Canonical example record

One JSON object per line. Hindi is the anchor; the regional variety is the target. Code: `schema.py`.

```jsonc
{
  "id": "SYNTHETIC-0001",                 // SYNTHETIC record: fixture only, not real language data
  "anchor_language": "hi",
  "target_language": "bho",
  "anchor_text": "[SYNTHETIC] placeholder anchor sentence",
  "target_text": "[SYNTHETIC] placeholder target sentence",
  "audio_path": null,
  "speaker_id": null,
  "source": "synthetic-fixture",
  "license": "none (not real data)",
  "split": null,

  // proposed additions, all optional with safe defaults:
  "synthetic": true,                      // true only for fixtures like this one
  "verification_status": "unverified",
  "anchor_audio_path": null,
  "audio_transcript": null
}
```

| Field | Rule |
|---|---|
| `id` | Non-empty string, unique across the dataset, never reused for different content. If the source has no id: first 12 hex chars of sha256 of NFC(anchor) + `\x1f` + NFC(target). Ids are opaque: nothing parses them. |
| `anchor_language`, `target_language` | Lowercase ISO 639 codes (`hi`, `bho`, `mai`, `te`). One pair per dataset/run; mixing pairs is rejected by the runner. Script is not a record field today (runner flag `--script`, default Devanagari): see Undecided. |
| `anchor_text`, `target_text` | Unicode NFC, trimmed, non-empty. |
| `source`, `license` | Required, free text but never blank: where it came from and the licence or consent basis. Ingest refuses to run without them. |
| `speaker_id` | Optional opaque id (never a name or phone number). Enables speaker-held-out splits. |
| `audio_path` | Optional, relative to `data/raw` unless absolute. **Proposed meaning: audio of the target-side utterance.** |
| `anchor_audio_path` (proposed) | Optional audio of the Hindi side, for same-speaker pairs. |
| `audio_transcript` (proposed) | Optional text of what the audio actually says (human or Prisma), kept apart from `target_text` so a mishearing is never mistaken for a reference. |
| `verification_status` (proposed) | `unverified` (default) / `machine_generated` / `native_verified` / `native_corrected` / `rejected`. |
| `synthetic` (proposed) | Bool, default false. |
| `split` | `train` / `validation` / `test` / null. **Written only by `boli_zero.split`.** |

Proposed eligibility rules (not enforced yet):
- `validation` and `test` may contain only `native_verified` or `native_corrected` records. A machine-generated
  or unchecked reference is not a valid exam answer.
- `machine_generated` and `synthetic` records may only ever be in `train`, and only if derived from train.
- `rejected` records appear in no split and no prompt.

## 2. Who assigns train/test membership

**The data layer (`split.py`) is the single owner.** The experiment side never splits.

- Output: `data/splits/{train,validation,test}.jsonl` + `manifest.json` (seed, ratios, grouping, input hashes,
  counts). Each record's `split` field is set in those files.
- Deterministic and order-independent: records are ordered by `sha256(seed:group)`; same data + seed gives
  byte-identical files. Grouping defaults to the anchor sentence, so all renderings of one Hindi sentence share
  a split (otherwise a held-out sentence has its answer in train).
- Teaching and retrieval read **`train.jsonl` only**. Development scores use `validation`. `test` is read once,
  for final numbers.
- Guard: `split.check_no_leakage(teaching_pool, held_out)` raises on wrong split labels or any shared id,
  anchor sentence or target sentence. The runner calls it before every run. Any retrieval index built by the
  other side must call it too.
- Every run's `config.json` records `splits_manifest_sha256`, tying results to one split version. Re-splitting
  changes the hash and invalidates older comparisons.

## 3. Evon provider interface

```python
class EvonClient:                                   # src/boli_zero/clients.py
    def __init__(self, config=None, cache=None, transport=None): ...
    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.0) -> str: ...
    calls: int          # requests that actually left the machine
    cache_hits: int
    transport_implemented: bool
```

- **Transport contract** (what a real HTTP layer, a local runtime, or a test stub implements):
  `transport("generate", {"prompt", "max_tokens", "temperature"}, files={}) -> ({"text": str}, None)`.
- **Caching**: every call is keyed by sha256 of service, operation, params (and audio bytes for Prisma).
  Identical calls are never repeated; cached answers replay with no credentials. Credentials are never stored.
- **Errors**: `NotConfigured` when no transport exists, with the list of things to confirm. A transport that
  returns anything but `{"text": str}` raises `ValueError`.
- **Determinism**: temperature defaults to 0. Temperature, max_tokens and any future param are part of the
  cache key.
- The HTTP endpoint, auth and model name are **unconfirmed**; nothing is guessed.
- `PrismaClient.transcribe(audio, language) -> str` and `TimbreClient.synthesize(text, language, voice) -> bytes`
  follow the same pattern.

## 4. What the demo app reads from a run folder

`experiments/<run>/config.json` (task, status, eval_split, n_eval, n_train, ...) and, optionally,
`metrics.json` shaped as `{"identity_baseline": M, "conditions": {"0": M, "10": M, ...}}` where each `M` is
`{n, complete, chrf, exact_match, copy_rate}`. If the experiment side produces different output, it should
keep this shape or tell the application side so the page can be updated.

## 5. Overlap to resolve

`experiment.py`, `evaluate.py` and `ratings.py` already exist as a working reference implementation. If the
experiment side owns that subsystem, propose: it replaces those three modules, keeps sections 2 to 4 as its
inputs, and the reference versions are deleted once its tests pass. Until agreed, the application side leaves
them frozen apart from bug fixes.

## 6. Undecided

1. Which side owns `experiment.py` / `evaluate.py` / `ratings.py` (section 5).
2. Whether the proposed fields (`synthetic`, `verification_status`, `anchor_audio_path`, `audio_transcript`) are
   accepted, and whether the held-out eligibility rule should be enforced by `split.py`.
3. Script as data: a `target_script` record field versus the current runner flag.
4. Whether `audio_path` is target-side only or needs a clearer name.
5. Prompt shape for Evon: raw string today; chat roles, stop sequences or a seed may be needed once the real
   interface is known.
6. Whether to record who verified a record, and when.
7. Retrieval: today shots are a seeded random order of train. Similarity retrieval is not built; it must read
   train only and call the leakage guard.
8. Model name/version in the request params (needed to keep the cache honest across model upgrades).
