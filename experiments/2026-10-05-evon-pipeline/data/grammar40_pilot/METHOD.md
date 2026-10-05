# Method — 40-parameter grammar pilot (frozen schema, 999-clip shared manifest)

Input: `prisma_transcript` of every row of `../shared_1k_audio_manifest.jsonl` (no resampling). Code: `scripts/grammar40_lexicon.py`, `scripts/grammar40_pilot.py`.
Outputs: `results.json` (8 languages x exactly 40 parameter objects), `report.md` (full ranked tables + cross-language summary).

## Frozen 40 classes
1. Copulas
2. Non-copular auxiliaries
3. Existential/possessive constructions
4. Modal auxiliaries
5. Negation particles
6. Negative auxiliaries
7. Tense morphology
8. Aspect morphology
9. Mood / imperative / subjunctive
10. Person agreement
11. Number agreement
12. Gender agreement
13. Honorific verb agreement
14. Infinitives / non-finite forms
15. Participles / converbs
16. Causative / passive morphology
17. Resultative / completive auxiliaries
18. Light / compound verb patterns
19. Basic pronouns
20. Oblique pronouns
21. Genitive / possessive pronouns
22. Honorific pronouns
23. Reflexive / reciprocal pronouns
24. Demonstratives
25. Interrogatives
26. Question / tag particles
27. Relative / correlative forms
28. Indefinite / quantifier paradigms
29. Case / postposition system
30. Plural markers
31. Numeral classifiers / count markers
32. Locative / deictic adverbs
33. Temporal / directional adverbs
34. Conjunctions
35. Subordinators / complementizers
36. Discourse / emphatic / topic / focus particles
37. Vocative / address particles
38. Definiteness / determiner markers
39. Comparative / degree markers
40. Clitics / enclitics

## Detection
Hand-written lexicon + generated verb paradigms + token-pair rules (not derived from this sample). Each marker belongs to one class; classes 10/11/12
(person/number/gender agreement) are cross-cutting inflection patterns matched additively, so their forms also count under 1/7/8/9 (overlap by design).
Known noise: stem+ending generation over-matches some nouns (e.g. खाना as infinitive). Prisma output is Hindi-normalised, so dialect-only forms are mostly absent.

## Per language x parameter (all 0-100)
- coverage = % of the language's rows with >=1 marker (100 at >=50%).
- distinctiveness = Cohen's h between the language's firing rate and the mean of the other 7 languages, minus 1 SE (noise penalty), scaled so h=0.6 -> 100.
- precision = balanced posterior P(language | marker fires) = r_L / sum of all 8 rates, rescaled above chance (1/8); null if <3 firing rows in the language.
- stability = 1 - (excess-over-binomial-noise SD of the firing rate across 3 shard-folds / mean rate), needs >=2 folds with >=25 rows and >=5 firing rows, else null.
- ablation_value = drop in that language's one-vs-rest AUC when the parameter is removed from a 40-feature logistic regression (5-fold stratified CV x 8 repeats,
  all 8 languages jointly); score = 100 * (mean drop - SD across repeats) / 0.03, clipped to [0,100]. Null if the class fires in <5 rows overall.
- exact_language_score = 0.40 ablation + 0.25 distinctiveness + 0.15 precision + 0.10 coverage + 0.10 stability; null components are dropped and weights
  renormalised; if ablation is null the score is capped at 19. Class never observed in the corpus -> 0.
- family_score = identical pipeline with the 5 family groups (family-label AUC drop, family rates, stability across member languages, or shard-folds if single-language family).
- rank = competition rank within the language (ties share a rank). status: >=80 core, 60-79 strong, 40-59 supporting, 20-39 weak, 1-19 negligible, 0 zero.
- notes record signal direction: `present` (language fires more than others) vs `absent` (the score comes from the language *lacking* a form others have; no observed marker explains it).

## Family grouping (assumption — the repo defines no F-codes)
Bihari: Bhojpuri, Maithili | Eastern-Hindi: Chhattisgarhi | Rajasthani: Rajasthani | Pahari: Garhwali, Kumaoni | Western-Hindi: Hindi, Khariboli.
Single-language families make family score ~ exact score by construction.

## Limits
~125 rows/language, one sample, one seed; 3 of 8 languages come from 1-2 districts. Scores are pilot-grade; AUC drops of ~0.01 are near the noise floor.
Weights/scales are the pre-specified suggestion, not validated. Mean full-model OvR AUC is only 0.65-0.81.
