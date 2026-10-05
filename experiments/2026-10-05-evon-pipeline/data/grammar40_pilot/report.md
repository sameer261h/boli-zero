# 40-parameter grammar pilot (999-clip shared manifest, prisma_transcript)


## Hindi (family: Western-Hindi; n=124; full-model OvR AUC=0.747)
- materially useful (score>=40): **4**; weak-or-better (>=20): 13; effectively zero (<1): 7
- top 5: Copulas (51.6); Participles / converbs (47.0); Non-copular auxiliaries (44.9); Locative / deictic adverbs (41.2); Gender agreement (36.9)
- of the useful ones, absence-driven: none
- zero: Mood / imperative / subjunctive, Reflexive / reciprocal pronouns, Light / compound verb patterns, Negative auxiliaries, Honorific verb agreement, Question / tag particles, Clitics / enclitics
- exact vs family: Copulas exact 51.6 / family 79.1; Participles / converbs exact 47.0 / family 34.0; Non-copular auxiliaries exact 44.9 / family 36.4; Locative / deictic adverbs exact 41.2 / family 48.2; Gender agreement exact 36.9 / family 39.4

| rank | parameter | coverage% | distinct | precision | stability | ablation | exact | family | status | observed markers |
|--|--|--|--|--|--|--|--|--|--|--|
| 1 | 1. Copulas | 96 | 84.8 | 3.3 | 95.7 | 25.9 | 51.6 | 79.1 | supporting | present | हूं [2 in Hindi / 3 elsewhere]; हैं [44 in Hindi / 152 elsewhere]; है [105 in Hindi / 387 elsewhere]; हो [4 in Hindi / 43 elsewhere] |
| 2 | 15. Participles / converbs | 39.5 | 67.8 | 15.4 | 100 | 24.7 | 47.0 | 34.0 | supporting | present | हुई [21 in Hindi / 51 elsewhere]; हुआ [26 in Hindi / 64 elsewhere]; हुए [14 in Hindi / 49 elsewhere] |
| 3 | 2. Non-copular auxiliaries | 57.3 | 78.7 | 11.5 | 85.1 | 12.5 | 44.9 | 36.4 | supporting | present | रही [32 in Hindi / 84 elsewhere]; रहा [42 in Hindi / 115 elsewhere]; रहे [19 in Hindi / 96 elsewhere] |
| 4 | 32. Locative / deictic adverbs | 59.7 | 65.4 | 8.6 | 90.2 | 11.4 | 41.2 | 48.2 | supporting | present | चारों [4 in Hindi / 5 elsewhere]; सामने [15 in Hindi / 34 elsewhere]; यहां [42 in Hindi / 115 elsewhere]; पीछे [8 in Hindi / 24 elsewhere] |
| 5 | 12. Gender agreement | 67.7 | 71.3 | 7.8 | 78.6 | 0 | 36.9 | 39.4 | weak | present | लिखा [8 in Hindi / 9 elsewhere]; बनी [5 in Hindi / 8 elsewhere]; रही [32 in Hindi / 84 elsewhere]; बैठा [2 in Hindi / 5 elsewhere] |
| 6 | 16. Causative / passive morphology | 34.7 | 63.4 | 16.4 | 98.1 | 0 | 35.1 | 35.0 | weak | present | दिखाया [2 in Hindi / 0 elsewhere]; दिखाई [37 in Hindi / 82 elsewhere]; लगाई [2 in Hindi / 4 elsewhere] |
| 7 | 31. Numeral classifiers / count markers | 0 | 63.3 | null | null | 20.7 | 32.1 | 6.1 | weak | absent |  |
| 8 | 37. Vocative / address particles | 2.4 | 50.5 | 0 | null | 29.2 | 27.5 | 54.9 | weak | absent | ए [2 in Hindi / 13 elsewhere] |
| 9 | 17. Resultative / completive auxiliaries | 11.3 | 35.4 | 25.9 | 100 | 0 | 25.0 | 9.4 | weak | present | गई [5 in Hindi / 5 elsewhere]; गया [8 in Hindi / 17 elsewhere] |
| 10 | 39. Comparative / degree markers | 41.9 | 28.2 | 5.9 | 80.7 | 0 | 24.4 | 23.4 | weak | present | काफी [14 in Hindi / 26 elsewhere]; बहुत [41 in Hindi / 199 elsewhere] |
| 11 | 34. Conjunctions | 45.2 | 10.4 | 3.1 | 100 | 0 | 22.1 | 20.3 | weak | present | आ [12 in Hindi / 41 elsewhere]; और [46 in Hindi / 253 elsewhere]; या [2 in Hindi / 20 elsewhere] |
| 12 | 11. Number agreement | 25.8 | 0 | 0 | 86 | 16.5 | 20.4 | 16.1 | weak | absent | बैठते [2 in Hindi / 1 elsewhere]; पीले [2 in Hindi / 3 elsewhere]; करते [2 in Hindi / 5 elsewhere]; लगे [10 in Hindi / 31 elsewhere] |
| 13 | 20. Oblique pronouns | 14.5 | 20.9 | 12.3 | 100 | 0 | 20.0 | 30.5 | negligible | present | मुझे [3 in Hindi / 1 elsewhere]; हमें [9 in Hindi / 19 elsewhere]; उसमें [2 in Hindi / 6 elsewhere]; इसमें [6 in Hindi / 20 elsewhere] |
| 14 | 29. Case / postposition system | 79 | 0 | 0.8 | 94.6 | 0 | 19.6 | 20.4 | negligible | present | साथ [2 in Hindi / 6 elsewhere]; पे [14 in Hindi / 59 elsewhere]; पर [27 in Hindi / 123 elsewhere]; को [8 in Hindi / 37 elsewhere] |
| 15 | 5. Negation particles | 0 | 42 | null | null | 8.6 | 18.6 | 2.3 | negligible | absent |  |
| 16 | 7. Tense morphology | 35.5 | 15.6 | 4.7 | 66.8 | 0 | 18.4 | 21.1 | negligible | present | किया [6 in Hindi / 5 elsewhere]; लिखा [8 in Hindi / 9 elsewhere]; बनी [5 in Hindi / 8 elsewhere]; बैठा [2 in Hindi / 5 elsewhere] |
| 17 | 28. Indefinite / quantifier paradigms | 35.5 | 0 | 2 | 100 | 0 | 17.4 | 18.4 | negligible | present | किसी [3 in Hindi / 2 elsewhere]; सारे [14 in Hindi / 39 elsewhere]; सारी [9 in Hindi / 37 elsewhere]; कुछ [14 in Hindi / 74 elsewhere] |
| 18 | 25. Interrogatives | 0 | 30.7 | null | null | 12.3 | 16.8 | 0.3 | negligible | absent |  |
| 19 | 36. Discourse / emphatic / topic / focus particles | 37.1 | 0 | 0.6 | 91.3 | 0 | 16.6 | 17.4 | negligible | present | ही [13 in Hindi / 46 elsewhere]; भी [37 in Hindi / 206 elsewhere]; अच्छा [4 in Hindi / 51 elsewhere] |
| 20 | 24. Demonstratives | 32.3 | 0.3 | 2.7 | 95.2 | 0 | 16.5 | 24.7 | negligible | present | इस [15 in Hindi / 18 elsewhere]; यह [12 in Hindi / 42 elsewhere]; ये [17 in Hindi / 105 elsewhere] |
| 21 | 27. Relative / correlative forms | 21.8 | 2.5 | 4.1 | 100 | 0 | 15.6 | 16.7 | negligible | present | जैसा [5 in Hindi / 13 elsewhere]; जहां [5 in Hindi / 15 elsewhere]; जो [14 in Hindi / 73 elsewhere] |
| 22 | 4. Modal auxiliaries | 7.3 | 4.7 | 10.4 | 89.4 | 0 | 13.1 | 6.1 | negligible | present | सकते [9 in Hindi / 21 elsewhere] |
| 22 | 10. Person agreement | 5.6 | 0 | 0 | 100 | 4.9 | 13.1 | 13.7 | negligible | absent | हूं [2 in Hindi / 3 elsewhere]; देखो [2 in Hindi / 6 elsewhere]; हो [4 in Hindi / 43 elsewhere] |
| 24 | 22. Honorific pronouns | 4 | 0 | 7.8 | 100 | 0 | 12.0 | 16.5 | negligible | present | आपको [2 in Hindi / 7 elsewhere]; आप [4 in Hindi / 18 elsewhere] |
| 25 | 14. Infinitives / non-finite forms | 9.7 | 0 | 0 | 100 | 0 | 11.9 | 11.9 | negligible | absent | देखने [6 in Hindi / 22 elsewhere]; पानी [4 in Hindi / 25 elsewhere] |
| 26 | 21. Genitive / possessive pronouns | 5.6 | 0 | 0 | 100 | 0 | 11.1 | 12.3 | negligible | absent | इसके [3 in Hindi / 7 elsewhere] |
| 27 | 30. Plural markers | 19.4 | 0 | 0 | 67.4 | 0 | 10.6 | 13.5 | negligible | present | गाडियां [3 in Hindi / 2 elsewhere]; कुर्सियां [3 in Hindi / 5 elsewhere]; खिडकियां [2 in Hindi / 7 elsewhere]; लोग [9 in Hindi / 65 elsewhere] |
| 28 | 19. Basic pronouns | 5.6 | 0 | 5.8 | 79.9 | 0 | 10.0 | 0.6 | negligible | present | मैं [2 in Hindi / 2 elsewhere]; हम [4 in Hindi / 24 elsewhere] |
| 29 | 38. Definiteness / determiner markers | 0 | 19.6 | null | null | 3.1 | 8.2 | 1.3 | negligible | absent |  |
| 30 | 8. Aspect morphology | 6.5 | 16.9 | 0 | 7.6 | 0 | 6.3 | 11.3 | negligible | absent | बैठते [2 in Hindi / 1 elsewhere]; पीले [2 in Hindi / 3 elsewhere]; करते [2 in Hindi / 5 elsewhere] |
| 31 | 35. Subordinators / complementizers | 8.1 | 0 | 6.6 | 30.3 | 0 | 5.6 | 16.9 | negligible | present | कि [9 in Hindi / 37 elsewhere] |
| 32 | 33. Temporal / directional adverbs | 0.8 | 13 | null | null | 1.2 | 5.2 | 4.7 | negligible | absent |  |
| 33 | 3. Existential/possessive constructions | 0 | 4.1 | null | null | 0 | 1.4 | 4.6 | negligible | absent |  |
| 34 | 9. Mood / imperative / subjunctive | 1.6 | 0 | null | null | 0 | 0.4 | 0.9 | zero | absent | देखो [2 in Hindi / 6 elsewhere] |
| 34 | 23. Reflexive / reciprocal pronouns | 1.6 | 0 | null | null | 0 | 0.4 | 10.8 | zero | absent | अपने [2 in Hindi / 3 elsewhere] |
| 36 | 18. Light / compound verb patterns | 0.8 | 0 | null | null | 0 | 0.2 | 0.2 | zero | absent |  |
| 37 | 6. Negative auxiliaries | 0 | null | null | null | 0 | 0.0 | 0.0 | zero | - |  |
| 37 | 13. Honorific verb agreement | 0 | null | null | null | 0 | 0.0 | 0.0 | zero | - |  |
| 37 | 26. Question / tag particles | 0 | 0 | null | null | null | 0.0 | 0.0 | zero | absent |  |
| 37 | 40. Clitics / enclitics | 0 | 0 | null | null | null | 0.0 | 0.0 | zero | absent |  |

## Bhojpuri (family: Bihari; n=125; full-model OvR AUC=0.730)
- materially useful (score>=40): **3**; weak-or-better (>=20): 12; effectively zero (<1): 7
- top 5: Aspect morphology (77.4); Gender agreement (60.7); Numeral classifiers / count markers (43.1); Non-copular auxiliaries (36.8); Case / postposition system (32.0)
- of the useful ones, absence-driven: Gender agreement
- zero: Basic pronouns, Question / tag particles, Honorific pronouns, Interrogatives, Negative auxiliaries, Honorific verb agreement, Clitics / enclitics
- exact vs family: Aspect morphology exact 77.4 / family 62.0; Gender agreement exact 60.7 / family 59.1; Numeral classifiers / count markers exact 43.1 / family 60.1; Non-copular auxiliaries exact 36.8 / family 29.3; Case / postposition system exact 32.0 / family 23.6

