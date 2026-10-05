# 19 — Allosaurus phonotactic LID feasibility (shared 1k manifest)

Question: can phone sequences extracted directly from audio distinguish Hindi from close regional varieties?
Inputs to the classifier are only Allosaurus phone n-grams. No transcripts, Prisma output, metadata or IndicWav2Vec features are used.
Script: `experiments/2026-10-05-evon-pipeline/scripts/allosaurus_phonotactic_lid.py`. Full numbers are in `data/allosaurus_lid/results.json` and the phone cache is `data/allosaurus_lid/phones.jsonl`.

1. **Model:** `allosaurus` 1.0.2, default pretrained universal model `uni2005`, frozen, universal IPA inventory (no language restriction).
2. **Clips:** 125 per language × 8 = 1,000 from the frozen `data/shared_1k_audio_manifest.jsonl`. No audio was unusable (0 errors).
3. **Duration:** mean 6.33 s (median 6.05). Hindi is the shortest at 4.88 s; Kumaoni the longest at 7.75 s. Mean is 59.8 phones per clip, at 8.5–10.7 phones/s.
4. **Split and leakage controls:**
   - 5-fold StratifiedGroupKFold, with groups = state|district (94 groups). A district never appears in both train and test, which also covers speaker and session.
   - Metadata is never a feature.
   - The manifest de-duplicates by row, normalized transcript and (for Hindi) audio hash. It allows at most one clip per (group, reference image).
   - Limits:
     - Rajasthani, Garhwali and Kumaoni have only 2 districts each.
     - Garhwali and Kumaoni come from the *same* 2 districts (Tehri Garhwal and Uttarkashi), so their distinction cannot be confounded by district.
     - Hindi is spread across 74 districts nationally.
5. **Example phone outputs:**
   - `Hindi:test-00005:37` (1.9 s): `ʀ ɒ l i ɕ i a ɒ tʂ iː j y d iː kʰ a ɪ ʂ ɪ n`
   - `Rajasthani:test-00000:1` (2.0 s): `t̪ ɒ ә a k͡p̚ i ʔ ɒ ɾ ɒ t͡ɕ ɔ̃ ŋ ɴ ʌ k o uə`
   - `Kumaoni:validation-00000:92` (10.2 s): `ʁ uə ɒ ʔ i z ɒ ɾʲ iː ɕ iː b iː j a l̪ t̪ʰ i l æ t͡ɕ iː …`
   - These outputs include many phones that are implausible for Indo-Aryan speech, such as `ʀ ʁ ɴ k͡p̚ uə y`. This is recognition noise.
6. **Hindi vs regional (uni+bi+tri):**
   - Balanced accuracy is **0.521**. Hindi P/R/F1 = 0.23/0.08/0.12; Regional = 0.88/0.96/0.92.
   - Confusion (true Hindi = 125, true Regional = 875):
     - Hindi clips: 10 predicted Hindi, 115 predicted Regional.
     - Regional clips: 33 predicted Hindi, 842 predicted Regional.
   - The best configuration was unigrams only: balanced accuracy **0.634** (Hindi recall 0.53, Regional recall 0.74).
7. **8-way (uni+bi+tri):**
   - Balanced accuracy **0.235** (chance is 0.125); macro F1 0.230.
   - Recall by language: Hindi .26, Bhojpuri .43, Maithili .21, Chhattisgarhi .37, Rajasthani .09, Garhwali .25, Khariboli .14, Kumaoni .14.
8. **Ablation (balanced accuracy, Task A / Task B):**

   | Features | Task A | Task B |
   |---|---|---|
   | uni | .634 | .218 |
   | bi | .525 | .223 |
   | tri | .511 | .192 |
   | uni+bi | .579 | .235 |
   | uni+bi+tri | .521 | .235 |

   What little signal there is comes from individual phones (inventory and rate), not from sequencing. Adding trigrams adds sparsity, not signal.
9. **Top confusion pairs (true→pred, out of 125):**
   - Rajasthani→Garhwali 30, Khariboli→Kumaoni 30, Kumaoni→Khariboli 27, Maithili→Bhojpuri 23, Kumaoni→Maithili 23, Hindi→Kumaoni 22.
   - Close-pair grouped CV (balanced accuracy): Bhojpuri/Maithili .62, Garhwali/Kumaoni .56, Hindi/Khariboli .64, Rajasthani/Khariboli .52.
