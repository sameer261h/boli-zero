# 18: Evidence-grounded regional speech recognition for Evon

## Design decision

Evon should receive a small, transcript-specific set of raw linguistic clues and decide what they suggest. The application should not tell Evon a predicted dialect name as a fact. A compact, bounded classification result can be requested before the spoken reply, but it must be checked against held-out data before anyone treats Evon's self-reported confidence as calibrated.

This design uses the existing detector as a conservative routing and confidence ceiling, not as a verdict handed to Evon. The detector chooses which corpus-derived marker inventories to inspect and which of the four existing confidence levels are even available. The prompt contains only matched text, its local transcript context, and anonymous marker evidence. Evon gets no dialect names, meanings, z-scores, or application-generated conclusion. It must infer what the forms suggest from its own language knowledge. This preserves the requested reasoning constraint while preventing Evon from claiming a more specific result than the existing evidence can support.

The constraint is useful for the model's own interpretation, but it cannot by itself provide a reliable or calibrated language classifier. If an application decision depends on a dependable label, a separately evaluated classifier must own that decision. Evon's short classification is a reasoned interpretation to be measured, not ground truth.

## What the data supports

The fingerprint report compares 24,957 paired human and Prisma transcripts across 19 varieties. It finds repeatable transformations such as Garhwali `यख` being deleted or read as `एक`, Rajasthani `अठे` being deleted or changed to `अटे`, and Rajasthani or Marwari progressive forms such as `रियो`, `रेहो`, and `रहियो` being rendered as standard-Hindi forms such as `रही`. These are transcript-specific clues when the dialectal form survives Prisma. A deletion cannot be shown to Evon as a token that is no longer present, and a generic normalization such as `है`↔`हैं` is shared across dialects, so neither should be presented as dialect-specific evidence.

The audit's strongest lexical examples include Bhojpuri `बा` (z=43.0) and `एगो` (z=15.1). Their z-scores measure how strongly a token is overrepresented in the audit corpus, not the probability that a new utterance is Bhojpuri. Some high-scoring entries are common grammatical words, including `के`; a high score alone does not make a token safe to interpret as an exclusive dialect marker. The audit also lists suffixes, but suffixes alone are weak evidence because short endings can occur in many words and the inventory includes very low-count forms.

Earlier single-utterance classification work was poor for most varieties, and the current detector remains imperfect. The more recent detector document reports four routing levels: exact variety, named regional profile, generic regional-Hindi, and Hindi/default. It marks Bhojpuri, Garhwali, and Chhattisgarhi as the strongest independent profiles; routes Khariboli, Kumaoni, and Bundeli to generic regional-Hindi; and places Jaipuri in the Hindi/default tier because its sample is tiny and its prediction unstable. These levels should bound claims in Evon's returned classification. They do not prove that any one transcript is correctly classified.

## Evidence selection

Build a curated marker inventory from the audit and the explained transformation report. Keep each marker's source variety, token or short pattern, count, log-odds score where available, and known caveats in application-side metadata. Evon must not receive the source-variety field or numeric scores. For each transcript, normalize Unicode to NFC and apply only the documented cosmetic spelling normalizations. Do not stem, translate, or silently repair the words before matching.

For lexical entries, start with a conservative inventory threshold of at least 25 occurrences and z-score at least 8.0. This is a candidate-generation rule, not a confidence guarantee. Exclude generic orthographic variants, common words that recur across dialects, and tokens listed as meaning-ambiguous in the wrong-substitutions audit unless a human-reviewed context rule establishes that the instance is useful. `के`, `है`, `हैं`, `यहाँ`, spelling-only `यहां`/`यहाँ`, and other cross-dialect universal patterns must not count as independent dialect clues. Tokens such as `खातिर`, where the same form can support different meanings or sources, are omitted without a validated context rule.

For each hit, retain the exact transcript spelling and a short window of neighboring words, with the hit bracketed. This gives Evon context to assess whether the word fits the sentence. Count repeated copies of one token as one marker type, with its occurrence count shown; repetition in one sentence must not masquerade as several independent clues. Count two evidence types as independent only when they have different lexical roots or distinct grammatical constructions. Do not count multiple spellings of the same root, a suffix and its host word, or a token repeated several times as separate types.

Keep at most three marker types, choosing the strongest distinct and contextually clear matches. If candidates tie, prefer a marker whose corpus examples show a consistent transformation over one whose evidence is only a raw frequency association. Do not pad an empty or weak evidence set with lower-scoring matches. Deletions, substitutions, and insertions from paired references can guide which surviving forms belong in the curated inventory, but an ASR transformation does not prove that the spoken source word is present in the current transcript.