| rank | parameter | coverage% | distinct | precision | stability | ablation | exact | family | status | observed markers |
|--|--|--|--|--|--|--|--|--|--|--|
| 1 | 8. Aspect morphology | 31.2 | 71.4 | 21.9 | 100 | 100 | 77.4 | 62.0 | strong | present | देता [3 in Bhojpuri / 0 elsewhere]; जाले [3 in Bhojpuri / 0 elsewhere]; आवता [2 in Bhojpuri / 0 elsewhere]; लगेले [2 in Bhojpuri / 0 elsewhere] |
| 2 | 12. Gender agreement | 32 | 25.5 | 0 | 79.4 | 100 | 60.7 | 59.1 | strong | absent | देता [3 in Bhojpuri / 0 elsewhere]; आवता [2 in Bhojpuri / 0 elsewhere]; करता [5 in Bhojpuri / 2 elsewhere]; जाई [2 in Bhojpuri / 1 elsewhere] |
| 3 | 31. Numeral classifiers / count markers | 16.8 | 53.5 | 29.4 | 100 | 29.8 | 43.1 | 60.1 | supporting | present | एगो [18 in Bhojpuri / 20 elsewhere]; ठे [2 in Bhojpuri / 2 elsewhere] |
| 4 | 2. Non-copular auxiliaries | 28.8 | 0 | 0 | 100 | 52.7 | 36.8 | 29.3 | weak | absent | लागल [17 in Bhojpuri / 4 elsewhere]; रहल [2 in Bhojpuri / 3 elsewhere]; रहा [10 in Bhojpuri / 147 elsewhere]; रहे [6 in Bhojpuri / 109 elsewhere] |
| 5 | 29. Case / postposition system | 84 | 22.1 | 1.8 | 100 | 15.5 | 32.0 | 23.6 | weak | present | ले [8 in Bhojpuri / 9 elsewhere]; खातिर [2 in Bhojpuri / 3 elsewhere]; से [27 in Bhojpuri / 82 elsewhere]; के [51 in Bhojpuri / 177 elsewhere] |
| 6 | 16. Causative / passive morphology | 5.6 | 43.8 | 0 | 100 | 16 | 28.5 | 14.1 | weak | absent | दिखाई [5 in Bhojpuri / 114 elsewhere] |
| 7 | 32. Locative / deictic adverbs | 24 | 33.6 | 0 | 100 | 11.2 | 27.7 | 17.6 | weak | absent | आगे [3 in Bhojpuri / 11 elsewhere]; वहां [3 in Bhojpuri / 13 elsewhere]; नीचे [6 in Bhojpuri / 42 elsewhere]; बीच [2 in Bhojpuri / 14 elsewhere] |
| 8 | 38. Definiteness / determiner markers | 4 | 14.1 | 29.7 | 100 | 13.8 | 24.3 | 7.9 | weak | present |  |
| 9 | 7. Tense morphology | 27.2 | 0 | 0.3 | 59.1 | 31.4 | 24.0 | 36.1 | weak | present | रखल [5 in Bhojpuri / 2 elsewhere]; करल [2 in Bhojpuri / 1 elsewhere]; लिखल [3 in Bhojpuri / 2 elsewhere]; लगल [6 in Bhojpuri / 6 elsewhere] |
| 10 | 18. Light / compound verb patterns | 4.8 | 18.7 | 31.4 | 100 | 5.5 | 22.5 | 8.4 | weak | present | ले ले [3 in Bhojpuri / 0 elsewhere]; पूजा करता [2 in Bhojpuri / 1 elsewhere] |
| 11 | 34. Conjunctions | 26.4 | 22.4 | 0 | 100 | 0 | 20.9 | 27.8 | weak | absent | लेकिन [3 in Bhojpuri / 3 elsewhere]; आ [5 in Bhojpuri / 48 elsewhere]; या [2 in Bhojpuri / 20 elsewhere]; और [26 in Bhojpuri / 273 elsewhere] |
| 12 | 1. Copulas | 78.4 | 0 | 0.1 | 100 | 0 | 20.0 | 20.1 | weak | present | बाटे [14 in Bhojpuri / 1 elsewhere]; बा [51 in Bhojpuri / 13 elsewhere]; ह [8 in Bhojpuri / 5 elsewhere]; था [3 in Bhojpuri / 4 elsewhere] |
| 13 | 15. Participles / converbs | 9.6 | 30.1 | 0 | 84.5 | 5.1 | 19.9 | 7.6 | negligible | absent | जाके [5 in Bhojpuri / 0 elsewhere]; हुआ [6 in Bhojpuri / 84 elsewhere] |
| 14 | 36. Discourse / emphatic / topic / focus particles | 33.6 | 0 | 0 | 100 | 0 | 16.7 | 17.4 | negligible | absent | अच्छा [14 in Bhojpuri / 41 elsewhere]; भी [27 in Bhojpuri / 216 elsewhere]; तो [3 in Bhojpuri / 24 elsewhere]; ही [4 in Bhojpuri / 55 elsewhere] |
| 15 | 39. Comparative / degree markers | 29.6 | 0 | 0 | 100 | 0 | 15.9 | 26.5 | negligible | absent | ढेर [5 in Bhojpuri / 6 elsewhere]; एकदम [2 in Bhojpuri / 4 elsewhere]; खूब [3 in Bhojpuri / 8 elsewhere]; बहुत [27 in Bhojpuri / 213 elsewhere] |
| 16 | 24. Demonstratives | 30.4 | 0 | 1.7 | 92.8 | 0 | 15.6 | 16.2 | negligible | present | इ [10 in Bhojpuri / 10 elsewhere]; ई [5 in Bhojpuri / 10 elsewhere]; वो [5 in Bhojpuri / 20 elsewhere]; इस [4 in Bhojpuri / 29 elsewhere] |
| 17 | 28. Indefinite / quantifier paradigms | 29.6 | 0 | 0 | 90.7 | 0 | 15.0 | 16.7 | negligible | absent | सब [9 in Bhojpuri / 38 elsewhere]; कोई [5 in Bhojpuri / 24 elsewhere]; कई [5 in Bhojpuri / 26 elsewhere]; सारा [8 in Bhojpuri / 42 elsewhere] |
| 18 | 11. Number agreement | 23.2 | 0 | 0 | 100 | 0 | 14.6 | 15.2 | negligible | absent | जाले [3 in Bhojpuri / 0 elsewhere]; लगेले [2 in Bhojpuri / 0 elsewhere]; देखे [5 in Bhojpuri / 6 elsewhere]; कहीं [2 in Bhojpuri / 3 elsewhere] |
| 19 | 30. Plural markers | 19.2 | 0 | 0 | 100 | 0 | 13.8 | 13.5 | negligible | absent | लडकियां [2 in Bhojpuri / 2 elsewhere]; लोगों [2 in Bhojpuri / 6 elsewhere]; लोग [12 in Bhojpuri / 62 elsewhere] |
| 20 | 37. Vocative / address particles | 12 | 0 | 0.2 | 100 | 0 | 12.4 | 16.4 | negligible | present | ए [3 in Bhojpuri / 12 elsewhere]; हे [4 in Bhojpuri / 27 elsewhere]; जी [6 in Bhojpuri / 58 elsewhere] |
| 21 | 5. Negation particles | 5.6 | 3.1 | 11.5 | 85.2 | 0 | 12.1 | 17.0 | negligible | present | ना [4 in Bhojpuri / 4 elsewhere]; नहीं [4 in Bhojpuri / 13 elsewhere] |
| 22 | 27. Relative / correlative forms | 16.8 | 0 | 0 | 74.5 | 0 | 10.8 | 14.9 | negligible | absent | जब [2 in Bhojpuri / 2 elsewhere]; जैसे [3 in Bhojpuri / 12 elsewhere]; जे [2 in Bhojpuri / 11 elsewhere]; जहां [3 in Bhojpuri / 17 elsewhere] |
| 22 | 35. Subordinators / complementizers | 4 | 0 | 0 | 100 | 0 | 10.8 | 8.4 | negligible | absent | ताकि [2 in Bhojpuri / 2 elsewhere]; कि [3 in Bhojpuri / 43 elsewhere] |
| 24 | 14. Infinitives / non-finite forms | 10.4 | 0 | 0.4 | 83.3 | 0 | 10.5 | 19.4 | negligible | present | जाना [2 in Bhojpuri / 1 elsewhere]; पानी [8 in Bhojpuri / 21 elsewhere] |
| 25 | 10. Person agreement | 11.2 | 1.3 | 6.2 | 51.4 | 0 | 8.6 | 9.6 | negligible | present | हो [10 in Bhojpuri / 37 elsewhere] |
| 26 | 20. Oblique pronouns | 8 | 0 | 0.3 | 51.7 | 0 | 6.8 | 12.6 | negligible | present | एकरा [3 in Bhojpuri / 1 elsewhere]; इसमें [4 in Bhojpuri / 22 elsewhere] |
| 27 | 4. Modal auxiliaries | 4 | 0 | 0 | 47.4 | 0 | 5.5 | 11.5 | negligible | absent | सकते [3 in Bhojpuri / 27 elsewhere] |
| 28 | 33. Temporal / directional adverbs | 5.6 | 0.8 | 10 | 24 | 0 | 5.2 | 14.4 | negligible | present | बाद [2 in Bhojpuri / 1 elsewhere]; अब [2 in Bhojpuri / 2 elsewhere]; अभी [2 in Bhojpuri / 4 elsewhere] |
| 29 | 21. Genitive / possessive pronouns | 4.8 | 0 | 0 | 25.4 | 0 | 3.5 | 9.8 | negligible | absent |  |
| 30 | 17. Resultative / completive auxiliaries | 1.6 | 6.7 | null | null | 0 | 2.7 | 5.5 | negligible | absent | गया [2 in Bhojpuri / 23 elsewhere] |
| 31 | 3. Existential/possessive constructions | 0 | 4.1 | null | null | 1.2 | 2.0 | 5.6 | negligible | absent |  |
| 32 | 9. Mood / imperative / subjunctive | 3.2 | 0 | 4.7 | null | 0 | 1.5 | 19.2 | negligible | present |  |
| 32 | 23. Reflexive / reciprocal pronouns | 3.2 | 0 | 4.7 | null | 0 | 1.5 | 13.3 | negligible | present | अपन [4 in Bhojpuri / 10 elsewhere] |
| 34 | 19. Basic pronouns | 3.2 | 0 | 0 | null | 0 | 0.7 | 10.8 | zero | absent | हम [4 in Bhojpuri / 24 elsewhere] |
| 35 | 26. Question / tag particles | 0.8 | 0 | null | null | null | 0.5 | 0.2 | zero | present |  |
| 36 | 22. Honorific pronouns | 1.6 | 0 | null | null | 0 | 0.4 | 1.5 | zero | absent |  |
| 37 | 25. Interrogatives | 0.8 | 0 | null | null | 0 | 0.2 | 6.0 | zero | absent |  |
| 38 | 6. Negative auxiliaries | 0 | null | null | null | 0 | 0.0 | 0.0 | zero | - |  |
| 38 | 13. Honorific verb agreement | 0 | null | null | null | 0 | 0.0 | 0.0 | zero | - |  |
| 38 | 40. Clitics / enclitics | 0 | 0 | null | null | null | 0.0 | 0.0 | zero | absent |  |

## Maithili (family: Bihari; n=125; full-model OvR AUC=0.648)
- materially useful (score>=40): **3**; weak-or-better (>=20): 10; effectively zero (<1): 7
- top 5: Comparative / degree markers (55.0); Numeral classifiers / count markers (46.3); Gender agreement (43.8); Interrogatives (29.2); Conjunctions (26.2)
- of the useful ones, absence-driven: Gender agreement
- zero: Honorific pronouns, Light / compound verb patterns, Definiteness / determiner markers, Negative auxiliaries, Honorific verb agreement, Question / tag particles, Clitics / enclitics
- exact vs family: Comparative / degree markers exact 55.0 / family 26.5; Numeral classifiers / count markers exact 46.3 / family 60.1; Gender agreement exact 43.8 / family 59.1; Interrogatives exact 29.2 / family 6.0; Conjunctions exact 26.2 / family 27.8