10. **Top predictive phone patterns.** Each row reads pattern: coverage in the language → coverage in the other languages (enrichment vs others, enrichment vs Hindi), from a model fit on all data. Everything listed is a *predictive phone pattern*; none is linguistically interpreted, because the evaluation shows they do not generalize.
    - **Bhojpuri** (only target with a semi-coherent cluster):
      - b-a: 23% → 9% (2.6x, 2.7x vs Hindi)
      - b̞-a: 31% → 14% (2.2x)
      - t-a: 26% → 13% (1.9x, 2.5x vs Hindi)
      - a-t: 23% (4.2x vs Hindi)
      - a-l: 35% (3.7x vs Hindi)
      - also: ɡ, kʰ, b, l̪
      - A b/b̞+a cluster could reflect the copula बा, but that is an unverified hypothesis.
    - **Maithili:** l-a 42% (3.5x vs Hindi), tɕʰ 21% (3.3x), ɴ, o-t̪, tʂ-a, ɾ-a, tsʰ, e-iː, ʌ-ɾ-ɒ, l-a-ɡ.
    - **Chhattisgarhi:** h 29% (1.9x), tʰ, kʰ-a, a-b̞-e (10%, 4.3x), i-h, t̪ʰ, h-a, t̪ʰ-i, m, pʰ.
    - **Rajasthani:** k-o 15% (2.0x), j-e, j-a, iː-ɾ, t͡ɕ-i, n-ɒ, ʊ, ɒ-ɪ, m-i, ɾ-o.
    - **Garhwali:** t͡ɕ 40% (1.4x), ʌ-p 16% (2.3x), k-ʌ, ɴ, æ-n, d͡ʒ, t͡ɕ-i, uə-k, ɴ-ɒ, o-ŋ.
    - **Khariboli:** iː-tʂ, ð-ɪ, ɔ, e-p, uə-a-ɾ (8%, 3.3x), e-ɾ, a-p-ʌ, e-ɪ, e-ɾ-e, ɾʲ.
    - **Kumaoni:** ts 28% (2.0x), y 20% (2.6x), p-e, ɪ-k, k, o-uə, ts-a, e-ɾ, w, ɴ-d.
    - **Hindi:** ɻ̩ 22% (1.55x), x, kʰ-a-ɪ, p-a-ɾ, ɪ-i, iː-ʂ, tʂ-ɻ̩, b̥, ɒ-tʂ, b-i.
11. **Hindi vs regional patterns:**
    - Pointing to Hindi: ɻ̩, kʰ-a-ɪ, x, p-a-ɾ, ɪ-i, iː-ʂ, tʂ-ɻ̩.
    - Pointing to regional (useful for Hindi rejection): ɴ (61% vs 36%), l, l-a (31% vs 11%), ŋ, d, tʂʰ, tʂ-ʌ (14% vs 4%).
    - Enriched across 5–7 of the regional targets vs Hindi: b-uə, t-uə, ɒ-ɴ, tʂ-ʌ, l-a, a-ɳ.
    - **Caveat:** Hindi clips are about 25% shorter, so the higher regional coverage of many patterns is partly a length artifact.
12. **Shuffled-label control:** Task A 0.511, Task B 0.113, both at chance. There is no leakage. The real models sit only slightly above this floor.
13. **FINAL VERDICT: WEAK SIGNAL.** Hindi-vs-regional is 0.52–0.63 balanced accuracy, below the 80% bar.
14. **NEXT ACTION: ALLOSAURUS REPRESENTATION IS THE BOTTLENECK.**
    - Evidence:
      - Outputs are full of non-Indo-Aryan phones.
      - Unigrams beat n-grams, meaning the sequencing is too noisy to carry phonotactics.
      - Shuffled controls are clean, so this is not leakage.
      - Utterances (about 6 s, about 60 phones) are not too short for phonotactic LID in principle.
    - The weakness is the representation, not data volume, so more Allosaurus data is not recommended.
    - A follow-up could restrict Allosaurus to the Hindi inventory (`lang_id='hin'`) as a cheap check before abandoning the route.

## Control: Hindi phone inventory (`recognize(audio, "hin")`)

Everything is unchanged except the inventory: same 1,000 clips, district-grouped split, classifier and metrics. Results are in `data/allosaurus_lid_hin/`.

The implausible phones (ʀ ɴ k͡p̚ uə …) disappear, but generalization barely moves.

| Task | Universal (best) | Hindi inventory (best) | Delta |
|---|---|---|---|
| Hindi vs regional | 0.634 (uni) | 0.660 (uni) | +0.026 |
| 8-way | 0.235 (uni+bi+tri) | 0.249 (uni) | +0.014 |

Shuffled control: 0.510 / 0.101. Unigrams still beat bigrams and trigrams.

0.660 falls in the 0.65–0.75 "marginal" band. The gain over the universal inventory is within fold noise, so the decision is to **DROP Allosaurus for Boli**.
