# shared_1k_audio_manifest.jsonl

Canonical 999-clip sample reused by (1) the 40-parameter grammatical analysis, (2) Allosaurus, (3) IndicWav2Vec. **Do not resample.**

- **Identity:** `dataset + shard + row_idx` (row_idx = positional index in the shard parquet).
  `dataset` is `ARTPARK-IISc/Vaani-transcription-part` (the repo the earlier Prisma pulls used), not `ARTPARK-IISc/Vaani`.
  `audio_sha256` lets you verify retrieval; 16 random rows were re-fetched independently and matched (hash + transcript).
- **Languages:** Bhojpuri, Chhattisgarhi, Garhwali, Khariboli, Kumaoni, Maithili, Rajasthani = 125 each; Hindi = 124
  (one clip dropped because its Prisma call failed). Total 999.
- **Prisma transcripts:** 7 non-Hindi languages reuse the earlier hi-IN/verbatim pull (row_idx alignment verified, 0 mismatches);
  Hindi was transcribed fresh with the same settings.
- **Selection:** seeded (20261005), neutral — diversity-greedy over speaker key, reference image, district, gender, shard,
  transcript-length bin; never looks at dialect markers. All speaker keys and audio hashes are unique; reference images unique except one Khariboli pair.
- **speaker_or_source_group:** parsed from the audio filename (`<recording-kind>:<district>:<id token>`). The dataset has no explicit speaker column;
  across 47.7k keys none mixes genders, so it is consistent with a speaker/session ID but unconfirmed.
- **Limits:** Garhwali/Kumaoni/Rajasthani come from only 1–2 districts (that is all the corpus has); Hindi has no earlier corpus rows and was drawn from 12 random of 250 shards.
- Rebuild: `scripts/scan_shard_metadata.py` then `scripts/build_shared_1k_manifest.py`. Audio is not re-hosted.