| rank | parameter | coverage% | distinct | precision | stability | ablation | exact | family | status | observed markers |
|--|--|--|--|--|--|--|--|--|--|--|
| 1 | 39. Comparative / degree markers | 43.2 | 33.2 | 6.5 | 100 | 67.6 | 55.0 | 26.5 | supporting | present | ढेर [4 in Maithili / 7 elsewhere]; बहुत [46 in Maithili / 194 elsewhere]; काफी [7 in Maithili / 33 elsewhere]; ज्यादा [2 in Maithili / 10 elsewhere] |
| 2 | 31. Numeral classifiers / count markers | 12.8 | 30 | 19 | 100 | 58.5 | 46.3 | 60.1 | supporting | present | तीनगो [2 in Maithili / 0 elsewhere]; एगो [14 in Maithili / 24 elsewhere] |
| 3 | 12. Gender agreement | 40 | 0 | 0 | 100 | 64.6 | 43.8 | 59.1 | supporting | absent | लगता [7 in Maithili / 6 elsewhere]; चला [2 in Maithili / 2 elsewhere]; लिखा [6 in Maithili / 11 elsewhere]; लगा [10 in Maithili / 24 elsewhere] |
| 4 | 25. Interrogatives | 6.4 | 23.4 | 29.3 | 100 | 19.2 | 29.2 | 6.0 | weak | present | कितना [4 in Maithili / 5 elsewhere]; क्या [2 in Maithili / 5 elsewhere] |
| 5 | 34. Conjunctions | 30.4 | 5.6 | 0 | 100 | 21.9 | 26.2 | 27.8 | weak | absent | या [3 in Maithili / 19 elsewhere]; और [31 in Maithili / 268 elsewhere]; आ [5 in Maithili / 48 elsewhere] |
| 6 | 1. Copulas | 82.4 | 0.3 | 0.8 | 93.6 | 11.8 | 24.3 | 20.1 | weak | present | हय [2 in Maithili / 0 elsewhere]; छै [8 in Maithili / 7 elsewhere]; छे [34 in Maithili / 41 elsewhere]; है [66 in Maithili / 426 elsewhere] |
| 7 | 14. Infinitives / non-finite forms | 17.6 | 21.4 | 10.6 | 100 | 4.8 | 22.4 | 19.4 | weak | present | देखने [16 in Maithili / 12 elsewhere]; खाने [2 in Maithili / 3 elsewhere]; पानी [2 in Maithili / 27 elsewhere] |
| 8 | 7. Tense morphology | 33.6 | 8 | 3.7 | 100 | 6.3 | 21.8 | 36.1 | weak | present | रहेंगे [2 in Maithili / 0 elsewhere]; बनल [3 in Maithili / 2 elsewhere]; चला [2 in Maithili / 2 elsewhere]; बैठल [2 in Maithili / 3 elsewhere] |
| 9 | 15. Participles / converbs | 26.4 | 12.8 | 5.5 | 100 | 5.8 | 21.6 | 7.6 | weak | present | हुआ [23 in Maithili / 67 elsewhere]; हुए [6 in Maithili / 57 elsewhere]; हुई [6 in Maithili / 66 elsewhere] |
| 10 | 29. Case / postposition system | 76 | 0 | 0.2 | 100 | 0 | 20.0 | 23.6 | weak | present | पे [18 in Maithili / 55 elsewhere]; साथ [2 in Maithili / 6 elsewhere]; कर [8 in Maithili / 28 elsewhere]; में [53 in Maithili / 200 elsewhere] |
| 11 | 28. Indefinite / quantifier paradigms | 36.8 | 1.8 | 2.6 | 100 | 0 | 18.2 | 16.7 | negligible | present | दोनों [3 in Maithili / 1 elsewhere]; कोनो [2 in Maithili / 1 elsewhere]; कम [2 in Maithili / 3 elsewhere]; सब [17 in Maithili / 30 elsewhere] |
| 12 | 32. Locative / deictic adverbs | 36.8 | 0 | 0 | 100 | 0 | 17.4 | 17.6 | negligible | absent | वहीं [2 in Maithili / 2 elsewhere]; पास [2 in Maithili / 8 elsewhere]; यहां [28 in Maithili / 129 elsewhere]; लगे [6 in Maithili / 35 elsewhere] |
| 13 | 9. Mood / imperative / subjunctive | 5.6 | 11.9 | 19 | 100 | 0.2 | 17.0 | 19.2 | negligible | present | देखिये [3 in Maithili / 2 elsewhere] |
| 14 | 2. Non-copular auxiliaries | 32.8 | 0 | 0.5 | 100 | 0 | 16.6 | 29.3 | negligible | present | रहल [3 in Maithili / 2 elsewhere]; लागल [4 in Maithili / 17 elsewhere]; रहा [21 in Maithili / 136 elsewhere]; रहे [14 in Maithili / 101 elsewhere] |
| 14 | 36. Discourse / emphatic / topic / focus particles | 38.4 | 0 | 1.1 | 87.9 | 0 | 16.6 | 17.4 | negligible | present | अरे [5 in Maithili / 6 elsewhere]; अच्छा [15 in Maithili / 40 elsewhere]; मतलब [2 in Maithili / 6 elsewhere]; ही [10 in Maithili / 49 elsewhere] |
| 16 | 8. Aspect morphology | 13.6 | 0 | 1.5 | 100 | 9 | 16.5 | 62.0 | negligible | present | लगते [2 in Maithili / 1 elsewhere]; मिलत [2 in Maithili / 1 elsewhere]; लगता [7 in Maithili / 6 elsewhere]; जाता [2 in Maithili / 5 elsewhere] |
| 16 | 27. Relative / correlative forms | 22.4 | 5.4 | 4.6 | 100 | 0 | 16.5 | 14.9 | negligible | present | जैसे [5 in Maithili / 10 elsewhere]; जे [4 in Maithili / 9 elsewhere]; जहां [4 in Maithili / 16 elsewhere]; जो [13 in Maithili / 74 elsewhere] |
| 16 | 37. Vocative / address particles | 6.4 | 14.5 | 0 | 43.8 | 18 | 16.5 | 16.4 | negligible | absent | भैया [2 in Maithili / 4 elsewhere]; ए [2 in Maithili / 13 elsewhere]; जी [4 in Maithili / 60 elsewhere] |
| 19 | 24. Demonstratives | 27.2 | 0 | 0 | 100 | 0 | 15.4 | 16.2 | negligible | present | वही [2 in Maithili / 1 elsewhere]; उस [2 in Maithili / 4 elsewhere]; ई [4 in Maithili / 11 elsewhere]; इ [4 in Maithili / 16 elsewhere] |
| 20 | 11. Number agreement | 25.6 | 0 | 0 | 100 | 0 | 15.1 | 15.2 | negligible | absent | रहेंगे [2 in Maithili / 0 elsewhere]; लगते [2 in Maithili / 1 elsewhere]; करते [2 in Maithili / 5 elsewhere]; देखे [2 in Maithili / 9 elsewhere] |
| 21 | 35. Subordinators / complementizers | 8.8 | 3.8 | 8.5 | 100 | 0 | 14.0 | 8.4 | negligible | present | कि [11 in Maithili / 35 elsewhere] |
| 22 | 21. Genitive / possessive pronouns | 8.8 | 1.3 | 7.4 | 100 | 0 | 13.2 | 9.8 | negligible | present | हमरा [2 in Maithili / 1 elsewhere]; हमारे [3 in Maithili / 2 elsewhere]; उसके [2 in Maithili / 8 elsewhere] |
| 23 | 16. Causative / passive morphology | 12.8 | 0 | 0 | 100 | 0 | 12.6 | 14.1 | negligible | absent | बनाया [5 in Maithili / 1 elsewhere]; दिखाई [8 in Maithili / 111 elsewhere] |
| 24 | 23. Reflexive / reciprocal pronouns | 4 | 0 | 9.5 | 100 | 0 | 12.2 | 13.3 | negligible | present | अपन [4 in Maithili / 10 elsewhere] |
| 25 | 10. Person agreement | 6.4 | 0 | 0 | 100 | 0.8 | 11.6 | 9.6 | negligible | absent | हो [4 in Maithili / 43 elsewhere] |
| 26 | 19. Basic pronouns | 4.8 | 0 | 2.8 | 100 | 0.4 | 11.5 | 10.8 | negligible | present | हम [6 in Maithili / 22 elsewhere] |
| 27 | 17. Resultative / completive auxiliaries | 4.8 | 0 | 2.8 | 100 | 0 | 11.4 | 5.5 | negligible | present | गया [4 in Maithili / 21 elsewhere] |
| 28 | 4. Modal auxiliaries | 4.8 | 0 | 2 | 100 | 0 | 11.3 | 11.5 | negligible | present | सकते [6 in Maithili / 24 elsewhere] |
| 29 | 30. Plural markers | 13.6 | 8.1 | 0 | 56.3 | 0 | 10.4 | 13.5 | negligible | absent | लोग [9 in Maithili / 65 elsewhere] |
| 30 | 20. Oblique pronouns | 8.8 | 0 | 1.8 | 78.6 | 0 | 9.9 | 12.6 | negligible | present | उसमें [2 in Maithili / 6 elsewhere]; हमें [5 in Maithili / 23 elsewhere] |
| 31 | 5. Negation particles | 4.8 | 0 | 7.8 | 76.6 | 0 | 9.8 | 17.0 | negligible | present | न [2 in Maithili / 3 elsewhere]; नहीं [4 in Maithili / 13 elsewhere] |
| 32 | 3. Existential/possessive constructions | 0 | 4.1 | null | null | 1 | 1.9 | 5.6 | negligible | absent |  |
| 32 | 33. Temporal / directional adverbs | 4.8 | 0 | 6.5 | 0 | 0 | 1.9 | 14.4 | negligible | present | तब [2 in Maithili / 2 elsewhere] |
| 34 | 22. Honorific pronouns | 1.6 | 0 | null | null | 0 | 0.4 | 1.5 | zero | absent |  |
| 35 | 18. Light / compound verb patterns | 0.8 | 0 | null | null | 0 | 0.2 | 8.4 | zero | absent |  |
| 35 | 38. Definiteness / determiner markers | 0.8 | 0 | null | null | 0 | 0.2 | 7.9 | zero | absent |  |
| 37 | 6. Negative auxiliaries | 0 | null | null | null | 0 | 0.0 | 0.0 | zero | - |  |
| 37 | 13. Honorific verb agreement | 0 | null | null | null | 0 | 0.0 | 0.0 | zero | - |  |
| 37 | 26. Question / tag particles | 0 | 0 | null | null | null | 0.0 | 0.2 | zero | absent |  |
| 37 | 40. Clitics / enclitics | 0 | 0 | null | null | null | 0.0 | 0.0 | zero | absent |  |

## Chhattisgarhi (family: Eastern-Hindi; n=125; full-model OvR AUC=0.677)
- materially useful (score>=40): **1**; weak-or-better (>=20): 5; effectively zero (<1): 8
- top 5: Vocative / address particles (42.9); Non-copular auxiliaries (31.5); Locative / deictic adverbs (27.7); Indefinite / quantifier paradigms (25.6); Case / postposition system (20.0)
- of the useful ones, absence-driven: none
- zero: Negation particles, Reflexive / reciprocal pronouns, Light / compound verb patterns, Definiteness / determiner markers, Negative auxiliaries, Honorific verb agreement, Question / tag particles, Clitics / enclitics
- exact vs family: Vocative / address particles exact 42.9 / family 42.1; Non-copular auxiliaries exact 31.5 / family 31.6; Locative / deictic adverbs exact 27.7 / family 26.7; Indefinite / quantifier paradigms exact 25.6 / family 25.4; Case / postposition system exact 20.0 / family 19.8