When available, inspect the calibrated transcript detector and preserve its existing four-level hierarchy. The inventory lookup may inspect marker sets for the detector's leading candidate and runner-up, but the prompt must not expose either candidate's name or ranking. If the two candidate inventories produce indistinguishable clues, Evon should receive the clues without a label and the result must be capped at the broader level supported by the existing hierarchy. If the detector has no viable regional signal, do not surface a forced dialect marker set.

```text
evidence = match_curated_markers(NFC(transcript))
evidence = remove_universal_orthography_and_ambiguous_hits(evidence)
evidence = collapse_repeats_by_marker_type(evidence)
evidence = choose_up_to_three_distinct_contextual_hits(evidence)

level = existing_four_level_detector(transcript)
if evidence is empty:
    level_cap = LEVEL_4
elif fewer_than_two_independent_marker_types(evidence):
    level_cap = LEVEL_3
else:
    level_cap = LEVEL_1

level_cap = broader_of(level, level_cap)  # higher level number means broader claim
send_single_user_turn(transcript, anonymous_raw_evidence(evidence), level_cap=level_cap)
```

The caps above are intentionally conservative starting rules for evaluation, not already validated operating thresholds. A single marker type can support a tentative regional reading, but it cannot justify an exact variety claim. Exact variety requires both the existing Level 1 detector gate and at least two independent, contextually coherent marker types. Level 2 requires the existing named-profile gate plus multiple clues compatible with that profile. One clue, conflicting clues, or an absent detector signal stays at Level 3 or Level 4. A short Hindi-like utterance with no usable clues should remain at Hindi/default even when its recording came from a regional variety in the dataset.

## What to add to Evon's single user turn

Keep the existing single-message, no-system-prompt constraint. Add one compact evidence section between the conversation history and `User said:`. It should contain the original transcript, each selected surface form with a brief unaltered context window, and a neutral instruction to assess whether the forms fit standard Hindi, a regional variety, or remain unclear. Do not include dialect names, glosses, corpus rankings, detector probabilities, or explanatory labels such as "Bhojpuri marker." Those would pre-answer the question.

Evon should return a small parseable header followed by the existing reply field, for example:

```text
LANGUAGE_LEVEL: exact | profile | regional_hindi | hindi_default
LANGUAGE_GUESS: <name, or unknown>
CONFIDENCE: high | medium | low
EVIDENCE_IDS: <zero or more supplied evidence IDs>
REPLY: <one short spoken response>
```

The instruction should say: use only supplied evidence and the transcript; compare the forms with ordinary Hindi and your language knowledge; do not infer a dialect from geography, topic, or a single common word; select the broadest level that fits; use `unknown` and low confidence when evidence is insufficient or conflicts; never reveal private reasoning; and keep the reply behavior and `REPLY:` extraction contract unchanged. A brief, bounded header gives the application a record of Evon's conclusion without requesting free-form chain-of-thought. The caller should parse only the fixed fields and continue extracting the first reply line after `REPLY:`. If output is malformed, fall back to the reply-only path and treat the language classification as unknown.

Evon's confidence word is not a calibrated probability. It must be capped by the detector hierarchy and assessed later against held-out, human-verified labels. No confidence level should be described as "genuine" until that assessment establishes reliability. In particular, repeated tokens from one short utterance, ASR corruption, or a common form cannot turn low evidence into high confidence.

## Walk-throughs from paired transcripts

The examples below are literal rows from the committed JSONL files. Their gold dialect comes from the dataset row, so these examples illustrate what evidence selection would send; they do not measure whether Evon reaches the right answer on unseen data.

### Clearer case: Bhojpuri, row 28

The Prisma transcript is: `बस स्टैंड बा जेना में पाँच छगो बस खड़ा बारी सान जोना के आयशर कंपनी के बाड़ी सान उजर कलर के एगो`.

After excluding generic forms such as `के`, the conservative inventory finds the raw forms `बा` and `एगो`. The audit reports `बा` with z=43.0 and `एगो` with z=15.1. The evidence section would show the exact forms and their short contexts, without names or scores. Evon could reasonably infer a non-standard regional construction and consider Bhojpuri among the possibilities. The transcript is visibly noisy, and the single marker types are sparse; therefore the hoped-for output is a regional/profile-level or tentative variety reading, not a high-confidence exact label. The existing detector level would decide whether any exact/profile claim is even allowed.

### Marginal case: Khariboli, row 7

The Prisma transcript is: `यहाँ पर एक प्रतिमा दिखाई दे रही है और कुछ व्यक्ति दिखाई दे रहे हैं कई सारे पेड़ पौधे दिखाई दे रहे हैं`.