| rank | parameter | coverage% | distinct | precision | stability | ablation | exact | family | status | observed markers |
|--|--|--|--|--|--|--|--|--|--|--|
| 1 | 37. Vocative / address particles | 27.2 | 56.8 | 18.6 | 43.3 | 40.3 | 42.9 | 42.1 | supporting | present | हे [24 in Chhattisgarhi / 7 elsewhere]; ए [3 in Chhattisgarhi / 12 elsewhere]; जी [6 in Chhattisgarhi / 58 elsewhere] |
| 2 | 2. Non-copular auxiliaries | 16 | 49.3 | 0 | 19.4 | 35.2 | 31.5 | 31.6 | weak | absent | रहे [12 in Chhattisgarhi / 103 elsewhere]; रहा [16 in Chhattisgarhi / 141 elsewhere]; रही [3 in Chhattisgarhi / 113 elsewhere] |
| 3 | 32. Locative / deictic adverbs | 24.8 | 30.1 | 0 | 100 | 13 | 27.7 | 26.7 | weak | absent | अंदर [5 in Chhattisgarhi / 17 elsewhere]; पास [2 in Chhattisgarhi / 8 elsewhere]; लगे [6 in Chhattisgarhi / 35 elsewhere]; पीछे [4 in Chhattisgarhi / 28 elsewhere] |
| 4 | 28. Indefinite / quantifier paradigms | 18.4 | 35 | 0 | 45.9 | 21.5 | 25.6 | 25.4 | weak | absent | हर [5 in Chhattisgarhi / 7 elsewhere]; सब [8 in Chhattisgarhi / 39 elsewhere]; सारे [5 in Chhattisgarhi / 48 elsewhere]; कोई [2 in Chhattisgarhi / 27 elsewhere] |
| 5 | 29. Case / postposition system | 68.8 | 4.4 | 0 | 89 | 0 | 20.0 | 19.8 | negligible | absent | ला [3 in Chhattisgarhi / 1 elsewhere]; ले [5 in Chhattisgarhi / 12 elsewhere]; कर [10 in Chhattisgarhi / 26 elsewhere]; ने [2 in Chhattisgarhi / 10 elsewhere] |
| 6 | 8. Aspect morphology | 21.6 | 27.5 | 10.8 | 71.2 | 0 | 19.9 | 22.9 | negligible | present | जाते [4 in Chhattisgarhi / 0 elsewhere]; देखत [2 in Chhattisgarhi / 0 elsewhere]; करेला [2 in Chhattisgarhi / 1 elsewhere]; करत [2 in Chhattisgarhi / 1 elsewhere] |
| 7 | 1. Copulas | 72.8 | 1.6 | 0 | 89.7 | 0 | 19.4 | 19.9 | negligible | absent | हवे [17 in Chhattisgarhi / 2 elsewhere]; थे [4 in Chhattisgarhi / 1 elsewhere]; था [3 in Chhattisgarhi / 4 elsewhere]; ह [3 in Chhattisgarhi / 10 elsewhere] |
| 8 | 9. Mood / imperative / subjunctive | 0 | 34.4 | null | null | 11.8 | 17.8 | 21.6 | negligible | absent |  |
| 9 | 14. Infinitives / non-finite forms | 4.8 | 17.3 | 0 | 100 | 3.7 | 16.8 | 15.9 | negligible | absent | पानी [3 in Chhattisgarhi / 26 elsewhere] |
| 9 | 24. Demonstratives | 32 | 0 | 2.6 | 100 | 0 | 16.8 | 19.6 | negligible | present | ओ [6 in Chhattisgarhi / 2 elsewhere]; उ [2 in Chhattisgarhi / 4 elsewhere]; इ [4 in Chhattisgarhi / 16 elsewhere]; यह [9 in Chhattisgarhi / 45 elsewhere] |
| 11 | 15. Participles / converbs | 7.2 | 45.9 | 0 | 3 | 8.1 | 16.5 | 12.4 | negligible | absent | लेके [2 in Chhattisgarhi / 2 elsewhere]; हुए [4 in Chhattisgarhi / 59 elsewhere]; हुआ [4 in Chhattisgarhi / 86 elsewhere] |
| 12 | 17. Resultative / completive auxiliaries | 5.6 | 0 | 5.7 | 100 | 11.1 | 16.4 | 20.4 | negligible | present | गए [2 in Chhattisgarhi / 4 elsewhere]; गई [2 in Chhattisgarhi / 8 elsewhere]; गया [3 in Chhattisgarhi / 22 elsewhere] |
| 13 | 22. Honorific pronouns | 0 | 36.7 | null | null | 7.7 | 16.3 | 16.5 | negligible | absent |  |
| 14 | 25. Interrogatives | 4.8 | 8.8 | 18.4 | 100 | 0 | 15.9 | 21.3 | negligible | present | कितने [2 in Chhattisgarhi / 0 elsewhere]; कहां [2 in Chhattisgarhi / 1 elsewhere]; क्या [3 in Chhattisgarhi / 4 elsewhere] |
| 15 | 12. Gender agreement | 33.6 | 19 | 0 | 39 | 0 | 15.4 | 15.5 | negligible | absent | देखा [3 in Chhattisgarhi / 1 elsewhere]; कहीं [3 in Chhattisgarhi / 2 elsewhere]; बैठा [3 in Chhattisgarhi / 4 elsewhere]; पीला [4 in Chhattisgarhi / 7 elsewhere] |
| 15 | 36. Discourse / emphatic / topic / focus particles | 32.8 | 0 | 0 | 88.1 | 0 | 15.4 | 15.4 | negligible | absent | हां [5 in Chhattisgarhi / 1 elsewhere]; बस [2 in Chhattisgarhi / 5 elsewhere]; अच्छा [11 in Chhattisgarhi / 44 elsewhere]; तो [4 in Chhattisgarhi / 23 elsewhere] |
| 17 | 34. Conjunctions | 31.2 | 2.4 | 0 | 84.3 | 0 | 15.3 | 16.5 | negligible | absent | अऊ [5 in Chhattisgarhi / 0 elsewhere]; अउ [2 in Chhattisgarhi / 0 elsewhere]; बाकी [2 in Chhattisgarhi / 1 elsewhere]; और [25 in Chhattisgarhi / 274 elsewhere] |
| 18 | 7. Tense morphology | 18.4 | 16.3 | 0 | 74.2 | 0 | 15.2 | 13.9 | negligible | absent | देखा [3 in Chhattisgarhi / 1 elsewhere]; कहीं [3 in Chhattisgarhi / 2 elsewhere]; बैठा [3 in Chhattisgarhi / 4 elsewhere]; बना [5 in Chhattisgarhi / 12 elsewhere] |
| 19 | 11. Number agreement | 28 | 0 | 1.1 | 85.7 | 1.8 | 15.0 | 15.4 | negligible | present | जाते [4 in Chhattisgarhi / 0 elsewhere]; कहीं [3 in Chhattisgarhi / 2 elsewhere]; होते [3 in Chhattisgarhi / 2 elsewhere]; करे [2 in Chhattisgarhi / 2 elsewhere] |
| 20 | 4. Modal auxiliaries | 0.8 | 21.9 | null | null | 12.9 | 14.4 | 13.3 | negligible | absent |  |
| 21 | 3. Existential/possessive constructions | 2.4 | 14.8 | 54.3 | null | 0 | 13.7 | 17.1 | negligible | present | आहे [2 in Chhattisgarhi / 0 elsewhere] |
| 22 | 27. Relative / correlative forms | 15.2 | 0 | 0 | 100 | 0 | 13.0 | 13.0 | negligible | absent | जेकर [3 in Chhattisgarhi / 1 elsewhere]; जैसे [5 in Chhattisgarhi / 10 elsewhere]; जे [2 in Chhattisgarhi / 11 elsewhere]; जो [10 in Chhattisgarhi / 77 elsewhere] |
| 23 | 31. Numeral classifiers / count markers | 6.4 | 0 | 2.3 | 100 | 1.1 | 12.1 | 13.4 | negligible | present | ठो [4 in Chhattisgarhi / 6 elsewhere]; एगो [2 in Chhattisgarhi / 36 elsewhere] |
| 24 | 21. Genitive / possessive pronouns | 7.2 | 0 | 3.4 | 100 | 0 | 12.0 | 12.6 | negligible | present | एकर [2 in Chhattisgarhi / 2 elsewhere]; हमारे [2 in Chhattisgarhi / 3 elsewhere]; इसके [2 in Chhattisgarhi / 8 elsewhere] |
| 24 | 39. Comparative / degree markers | 25.6 | 0 | 0 | 68.3 | 0 | 12.0 | 12.0 | negligible | absent | एकदम [3 in Chhattisgarhi / 3 elsewhere]; बहुत [28 in Chhattisgarhi / 212 elsewhere] |
| 26 | 33. Temporal / directional adverbs | 4.8 | 0 | 6.5 | 100 | 0 | 11.9 | 12.7 | negligible | present | अब [2 in Chhattisgarhi / 2 elsewhere] |
| 27 | 30. Plural markers | 22.4 | 0 | 2.3 | 68.6 | 0 | 11.7 | 11.9 | negligible | present | मन [20 in Chhattisgarhi / 8 elsewhere]; लोग [5 in Chhattisgarhi / 69 elsewhere] |
| 28 | 10. Person agreement | 7.2 | 0 | 0 | 100 | 0 | 11.4 | 11.4 | negligible | absent | हो [7 in Chhattisgarhi / 40 elsewhere] |
| 28 | 19. Basic pronouns | 4.8 | 0 | 2.8 | 100 | 0 | 11.4 | 11.7 | negligible | present | हमन [3 in Chhattisgarhi / 0 elsewhere]; हम [3 in Chhattisgarhi / 25 elsewhere] |
| 30 | 35. Subordinators / complementizers | 4.8 | 0 | 0 | 100 | 0 | 11.0 | 11.0 | negligible | absent | कि [4 in Chhattisgarhi / 42 elsewhere] |
| 31 | 20. Oblique pronouns | 3.2 | 17.4 | 0 | null | 9 | 9.6 | 8.9 | negligible | absent |  |
| 32 | 16. Causative / passive morphology | 13.6 | 0 | 0 | 59.4 | 0 | 8.7 | 8.7 | negligible | absent | बनाए [2 in Chhattisgarhi / 2 elsewhere]; दिखाई [9 in Chhattisgarhi / 110 elsewhere] |
| 33 | 5. Negation particles | 3.2 | 0 | 0.5 | null | 0 | 0.8 | 1.3 | zero | present | नहीं [2 in Chhattisgarhi / 15 elsewhere] |
| 34 | 23. Reflexive / reciprocal pronouns | 2.4 | 0 | 0 | null | 0 | 0.5 | 0.8 | zero | absent | अपन [3 in Chhattisgarhi / 11 elsewhere] |
| 35 | 18. Light / compound verb patterns | 1.6 | 0 | null | null | 0 | 0.4 | 0.4 | zero | present |  |
| 36 | 38. Definiteness / determiner markers | 0.8 | 0 | null | null | 0 | 0.2 | 0.2 | zero | absent |  |
| 37 | 6. Negative auxiliaries | 0 | null | null | null | 0 | 0.0 | 0.0 | zero | - |  |
| 37 | 13. Honorific verb agreement | 0 | null | null | null | 0 | 0.0 | 0.0 | zero | - |  |
| 37 | 26. Question / tag particles | 0 | 0 | null | null | null | 0.0 | 0.0 | zero | absent |  |
| 37 | 40. Clitics / enclitics | 0 | 0 | null | null | null | 0.0 | 0.0 | zero | absent |  |

## Rajasthani (family: Rajasthani; n=125; full-model OvR AUC=0.777)
- materially useful (score>=40): **1**; weak-or-better (>=20): 14; effectively zero (<1): 8
- top 5: Comparative / degree markers (64.1); Demonstratives (37.7); Participles / converbs (36.6); Tense morphology (28.2); Non-copular auxiliaries (26.5)
- of the useful ones, absence-driven: Comparative / degree markers
- zero: Modal auxiliaries, Basic pronouns, Temporal / directional adverbs, Light / compound verb patterns, Definiteness / determiner markers, Negative auxiliaries, Honorific verb agreement, Question / tag particles
- exact vs family: Comparative / degree markers exact 64.1 / family 68.3; Demonstratives exact 37.7 / family 38.8; Participles / converbs exact 36.6 / family 41.3; Tense morphology exact 28.2 / family 25.4; Non-copular auxiliaries exact 26.5 / family 32.5

| rank | parameter | coverage% | distinct | precision | stability | ablation | exact | family | status | observed markers |
|--|--|--|--|--|--|--|--|--|--|--|
| 1 | 39. Comparative / degree markers | 9.6 | 76.1 | 0 | 100 | 82.8 | 64.1 | 68.3 | strong | absent | काफी [3 in Rajasthani / 37 elsewhere]; बहुत [8 in Rajasthani / 232 elsewhere] |
| 2 | 24. Demonstratives | 10.4 | 60.9 | 0 | 100 | 26 | 37.7 | 38.8 | weak | absent | यो [2 in Rajasthani / 3 elsewhere]; ओ [2 in Rajasthani / 6 elsewhere]; वो [3 in Rajasthani / 22 elsewhere]; यह [3 in Rajasthani / 51 elsewhere] |
| 3 | 15. Participles / converbs | 4.8 | 64.3 | 0 | 100 | 23.9 | 36.6 | 41.3 | weak | absent | हुए [2 in Rajasthani / 61 elsewhere]; हुई [2 in Rajasthani / 70 elsewhere]; हुआ [2 in Rajasthani / 88 elsewhere] |
| 4 | 7. Tense morphology | 12 | 49.5 | 0 | 100 | 8.5 | 28.2 | 25.4 | weak | absent | जाली [2 in Rajasthani / 2 elsewhere]; रखी [7 in Rajasthani / 30 elsewhere]; बनी [2 in Rajasthani / 11 elsewhere] |
| 5 | 2. Non-copular auxiliaries | 42.4 | 21.2 | 4.8 | 100 | 5.1 | 26.5 | 32.5 | weak | present | रही [32 in Rajasthani / 84 elsewhere]; रहे [20 in Rajasthani / 95 elsewhere]; रहा [11 in Rajasthani / 146 elsewhere] |
| 6 | 35. Subordinators / complementizers | 0 | 63.4 | null | null | 9.2 | 26.1 | 26.5 | weak | absent |  |
| 7 | 17. Resultative / completive auxiliaries | 0 | 50.8 | null | null | 16 | 25.5 | 28.4 | weak | absent |  |
| 8 | 34. Conjunctions | 44 | 6 | 2.7 | 100 | 5.8 | 23.0 | 24.8 | weak | present | आ [18 in Rajasthani / 35 elsewhere]; और [39 in Rajasthani / 260 elsewhere]; या [2 in Rajasthani / 20 elsewhere] |
| 9 | 1. Copulas | 78.4 | 0 | 0.1 | 100 | 5.7 | 22.3 | 20.0 | weak | present | छै [5 in Rajasthani / 10 elsewhere]; छे [20 in Rajasthani / 55 elsewhere]; छ [5 in Rajasthani / 25 elsewhere]; है [69 in Rajasthani / 423 elsewhere] |
| 9 | 8. Aspect morphology | 4 | 37.2 | 0 | 40.5 | 20.5 | 22.3 | 23.2 | weak | absent | पीला [2 in Rajasthani / 9 elsewhere] |
| 11 | 36. Discourse / emphatic / topic / focus particles | 25.6 | 20.3 | 0 | 100 | 4 | 21.8 | 20.3 | weak | absent | तो [7 in Rajasthani / 20 elsewhere]; भी [22 in Rajasthani / 221 elsewhere]; ही [2 in Rajasthani / 57 elsewhere] |
| 12 | 5. Negation particles | 0 | 42 | null | null | 14.5 | 21.7 | 22.8 | weak | absent |  |
| 12 | 20. Oblique pronouns | 1.6 | 36.5 | null | null | 17.1 | 21.7 | 22.8 | weak | absent |  |
| 14 | 29. Case / postposition system | 68.8 | 4.4 | 0 | 100 | 0 | 21.1 | 20.9 | weak | absent | बटिन [2 in Rajasthani / 0 elsewhere]; री [3 in Rajasthani / 1 elsewhere]; को [20 in Rajasthani / 25 elsewhere]; ऊपर [16 in Rajasthani / 54 elsewhere] |
| 15 | 32. Locative / deictic adverbs | 34.4 | 0 | 0 | 100 | 6.8 | 19.6 | 16.9 | negligible | absent | अठे [3 in Rajasthani / 0 elsewhere]; पास [4 in Rajasthani / 6 elsewhere]; बीच [5 in Rajasthani / 11 elsewhere]; आगे [4 in Rajasthani / 10 elsewhere] |
| 16 | 12. Gender agreement | 40.8 | 0 | 0 | 100 | 0 | 18.2 | 18.2 | negligible | absent | जाली [2 in Rajasthani / 2 elsewhere]; आई [2 in Rajasthani / 4 elsewhere]; रही [32 in Rajasthani / 84 elsewhere]; रखी [7 in Rajasthani / 30 elsewhere] |
| 17 | 27. Relative / correlative forms | 8.8 | 24.9 | 0 | 100 | 0 | 18.0 | 18.2 | negligible | absent | जैसा [2 in Rajasthani / 16 elsewhere]; जो [8 in Rajasthani / 79 elsewhere] |
| 18 | 31. Numeral classifiers / count markers | 1.6 | 19.5 | null | null | 19.4 | 17.3 | 18.2 | negligible | absent |  |
| 19 | 28. Indefinite / quantifier paradigms | 24.8 | 5.7 | 0 | 100 | 0 | 16.4 | 15.5 | negligible | absent | थोडा [3 in Rajasthani / 2 elsewhere]; कोई [9 in Rajasthani / 20 elsewhere]; सारा [7 in Rajasthani / 43 elsewhere]; सारी [3 in Rajasthani / 43 elsewhere] |
| 20 | 22. Honorific pronouns | 0 | 36.7 | null | null | 6.6 | 15.8 | 15.4 | negligible | absent |  |
| 21 | 21. Genitive / possessive pronouns | 0.8 | 35.1 | null | null | 7.1 | 15.7 | 15.8 | negligible | absent |  |
| 22 | 11. Number agreement | 23.2 | 0 | 0 | 100 | 0 | 14.6 | 14.6 | negligible | absent | रखे [4 in Rajasthani / 12 elsewhere]; रहे [20 in Rajasthani / 95 elsewhere]; बैठे [4 in Rajasthani / 22 elsewhere] |
| 23 | 25. Interrogatives | 0 | 30.8 | null | null | 7.6 | 14.3 | 16.1 | negligible | absent |  |
| 24 | 9. Mood / imperative / subjunctive | 4.8 | 4.5 | 14.3 | 100 | 0 | 14.2 | 17.2 | negligible | present | बैठो [2 in Rajasthani / 1 elsewhere]; देखो [4 in Rajasthani / 4 elsewhere] |
| 25 | 30. Plural markers | 17.6 | 0 | 0 | 100 | 0 | 13.5 | 13.5 | negligible | absent | कुर्सियां [4 in Rajasthani / 4 elsewhere]; खिडकियां [4 in Rajasthani / 5 elsewhere]; मन [2 in Rajasthani / 26 elsewhere]; लोग [5 in Rajasthani / 69 elsewhere] |
| 26 | 10. Person agreement | 10.4 | 0 | 4.7 | 100 | 0 | 12.8 | 13.2 | negligible | present | बैठो [2 in Rajasthani / 1 elsewhere]; देखो [4 in Rajasthani / 4 elsewhere]; हो [6 in Rajasthani / 41 elsewhere] |
| 27 | 14. Infinitives / non-finite forms | 6.4 | 4.4 | 0 | 100 | 0 | 12.4 | 12.0 | negligible | absent | करने [2 in Rajasthani / 1 elsewhere]; पानी [6 in Rajasthani / 23 elsewhere] |
| 28 | 16. Causative / passive morphology | 20.8 | 2 | 4.1 | 50.2 | 0 | 10.3 | 11.6 | negligible | present | कराया [2 in Rajasthani / 0 elsewhere]; लगाई [2 in Rajasthani / 4 elsewhere]; दिखाई [20 in Rajasthani / 99 elsewhere] |
| 29 | 37. Vocative / address particles | 11.2 | 0 | 0 | 78.5 | 0 | 10.1 | 10.1 | negligible | absent | रे [2 in Rajasthani / 0 elsewhere]; जी [10 in Rajasthani / 54 elsewhere] |
| 30 | 40. Clitics / enclitics | 0.8 | 8.8 | null | null | null | 6.7 | 8.4 | negligible | present |  |
| 31 | 3. Existential/possessive constructions | 0 | 4.1 | null | null | 0 | 1.4 | 4.0 | negligible | absent |  |
| 32 | 23. Reflexive / reciprocal pronouns | 0.8 | 3.4 | null | null | 0 | 1.3 | 2.0 | negligible | absent |  |
| 33 | 4. Modal auxiliaries | 3.2 | 0 | 0 | null | 0 | 0.7 | 0.7 | zero | absent | पडी [4 in Rajasthani / 3 elsewhere] |
| 33 | 19. Basic pronouns | 3.2 | 0 | 0 | null | 0 | 0.7 | 0.7 | zero | absent | हम [2 in Rajasthani / 26 elsewhere] |
| 35 | 33. Temporal / directional adverbs | 1.6 | 0 | null | null | 0 | 0.4 | 1.6 | zero | absent |  |
| 36 | 18. Light / compound verb patterns | 0.8 | 0 | null | null | 0 | 0.2 | 0.2 | zero | absent |  |
| 36 | 38. Definiteness / determiner markers | 0.8 | 0 | null | null | 0 | 0.2 | 0.2 | zero | absent |  |
| 38 | 6. Negative auxiliaries | 0 | null | null | null | 0 | 0.0 | 0.0 | zero | - |  |
| 38 | 13. Honorific verb agreement | 0 | null | null | null | 0 | 0.0 | 0.0 | zero | - |  |
| 38 | 26. Question / tag particles | 0 | 0 | null | null | null | 0.0 | 0.0 | zero | absent |  |

## Garhwali (family: Pahari; n=125; full-model OvR AUC=0.810)
- materially useful (score>=40): **2**; weak-or-better (>=20): 9; effectively zero (<1): 8
- top 5: Copulas (81.9); Non-copular auxiliaries (56.7); Participles / converbs (35.4); Aspect morphology (32.2); Gender agreement (27.5)
- of the useful ones, absence-driven: Copulas, Non-copular auxiliaries
- zero: Temporal / directional adverbs, Mood / imperative / subjunctive, Interrogatives, Light / compound verb patterns, Negative auxiliaries, Honorific verb agreement, Question / tag particles, Clitics / enclitics
- exact vs family: Copulas exact 81.9 / family 71.9; Non-copular auxiliaries exact 56.7 / family 32.3; Participles / converbs exact 35.4 / family 6.0; Aspect morphology exact 32.2 / family 47.3; Gender agreement exact 27.5 / family 18.2