The sentence has no hit that clears the initial lexical threshold. `यहाँ` and common Hindi sentence material are excluded, and the wording is close to standard Hindi. The evidence block is empty. Evon should choose Hindi/default or `unknown`, with low confidence if the output requires a confidence word. It should not announce that the input is non-Hindi simply because the dataset's source row is Khariboli. This follows the detector document's assignment of Khariboli to Level 3 only when there is actual generic regional evidence; absent such evidence, Level 4 remains appropriate.

### Weak detector case: Jaipuri, row 1

The Prisma transcript is: `एक पहाड़ी भी दिख रही है और एक व्यक्ति भी दिखाई पड़ रहा है`.

The audit's Jaipuri top markers are all below the proposed lexical threshold, and none appears here as a useful distinctive clue. The transcript reads as ordinary Hindi and the detector document places Jaipuri at Level 4 because its sample is small and its prediction unstable. The prompt should include no dialect clues and cap the result at Hindi/default. Evon should not infer Jaipuri from this sentence. This example shows why the design needs an honest empty-evidence path.

The examples also show a limit in the source material: row 28 supports two raw lexical clues but does not establish that Evon will infer correctly, while the marginal and weak cases offer no useful marker at all. The evaluation must measure that behavior rather than treating these illustrative rows as proof.

## Evaluation required before operational use

Before enabling this prompt in the live reply path, compare the current prompt with the evidence prompt on held-out, group-disjoint transcripts. Freeze the example rows and marker-selection rules before evaluation. Include short utterances, noisy Prisma outputs, common-word collisions, varieties near Hindi, and the weak or unstable detector cases. Have qualified speakers adjudicate the intended variety and whether each surfaced clue is valid in context.

Report separately: correct exact-variety identification, correct hierarchy-level choice, false non-Hindi claims on Hindi-like input, confidence calibration, empty-evidence abstention, and whether the final spoken answer improves. Compare three conditions: the current prompt, raw evidence only, and a direct-label baseline for measurement. The direct-label condition is an evaluation control, not the recommended production prompt. If raw evidence does not improve correct hierarchy-level selection or causes more false certainty, keep the current prompt and revise the inventory or abandon this route. Do not call Evon or Prisma APIs as part of this design work.

## Plain-English version

Prisma writes down what it hears using Hindi spelling, which can hide the way a regional speaker actually talks. The project has examples of words and grammar that Prisma often changes in particular ways. We can search the transcript for a few clear clues that survived and show Evon those exact words in their sentence.

Evon gets the words without being told which dialect they supposedly prove. It compares them with ordinary Hindi and uses what it knows about regional speech to decide whether the sentence sounds standard, regional, or too unclear to tell. If the sentence contains no useful clue, the system lets it remain Hindi or unknown instead of guessing.

The detector already has four levels of certainty, from a specific variety down to the Hindi default. Those levels limit how specific Evon's answer can be. Evon can record a short language guess and confidence label without writing out its private reasoning, then give its usual spoken reply.

This is a design to test, not proof that Evon can identify every dialect. The examples show why it may help and where it has nothing useful to work with. A held-out review by people who know the varieties must show that Evon gets more answers right and does not become more confident when the clues are weak.

## Sources

- `docs/2026-10-05-evon-pipeline/06-prisma-fingerprint-dialect-transformation-analysis.md`
- `experiments/2026-10-05-evon-pipeline/data/prisma_fingerprint/regional_fingerprint_audit/audit_results.json`
- `experiments/2026-10-05-evon-pipeline/data/prisma_fingerprint/analysis/per_dialect_results.json`
- `experiments/2026-10-05-evon-pipeline/data/prisma_fingerprint/analysis/cross_dialect_universal_substitutions.json`
- `experiments/2026-10-05-evon-pipeline/data/prisma_fingerprint/regional_fingerprint_audit/needs_fixing_wrong_substitutions.csv`
- `docs/2026-10-05-evon-pipeline/09-v1-regional-speech-detector.md`
- `docs/2026-10-05-evon-pipeline/12-safe-vs-ambiguous-classification-design.md`
- `docs/2026-10-05-evon-pipeline/14-phonetic-filter-wrong-vs-unsure.md`
- `src/boli_zero/conversation.py`
- `experiments/2026-10-05-evon-pipeline/data/prisma_fingerprint/Bhojpuri.jsonl`
- `experiments/2026-10-05-evon-pipeline/data/prisma_fingerprint/Khariboli.jsonl`
- `experiments/2026-10-05-evon-pipeline/data/prisma_fingerprint/Jaipuri.jsonl`