| rank | parameter | coverage% | distinct | precision | stability | ablation | exact | family | status | observed markers |
|--|--|--|--|--|--|--|--|--|--|--|
| 1 | 1. Copulas | 45.6 | 100 | 0 | 77.6 | 100 | 81.9 | 71.9 | core | absent | छी [5 in Garhwali / 2 elsewhere]; छ [18 in Garhwali / 12 elsewhere]; छो [2 in Garhwali / 2 elsewhere]; छन [15 in Garhwali / 23 elsewhere] |
| 2 | 2. Non-copular auxiliaries | 3.2 | 100 | 0 | null | 63.4 | 56.7 | 32.3 | supporting | absent |  |
| 3 | 15. Participles / converbs | 4 | 71.2 | 0 | 42.6 | 31.4 | 35.4 | 6.0 | weak | absent | हुई [4 in Garhwali / 68 elsewhere] |
| 4 | 8. Aspect morphology | 4.8 | 30.1 | 0 | 100 | 34.3 | 32.2 | 47.3 | weak | absent |  |
| 5 | 12. Gender agreement | 27.2 | 45.3 | 0 | 100 | 1.9 | 27.5 | 18.2 | weak | absent | होया [3 in Garhwali / 1 elsewhere]; लगीं [10 in Garhwali / 6 elsewhere]; लगी [8 in Garhwali / 30 elsewhere]; रखी [3 in Garhwali / 34 elsewhere] |
| 6 | 32. Locative / deictic adverbs | 22.4 | 40.7 | 0 | 100 | 0 | 24.7 | 12.0 | weak | absent | भीतर [4 in Garhwali / 2 elsewhere]; दूर [3 in Garhwali / 4 elsewhere]; यख [8 in Garhwali / 12 elsewhere]; किनारे [2 in Garhwali / 3 elsewhere] |
| 7 | 16. Causative / passive morphology | 2.4 | 73.5 | 0 | null | 7.2 | 24.2 | 16.6 | weak | absent |  |
| 8 | 29. Case / postposition system | 65.6 | 17.5 | 0 | 93 | 0 | 23.7 | 18.6 | weak | absent | कु [14 in Garhwali / 12 elsewhere]; मा [19 in Garhwali / 20 elsewhere]; तक [3 in Garhwali / 4 elsewhere]; खातिर [2 in Garhwali / 3 elsewhere] |
| 9 | 11. Number agreement | 14.4 | 33.4 | 0 | 100 | 0 | 21.2 | 9.7 | weak | absent | लगीं [10 in Garhwali / 6 elsewhere] |
| 10 | 21. Genitive / possessive pronouns | 0.8 | 35.1 | null | null | 9.1 | 16.8 | 1.2 | negligible | absent |  |
| 11 | 28. Indefinite / quantifier paradigms | 35.2 | 0 | 1.9 | 88.8 | 0.7 | 16.5 | 22.9 | negligible | present | कुछ [22 in Garhwali / 66 elsewhere]; हर [3 in Garhwali / 9 elsewhere]; सारा [7 in Garhwali / 43 elsewhere]; कई [4 in Garhwali / 27 elsewhere] |
| 12 | 22. Honorific pronouns | 6.4 | 16.1 | 20.8 | 46.9 | 8.2 | 16.4 | 18.4 | negligible | present | आप [8 in Garhwali / 14 elsewhere] |
| 13 | 34. Conjunctions | 40 | 0 | 1.1 | 77.5 | 0 | 15.9 | 18.3 | negligible | present | या [6 in Garhwali / 16 elsewhere]; और [45 in Garhwali / 254 elsewhere] |
| 14 | 27. Relative / correlative forms | 10.4 | 14.9 | 0 | 100 | 0 | 15.8 | 8.7 | negligible | absent | जैकु [2 in Garhwali / 0 elsewhere]; जु [2 in Garhwali / 1 elsewhere]; जो [5 in Garhwali / 82 elsewhere] |
| 15 | 7. Tense morphology | 22.4 | 0 | 0 | 100 | 1.7 | 15.1 | 15.4 | negligible | absent | होया [3 in Garhwali / 1 elsewhere]; लगीं [10 in Garhwali / 6 elsewhere]; लगी [8 in Garhwali / 30 elsewhere]; रखी [3 in Garhwali / 34 elsewhere] |
| 15 | 24. Demonstratives | 25.6 | 0 | 0 | 100 | 0 | 15.1 | 15.1 | negligible | absent | यो [3 in Garhwali / 2 elsewhere]; ये [20 in Garhwali / 102 elsewhere]; यह [8 in Garhwali / 46 elsewhere]; ई [2 in Garhwali / 13 elsewhere] |
| 17 | 30. Plural markers | 22.4 | 0 | 2.3 | 100 | 0 | 14.8 | 17.5 | negligible | present | लोग [19 in Garhwali / 55 elsewhere]; लोगों [2 in Garhwali / 6 elsewhere]; मन [5 in Garhwali / 23 elsewhere] |
| 18 | 20. Oblique pronouns | 1.6 | 36.5 | null | null | 2.9 | 14.1 | 1.7 | negligible | absent |  |
| 19 | 36. Discourse / emphatic / topic / focus particles | 38.4 | 0 | 1.1 | 50.3 | 0 | 12.9 | 24.0 | negligible | present | मतलब [3 in Garhwali / 5 elsewhere]; बस [2 in Garhwali / 5 elsewhere]; भी [37 in Garhwali / 206 elsewhere]; तो [4 in Garhwali / 23 elsewhere] |
| 20 | 37. Vocative / address particles | 11.2 | 0 | 0 | 100 | 0 | 12.2 | 11.4 | negligible | absent | जी [13 in Garhwali / 51 elsewhere] |
| 21 | 5. Negation particles | 6.4 | 9.9 | 15.2 | 49.2 | 0 | 11.0 | 9.2 | negligible | present | नी [2 in Garhwali / 1 elsewhere]; न [2 in Garhwali / 3 elsewhere]; नहीं [3 in Garhwali / 14 elsewhere] |
| 22 | 39. Comparative / degree markers | 24 | 3.1 | 0 | 38.6 | 0 | 9.4 | 15.0 | negligible | absent | ज्यादा [5 in Garhwali / 7 elsewhere]; खूब [2 in Garhwali / 9 elsewhere]; बहुत [24 in Garhwali / 216 elsewhere]; काफी [4 in Garhwali / 36 elsewhere] |
| 23 | 4. Modal auxiliaries | 8 | 10.3 | 12.9 | 25.5 | 0.6 | 8.9 | 8.8 | negligible | present | सकते [6 in Garhwali / 24 elsewhere] |
| 24 | 10. Person agreement | 10.4 | 0 | 4.7 | 0 | 14.9 | 8.7 | 13.5 | negligible | present | छी [5 in Garhwali / 2 elsewhere]; हो [7 in Garhwali / 40 elsewhere] |
| 25 | 14. Infinitives / non-finite forms | 13.6 | 0 | 4.9 | 49.9 | 0 | 8.4 | 13.4 | negligible | present | जाणा [2 in Garhwali / 0 elsewhere]; लगण [4 in Garhwali / 1 elsewhere]; करना [2 in Garhwali / 2 elsewhere]; पानी [2 in Garhwali / 27 elsewhere] |
| 25 | 19. Basic pronouns | 7.2 | 6.3 | 11.4 | 36.5 | 0 | 8.4 | 8.3 | negligible | present | तुम [2 in Garhwali / 0 elsewhere]; हम [6 in Garhwali / 22 elsewhere] |
| 27 | 17. Resultative / completive auxiliaries | 0.8 | 20.1 | null | null | 0 | 6.9 | 1.2 | negligible | absent |  |
| 28 | 23. Reflexive / reciprocal pronouns | 4 | 0 | 9.5 | 42.6 | 0 | 6.5 | 0.4 | negligible | present | अपना [2 in Garhwali / 0 elsewhere]; अपनी [2 in Garhwali / 3 elsewhere]; अपन [2 in Garhwali / 12 elsewhere] |
| 29 | 35. Subordinators / complementizers | 4 | 0 | 0 | 40.5 | 0 | 4.8 | 11.3 | negligible | absent | कि [3 in Garhwali / 43 elsewhere] |
| 30 | 31. Numeral classifiers / count markers | 2.4 | 9.2 | 0 | null | 0 | 3.1 | 25.3 | negligible | absent | ठो [3 in Garhwali / 7 elsewhere] |
| 31 | 38. Definiteness / determiner markers | 0.8 | 0 | null | null | 2 | 1.3 | 1.7 | negligible | absent |  |
| 32 | 3. Existential/possessive constructions | 1.6 | 1.7 | null | null | 0 | 1.0 | 0.2 | zero | present | आछे [2 in Garhwali / 0 elsewhere] |
| 33 | 33. Temporal / directional adverbs | 3.2 | 0 | 0 | null | 0 | 0.7 | 10.6 | zero | absent | अभी [2 in Garhwali / 4 elsewhere] |
| 34 | 9. Mood / imperative / subjunctive | 1.6 | 0 | null | null | 0 | 0.4 | 0.4 | zero | absent |  |
| 34 | 25. Interrogatives | 1.6 | 0 | null | null | 0 | 0.4 | 0.3 | zero | absent |  |
| 36 | 18. Light / compound verb patterns | 0.8 | 0 | null | null | 0 | 0.2 | 0.3 | zero | absent |  |
| 37 | 6. Negative auxiliaries | 0 | null | null | null | 0 | 0.0 | 0.0 | zero | - |  |
| 37 | 13. Honorific verb agreement | 0 | null | null | null | 0 | 0.0 | 0.0 | zero | - |  |
| 37 | 26. Question / tag particles | 0 | 0 | null | null | null | 0.0 | 0.2 | zero | absent |  |
| 37 | 40. Clitics / enclitics | 0 | 0 | null | null | null | 0.0 | 0.0 | zero | absent |  |

## Khariboli (family: Western-Hindi; n=125; full-model OvR AUC=0.657)
- materially useful (score>=40): **2**; weak-or-better (>=20): 10; effectively zero (<1): 10
- top 5: Copulas (76.4); Vocative / address particles (68.2); Locative / deictic adverbs (38.2); Basic pronouns (32.8); Non-copular auxiliaries (27.9)
- of the useful ones, absence-driven: Vocative / address particles
- zero: Interrogatives, Numeral classifiers / count markers, Temporal / directional adverbs, Negation particles, Definiteness / determiner markers, Light / compound verb patterns, Negative auxiliaries, Honorific verb agreement, Question / tag particles, Clitics / enclitics
- exact vs family: Copulas exact 76.4 / family 79.1; Vocative / address particles exact 68.2 / family 54.9; Locative / deictic adverbs exact 38.2 / family 48.2; Basic pronouns exact 32.8 / family 0.6; Non-copular auxiliaries exact 27.9 / family 36.4

| rank | parameter | coverage% | distinct | precision | stability | ablation | exact | family | status | observed markers |
|--|--|--|--|--|--|--|--|--|--|--|
| 1 | 1. Copulas | 93.6 | 65.7 | 2.9 | 95.6 | 100 | 76.4 | 79.1 | strong | present | हैं [48 in Khariboli / 148 elsewhere]; है [94 in Khariboli / 398 elsewhere]; बा [11 in Khariboli / 53 elsewhere]; हो [5 in Khariboli / 42 elsewhere] |
| 2 | 37. Vocative / address particles | 1.6 | 60.9 | null | null | 89.1 | 68.2 | 54.9 | strong | absent |  |
| 3 | 32. Locative / deictic adverbs | 48 | 20.5 | 4.1 | 87.5 | 35.2 | 38.2 | 48.2 | weak | present | वहीं [2 in Khariboli / 2 elsewhere]; यहां [36 in Khariboli / 121 elsewhere]; अंदर [5 in Khariboli / 17 elsewhere]; बाहर [5 in Khariboli / 17 elsewhere] |
| 4 | 19. Basic pronouns | 0 | 50.8 | null | null | 29.8 | 32.8 | 0.6 | weak | absent |  |
| 5 | 2. Non-copular auxiliaries | 42.4 | 21.2 | 4.8 | 65.7 | 17 | 27.9 | 36.4 | weak | present | रहा [36 in Khariboli / 121 elsewhere]; रहे [26 in Khariboli / 89 elsewhere]; रही [23 in Khariboli / 93 elsewhere] |
| 6 | 12. Gender agreement | 56.8 | 28.4 | 4.2 | 76.6 | 5.4 | 27.5 | 39.4 | weak | present | मिलती [3 in Khariboli / 0 elsewhere]; बैठी [2 in Khariboli / 1 elsewhere]; आई [2 in Khariboli / 4 elsewhere]; बनी [4 in Khariboli / 9 elsewhere] |
| 7 | 24. Demonstratives | 33.6 | 5.9 | 3.4 | 100 | 18.6 | 26.2 | 24.7 | weak | present | यह [11 in Khariboli / 43 elsewhere]; इस [6 in Khariboli / 27 elsewhere]; ये [21 in Khariboli / 101 elsewhere]; वो [3 in Khariboli / 22 elsewhere] |
| 8 | 20. Oblique pronouns | 15.2 | 24.7 | 13.5 | 100 | 0 | 21.3 | 30.5 | weak | present | हमें [10 in Khariboli / 18 elsewhere]; इसमें [8 in Khariboli / 18 elsewhere] |
| 9 | 11. Number agreement | 34.4 | 14.4 | 4.7 | 100 | 0 | 21.2 | 16.1 | weak | present | रखे [4 in Khariboli / 12 elsewhere]; बैठे [6 in Khariboli / 20 elsewhere]; रहे [26 in Khariboli / 89 elsewhere]; बने [3 in Khariboli / 10 elsewhere] |
| 10 | 29. Case / postposition system | 75.2 | 0 | 0.1 | 100 | 0 | 20.0 | 20.4 | weak | present | ने [3 in Khariboli / 9 elsewhere]; साथ [2 in Khariboli / 6 elsewhere]; पर [30 in Khariboli / 120 elsewhere]; ऊपर [13 in Khariboli / 57 elsewhere] |
| 11 | 16. Causative / passive morphology | 26.4 | 27.8 | 9.1 | 47.1 | 0 | 18.3 | 35.0 | negligible | present | दिखाई [28 in Khariboli / 91 elsewhere] |
| 12 | 36. Discourse / emphatic / topic / focus particles | 35.2 | 0 | 0 | 100 | 0 | 17.0 | 17.4 | negligible | absent | ही [10 in Khariboli / 49 elsewhere]; भी [30 in Khariboli / 213 elsewhere]; अच्छा [6 in Khariboli / 49 elsewhere] |
| 13 | 34. Conjunctions | 39.2 | 0 | 0.8 | 88 | 0 | 16.8 | 20.3 | negligible | present | और [47 in Khariboli / 252 elsewhere]; आ [4 in Khariboli / 49 elsewhere] |
| 14 | 15. Participles / converbs | 25.6 | 9.3 | 4.9 | 85 | 0 | 16.7 | 34.0 | negligible | present | हुई [18 in Khariboli / 54 elsewhere]; हुए [14 in Khariboli / 49 elsewhere]; हुआ [9 in Khariboli / 81 elsewhere] |
| 15 | 39. Comparative / degree markers | 31.2 | 0 | 0.8 | 100 | 0 | 16.4 | 23.4 | negligible | present | ज्यादा [3 in Khariboli / 9 elsewhere]; काफी [8 in Khariboli / 32 elsewhere]; बहुत [31 in Khariboli / 209 elsewhere] |
| 16 | 27. Relative / correlative forms | 18.4 | 0 | 1.2 | 100 | 0 | 13.9 | 16.7 | negligible | present | जैसा [5 in Khariboli / 13 elsewhere]; जहां [3 in Khariboli / 17 elsewhere]; जो [12 in Khariboli / 75 elsewhere] |
| 17 | 28. Indefinite / quantifier paradigms | 32 | 0 | 0.4 | 62.7 | 0 | 12.7 | 18.4 | negligible | present | सारी [11 in Khariboli / 35 elsewhere]; सारे [12 in Khariboli / 41 elsewhere]; हर [2 in Khariboli / 10 elsewhere]; कई [5 in Khariboli / 26 elsewhere] |
| 18 | 35. Subordinators / complementizers | 8 | 0 | 6.5 | 100 | 0 | 12.6 | 16.9 | negligible | present | कि [10 in Khariboli / 36 elsewhere] |
| 19 | 8. Aspect morphology | 11.2 | 0 | 0 | 100 | 0 | 12.2 | 11.3 | negligible | absent | मिलती [3 in Khariboli / 0 elsewhere] |
| 20 | 7. Tense morphology | 28 | 0 | 0.7 | 60.3 | 0 | 11.7 | 21.1 | negligible | present | बैठी [2 in Khariboli / 1 elsewhere]; लिखल [2 in Khariboli / 3 elsewhere]; बनी [4 in Khariboli / 9 elsewhere]; रखल [2 in Khariboli / 5 elsewhere] |
| 21 | 30. Plural markers | 15.2 | 0 | 0 | 67.7 | 2.5 | 10.8 | 13.5 | negligible | absent | मछलियां [2 in Khariboli / 1 elsewhere]; कुर्सियों [2 in Khariboli / 2 elsewhere]; बच्चों [2 in Khariboli / 3 elsewhere]; खिडकियां [2 in Khariboli / 7 elsewhere] |
| 22 | 17. Resultative / completive auxiliaries | 2.4 | 0 | 0 | null | 18.7 | 8.8 | 9.4 | negligible | absent | गया [2 in Khariboli / 23 elsewhere] |
| 23 | 14. Infinitives / non-finite forms | 8.8 | 0 | 0 | 65.5 | 0 | 8.3 | 11.9 | negligible | absent | खाने [2 in Khariboli / 3 elsewhere]; पानी [3 in Khariboli / 26 elsewhere]; देखने [2 in Khariboli / 26 elsewhere] |
| 24 | 21. Genitive / possessive pronouns | 8 | 0 | 5.4 | 38.7 | 0 | 6.3 | 12.3 | negligible | present | उनके [3 in Khariboli / 2 elsewhere]; आपके [2 in Khariboli / 2 elsewhere]; उसके [2 in Khariboli / 8 elsewhere]; इसके [2 in Khariboli / 8 elsewhere] |
| 25 | 10. Person agreement | 4 | 9.5 | 0 | 14.6 | 0.4 | 4.8 | 13.7 | negligible | absent | हो [5 in Khariboli / 42 elsewhere] |
| 26 | 4. Modal auxiliaries | 2.4 | 0 | 0 | null | 6.8 | 3.6 | 6.1 | negligible | absent | सकते [2 in Khariboli / 28 elsewhere] |
| 27 | 22. Honorific pronouns | 4 | 0 | 7.7 | 0 | 0 | 1.9 | 16.5 | negligible | present | आपको [4 in Khariboli / 5 elsewhere]; आप [5 in Khariboli / 17 elsewhere] |
| 28 | 23. Reflexive / reciprocal pronouns | 3.2 | 0 | 4.7 | null | 0 | 1.5 | 10.8 | negligible | present | अपने [2 in Khariboli / 3 elsewhere]; अपनी [2 in Khariboli / 3 elsewhere] |
| 29 | 3. Existential/possessive constructions | 0 | 4.1 | null | null | 0 | 1.4 | 4.6 | negligible | absent |  |
| 30 | 9. Mood / imperative / subjunctive | 0.8 | 3.4 | null | null | 0 | 1.3 | 0.9 | negligible | absent |  |
| 31 | 25. Interrogatives | 2.4 | 0 | 2 | null | 0 | 0.9 | 0.3 | zero | present | कितना [3 in Khariboli / 6 elsewhere] |
| 32 | 31. Numeral classifiers / count markers | 4 | 0 | 0 | 0 | 0 | 0.8 | 6.1 | zero | absent | एगो [4 in Khariboli / 34 elsewhere] |
| 33 | 33. Temporal / directional adverbs | 3.2 | 0 | 0 | null | 0 | 0.7 | 4.7 | zero | absent | दिन [2 in Khariboli / 2 elsewhere] |
| 34 | 5. Negation particles | 2.4 | 0 | 0 | null | 0 | 0.5 | 2.3 | zero | absent | नहीं [2 in Khariboli / 15 elsewhere] |
| 35 | 38. Definiteness / determiner markers | 0.8 | 0 | null | null | 0.4 | 0.4 | 1.3 | zero | absent |  |
| 36 | 18. Light / compound verb patterns | 0.8 | 0 | null | null | 0 | 0.2 | 0.2 | zero | absent |  |
| 37 | 6. Negative auxiliaries | 0 | null | null | null | 0 | 0.0 | 0.0 | zero | - |  |
| 37 | 13. Honorific verb agreement | 0 | null | null | null | 0 | 0.0 | 0.0 | zero | - |  |
| 37 | 26. Question / tag particles | 0 | 0 | null | null | null | 0.0 | 0.0 | zero | absent |  |
| 37 | 40. Clitics / enclitics | 0 | 0 | null | null | null | 0.0 | 0.0 | zero | absent |  |

## Kumaoni (family: Pahari; n=125; full-model OvR AUC=0.651)
- materially useful (score>=40): **3**; weak-or-better (>=20): 9; effectively zero (<1): 11
- top 5: Participles / converbs (64.6); Numeral classifiers / count markers (49.2); Aspect morphology (40.6); Vocative / address particles (31.1); Gender agreement (30.0)
- of the useful ones, absence-driven: Numeral classifiers / count markers, Aspect morphology
- zero: Modal auxiliaries, Basic pronouns, Negation particles, Question / tag particles, Temporal / directional adverbs, Mood / imperative / subjunctive, Light / compound verb patterns, Interrogatives, Negative auxiliaries, Honorific verb agreement, Clitics / enclitics
- exact vs family: Participles / converbs exact 64.6 / family 6.0; Numeral classifiers / count markers exact 49.2 / family 25.3; Aspect morphology exact 40.6 / family 47.3; Vocative / address particles exact 31.1 / family 11.4; Gender agreement exact 30.0 / family 18.2

| rank | parameter | coverage% | distinct | precision | stability | ablation | exact | family | status | observed markers |
|--|--|--|--|--|--|--|--|--|--|--|
| 1 | 15. Participles / converbs | 35.2 | 50.2 | 12.1 | 31.5 | 100 | 64.6 | 6.0 | strong | present | हुए [22 in Kumaoni / 41 elsewhere]; हुई [19 in Kumaoni / 53 elsewhere]; हुआ [20 in Kumaoni / 70 elsewhere] |
| 2 | 31. Numeral classifiers / count markers | 0 | 63.4 | null | null | 52.7 | 49.2 | 25.3 | supporting | absent |  |
| 3 | 8. Aspect morphology | 5.6 | 23.5 | 0 | 100 | 59 | 40.6 | 47.3 | supporting | absent | होता [2 in Kumaoni / 4 elsewhere]; पीला [2 in Kumaoni / 9 elsewhere] |
| 4 | 37. Vocative / address particles | 22.4 | 34.4 | 12.8 | 47.1 | 28.5 | 31.1 | 11.4 | weak | present | जी [24 in Kumaoni / 40 elsewhere]; ए [2 in Kumaoni / 13 elsewhere] |
| 5 | 12. Gender agreement | 52.8 | 13 | 2.9 | 81.1 | 20.5 | 30.0 | 18.2 | weak | present | रखीं [2 in Kumaoni / 0 elsewhere]; करा [3 in Kumaoni / 2 elsewhere]; लगीं [6 in Kumaoni / 10 elsewhere]; होता [2 in Kumaoni / 4 elsewhere] |
| 6 | 23. Reflexive / reciprocal pronouns | 0 | 34.4 | null | null | 24.1 | 24.3 | 0.4 | weak | absent |  |
| 7 | 32. Locative / deictic adverbs | 48 | 20.5 | 4.1 | 72.4 | 0 | 22.6 | 12.0 | weak | present | यख [12 in Kumaoni / 8 elsewhere]; चारों [3 in Kumaoni / 6 elsewhere]; पीछे [9 in Kumaoni / 23 elsewhere]; लगे [10 in Kumaoni / 31 elsewhere] |
| 8 | 29. Case / postposition system | 80.8 | 6.4 | 1.2 | 86.4 | 0 | 20.4 | 18.6 | weak | present | कु [10 in Kumaoni / 16 elsewhere]; मा [14 in Kumaoni / 25 elsewhere]; की [40 in Kumaoni / 146 elsewhere]; पे [14 in Kumaoni / 59 elsewhere] |
| 9 | 36. Discourse / emphatic / topic / focus particles | 44 | 11.6 | 3.4 | 79.6 | 0 | 20.2 | 24.0 | weak | present | अरे [4 in Kumaoni / 7 elsewhere]; मतलब [2 in Kumaoni / 6 elsewhere]; भी [43 in Kumaoni / 200 elsewhere]; तो [4 in Kumaoni / 23 elsewhere] |
| 10 | 7. Tense morphology | 36 | 17.7 | 5 | 67 | 0 | 19.1 | 15.4 | negligible | present | रखीं [2 in Kumaoni / 0 elsewhere]; करा [3 in Kumaoni / 2 elsewhere]; लगीं [6 in Kumaoni / 10 elsewhere]; रखा [7 in Kumaoni / 19 elsewhere] |
| 10 | 21. Genitive / possessive pronouns | 10.4 | 12.1 | 11.3 | 80.9 | 10.5 | 19.1 | 1.2 | negligible | present | इसकी [2 in Kumaoni / 0 elsewhere]; उनकी [2 in Kumaoni / 1 elsewhere]; उसके [4 in Kumaoni / 6 elsewhere]; हमारा [2 in Kumaoni / 3 elsewhere] |
| 12 | 1. Copulas | 76 | 0 | 0 | 84.2 | 0.8 | 18.7 | 71.9 | negligible | absent | छन [23 in Kumaoni / 15 elsewhere]; छ [7 in Kumaoni / 23 elsewhere]; हैं [39 in Kumaoni / 157 elsewhere]; है [63 in Kumaoni / 429 elsewhere] |
| 13 | 34. Conjunctions | 40 | 0 | 1.1 | 100 | 0 | 18.2 | 18.3 | negligible | present | अर [2 in Kumaoni / 0 elsewhere]; या [6 in Kumaoni / 16 elsewhere]; और [40 in Kumaoni / 259 elsewhere]; आ [4 in Kumaoni / 49 elsewhere] |
| 14 | 11. Number agreement | 32.8 | 7.9 | 3.8 | 79.7 | 0.1 | 17.1 | 9.7 | negligible | present | रखीं [2 in Kumaoni / 0 elsewhere]; लगीं [6 in Kumaoni / 10 elsewhere]; बने [4 in Kumaoni / 9 elsewhere]; लगे [10 in Kumaoni / 31 elsewhere] |
| 15 | 30. Plural markers | 24.8 | 4.3 | 4.1 | 100 | 0 | 16.6 | 17.5 | negligible | present | पेडों [2 in Kumaoni / 0 elsewhere]; लकडियों [2 in Kumaoni / 0 elsewhere]; लोग [8 in Kumaoni / 66 elsewhere] |
| 16 | 28. Indefinite / quantifier paradigms | 36.8 | 1.8 | 2.6 | 79.1 | 0 | 16.1 | 22.9 | negligible | present | कई [12 in Kumaoni / 19 elsewhere]; सारी [14 in Kumaoni / 32 elsewhere]; सारा [12 in Kumaoni / 38 elsewhere]; सारे [10 in Kumaoni / 43 elsewhere] |
| 17 | 24. Demonstratives | 25.6 | 0 | 0 | 93.2 | 0 | 14.4 | 15.1 | negligible | absent | ये [23 in Kumaoni / 99 elsewhere]; ई [2 in Kumaoni / 13 elsewhere]; वो [3 in Kumaoni / 22 elsewhere]; इस [2 in Kumaoni / 31 elsewhere] |
| 18 | 39. Comparative / degree markers | 32 | 0 | 1.1 | 72.3 | 0 | 13.8 | 15.0 | negligible | present | बिल्कुल [2 in Kumaoni / 2 elsewhere]; खूब [3 in Kumaoni / 8 elsewhere]; बहुत [35 in Kumaoni / 205 elsewhere] |
| 19 | 20. Oblique pronouns | 9.6 | 0 | 3.3 | 100 | 0 | 12.4 | 1.7 | negligible | present | इसको [2 in Kumaoni / 0 elsewhere]; उसमें [2 in Kumaoni / 6 elsewhere]; इसमें [5 in Kumaoni / 21 elsewhere]; हमें [2 in Kumaoni / 26 elsewhere] |
| 20 | 14. Infinitives / non-finite forms | 9.6 | 0 | 0 | 100 | 0 | 11.9 | 13.4 | negligible | absent |  |
| 21 | 10. Person agreement | 7.2 | 0 | 0 | 100 | 0 | 11.4 | 13.5 | negligible | absent | होईं [2 in Kumaoni / 0 elsewhere]; हो [4 in Kumaoni / 43 elsewhere] |
| 22 | 2. Non-copular auxiliaries | 31.2 | 0 | 0 | 49.8 | 0 | 11.2 | 32.3 | negligible | absent | रही [18 in Kumaoni / 98 elsewhere]; रहे [17 in Kumaoni / 98 elsewhere]; रहा [20 in Kumaoni / 137 elsewhere] |
| 23 | 27. Relative / correlative forms | 21.6 | 1.7 | 3.9 | 41.2 | 0 | 9.5 | 8.7 | negligible | present | जो [17 in Kumaoni / 70 elsewhere]; जैसा [3 in Kumaoni / 15 elsewhere]; जे [2 in Kumaoni / 11 elsewhere]; जहां [3 in Kumaoni / 17 elsewhere] |
| 24 | 16. Causative / passive morphology | 12.8 | 0 | 0 | 48.3 | 0 | 7.4 | 16.6 | negligible | absent | दिखाई [12 in Kumaoni / 107 elsewhere] |
| 25 | 35. Subordinators / complementizers | 6.4 | 0 | 2.3 | 23.7 | 0 | 4.0 | 11.3 | negligible | present | कि [6 in Kumaoni / 40 elsewhere] |
| 26 | 17. Resultative / completive auxiliaries | 5.6 | 0 | 5.7 | 8.5 | 0 | 2.8 | 1.2 | negligible | present | गया [6 in Kumaoni / 19 elsewhere] |
| 27 | 38. Definiteness / determiner markers | 2.4 | 0 | 12.1 | null | 0 | 2.5 | 1.7 | negligible | present |  |
| 28 | 3. Existential/possessive constructions | 0 | 4.1 | null | null | 1.2 | 2.0 | 0.2 | negligible | absent |  |
| 29 | 22. Honorific pronouns | 3.2 | 0 | 3.3 | null | 0 | 1.3 | 18.4 | negligible | present | आपको [2 in Kumaoni / 7 elsewhere]; आप [3 in Kumaoni / 19 elsewhere] |
| 30 | 4. Modal auxiliaries | 3.2 | 0 | 0 | null | 0 | 0.7 | 8.8 | zero | absent | सकते [3 in Kumaoni / 27 elsewhere] |
| 30 | 19. Basic pronouns | 3.2 | 0 | 0 | null | 0 | 0.7 | 8.3 | zero | absent | हम [3 in Kumaoni / 25 elsewhere] |
| 32 | 5. Negation particles | 2.4 | 0 | 0 | null | 0 | 0.5 | 9.2 | zero | absent | ना [2 in Kumaoni / 6 elsewhere]; नहीं [2 in Kumaoni / 15 elsewhere] |
| 32 | 26. Question / tag particles | 0.8 | 0 | null | null | null | 0.5 | 0.2 | zero | present |  |
| 32 | 33. Temporal / directional adverbs | 2.4 | 0 | 0 | null | 0 | 0.5 | 10.6 | zero | absent | फिर [2 in Kumaoni / 4 elsewhere] |
| 35 | 9. Mood / imperative / subjunctive | 1.6 | 0 | null | null | 0 | 0.4 | 0.4 | zero | absent | देखिये [2 in Kumaoni / 3 elsewhere] |
| 35 | 18. Light / compound verb patterns | 1.6 | 0 | null | null | 0 | 0.4 | 0.3 | zero | present |  |
| 37 | 25. Interrogatives | 0.8 | 0 | null | null | 0.1 | 0.3 | 0.3 | zero | absent |  |
| 38 | 6. Negative auxiliaries | 0 | null | null | null | 0 | 0.0 | 0.0 | zero | - |  |
| 38 | 13. Honorific verb agreement | 0 | null | null | null | 0 | 0.0 | 0.0 | zero | - |  |
| 38 | 40. Clitics / enclitics | 0 | 0 | null | null | null | 0.0 | 0.0 | zero | absent |  |

## Cross-language summary (important = exact score >=40; weak/zero = <20)

| parameter | languages where important | languages where weak/zero |
|--|--|--|
| 1. Copulas | Hindi, Garhwali, Khariboli | Chhattisgarhi, Kumaoni |
| 2. Non-copular auxiliaries | Hindi, Garhwali | Maithili, Kumaoni |
| 3. Existential/possessive constructions | - | Hindi, Bhojpuri, Maithili, Chhattisgarhi, Rajasthani, Garhwali, Khariboli, Kumaoni |
| 4. Modal auxiliaries | - | Hindi, Bhojpuri, Maithili, Chhattisgarhi, Rajasthani, Garhwali, Khariboli, Kumaoni |
| 5. Negation particles | - | Hindi, Bhojpuri, Maithili, Chhattisgarhi, Garhwali, Khariboli, Kumaoni |
| 6. Negative auxiliaries | - | Hindi, Bhojpuri, Maithili, Chhattisgarhi, Rajasthani, Garhwali, Khariboli, Kumaoni |
| 7. Tense morphology | - | Hindi, Chhattisgarhi, Garhwali, Khariboli, Kumaoni |
| 8. Aspect morphology | Bhojpuri, Kumaoni | Hindi, Maithili, Chhattisgarhi, Khariboli |
| 9. Mood / imperative / subjunctive | - | Hindi, Bhojpuri, Maithili, Chhattisgarhi, Rajasthani, Garhwali, Khariboli, Kumaoni |
| 10. Person agreement | - | Hindi, Bhojpuri, Maithili, Chhattisgarhi, Rajasthani, Garhwali, Khariboli, Kumaoni |
| 11. Number agreement | - | Bhojpuri, Maithili, Chhattisgarhi, Rajasthani, Kumaoni |
| 12. Gender agreement | Bhojpuri, Maithili | Chhattisgarhi, Rajasthani |
| 13. Honorific verb agreement | - | Hindi, Bhojpuri, Maithili, Chhattisgarhi, Rajasthani, Garhwali, Khariboli, Kumaoni |
| 14. Infinitives / non-finite forms | - | Hindi, Bhojpuri, Chhattisgarhi, Rajasthani, Garhwali, Khariboli, Kumaoni |
| 15. Participles / converbs | Hindi, Kumaoni | Bhojpuri, Chhattisgarhi, Khariboli |
| 16. Causative / passive morphology | - | Maithili, Chhattisgarhi, Rajasthani, Khariboli, Kumaoni |
| 17. Resultative / completive auxiliaries | - | Bhojpuri, Maithili, Chhattisgarhi, Garhwali, Khariboli, Kumaoni |
| 18. Light / compound verb patterns | - | Hindi, Maithili, Chhattisgarhi, Rajasthani, Garhwali, Khariboli, Kumaoni |
| 19. Basic pronouns | - | Hindi, Bhojpuri, Maithili, Chhattisgarhi, Rajasthani, Garhwali, Kumaoni |
| 20. Oblique pronouns | - | Bhojpuri, Maithili, Chhattisgarhi, Garhwali, Kumaoni |
| 21. Genitive / possessive pronouns | - | Hindi, Bhojpuri, Maithili, Chhattisgarhi, Rajasthani, Garhwali, Khariboli, Kumaoni |
| 22. Honorific pronouns | - | Hindi, Bhojpuri, Maithili, Chhattisgarhi, Rajasthani, Garhwali, Khariboli, Kumaoni |
| 23. Reflexive / reciprocal pronouns | - | Hindi, Bhojpuri, Maithili, Chhattisgarhi, Rajasthani, Garhwali, Khariboli |
| 24. Demonstratives | - | Hindi, Bhojpuri, Maithili, Chhattisgarhi, Garhwali, Kumaoni |
| 25. Interrogatives | - | Hindi, Bhojpuri, Chhattisgarhi, Rajasthani, Garhwali, Khariboli, Kumaoni |
| 26. Question / tag particles | - | Hindi, Bhojpuri, Maithili, Chhattisgarhi, Rajasthani, Garhwali, Khariboli, Kumaoni |
| 27. Relative / correlative forms | - | Hindi, Bhojpuri, Maithili, Chhattisgarhi, Rajasthani, Garhwali, Khariboli, Kumaoni |
| 28. Indefinite / quantifier paradigms | - | Hindi, Bhojpuri, Maithili, Rajasthani, Garhwali, Khariboli, Kumaoni |
| 29. Case / postposition system | - | Hindi |
| 30. Plural markers | - | Hindi, Bhojpuri, Maithili, Chhattisgarhi, Rajasthani, Garhwali, Khariboli, Kumaoni |
| 31. Numeral classifiers / count markers | Bhojpuri, Maithili, Kumaoni | Chhattisgarhi, Rajasthani, Garhwali, Khariboli |
| 32. Locative / deictic adverbs | Hindi | Maithili, Rajasthani |
| 33. Temporal / directional adverbs | - | Hindi, Bhojpuri, Maithili, Chhattisgarhi, Rajasthani, Garhwali, Khariboli, Kumaoni |
| 34. Conjunctions | - | Chhattisgarhi, Garhwali, Khariboli, Kumaoni |
| 35. Subordinators / complementizers | - | Hindi, Bhojpuri, Maithili, Chhattisgarhi, Garhwali, Khariboli, Kumaoni |
| 36. Discourse / emphatic / topic / focus particles | - | Hindi, Bhojpuri, Maithili, Chhattisgarhi, Garhwali, Khariboli |
| 37. Vocative / address particles | Chhattisgarhi, Khariboli | Bhojpuri, Maithili, Rajasthani, Garhwali |
| 38. Definiteness / determiner markers | - | Hindi, Maithili, Chhattisgarhi, Rajasthani, Garhwali, Khariboli, Kumaoni |
| 39. Comparative / degree markers | Maithili, Rajasthani | Bhojpuri, Chhattisgarhi, Garhwali, Khariboli, Kumaoni |
| 40. Clitics / enclitics | - | Hindi, Bhojpuri, Maithili, Chhattisgarhi, Rajasthani, Garhwali, Khariboli, Kumaoni |