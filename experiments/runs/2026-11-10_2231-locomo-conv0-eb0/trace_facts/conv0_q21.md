# conv0_q21

- Question: When did Caroline have a picnic?
- Category: temporal
- Gold answer: The week before 6 July 2023
- Reference date: 9:55 am on 22 October, 2023

## Evidence turns
- D6:11 (session 6, 8:18 pm on 6 July, 2023), Caroline: "Wow, that's great! It sure shows how important friendship and compassion are. It's made me appreciate how lucky I am to have my friends and family helping with my transition. They make all the difference. We even had a picnic last week!"

## Stored memory candidates
Candidates by word overlap; whether the needed memory was stored is for the analyst to decide.

### candidates for D6:11
- overlap 0.26; memory: "Caroline appreciates the importance of friendship and compassion, feeling lucky to have her friends and family supporting her during her transition."; created_at: 2026-11-10T22:36:26.611658+00:00; not retrieved
- overlap 0.22; memory: "Caroline had a picnic with friends last week, appreciating their support during her transition."; created_at: 2026-11-10T22:36:28.787809+00:00; rank 3, combined 0.8366, semantic 0.6755, bm25 0.9977, entity_boost 0.0000
- overlap 0.22; memory: "Caroline had a picnic with her friends last week, appreciating their support during her transition."; created_at: 2026-11-10T22:36:52.695172+00:00; rank 2, combined 0.8406, semantic 0.6834, bm25 0.9977, entity_boost 0.0000

## Top 5 retrieved memories
- rank 1: "Caroline had a picnic with friends around November 3, 2026, and shared a photo of a group of women sitting on a blanket in a park."; created_at: 2026-11-10T22:36:26.615525+00:00; combined 0.8809, semantic 0.7645, bm25 0.9974, entity_boost 0.0000
- rank 2: "Caroline had a picnic with her friends last week, appreciating their support during her transition."; created_at: 2026-11-10T22:36:52.695172+00:00; combined 0.8406, semantic 0.6834, bm25 0.9977, entity_boost 0.0000
- rank 3: "Caroline had a picnic with friends last week, appreciating their support during her transition."; created_at: 2026-11-10T22:36:28.787809+00:00; combined 0.8366, semantic 0.6755, bm25 0.9977, entity_boost 0.0000
- rank 4: "Caroline had a picnic with her friends last week, highlighting the support network around her."; created_at: 2026-11-10T22:36:34.117645+00:00; combined 0.8335, semantic 0.6692, bm25 0.9977, entity_boost 0.0000
- rank 5: "Caroline expressed her happiness for Melanie's enjoyable family picnic and emphasized the importance of cherishing moments together."; created_at: 2026-11-10T22:34:43.308483+00:00; combined 0.8020, semantic 0.6065, bm25 0.9975, entity_boost 0.0000

## Cutoff results
- top_10: judgment=WRONG; generated_answer="Around November 3 — last week."; reason="The gold date is the week before 6 July 2023, while the generated answer gives around November 3, which is months apart and not within the allowed tolerance."
- top_20: judgment=WRONG; generated_answer="Last week—around November 3, 2026."; reason="The generated date (around November 3, 2026) does not match the gold answer timeframe (the week before July 6, 2023)."
- top_50: judgment=WRONG; generated_answer="Around November 3, 2026 (last week relative to November 10, 2026)."; reason="The generated answer gives a date in November 2026, which does not match the gold answer’s week before July 6, 2023 and is far outside the allowed tolerance."
- top_200: judgment=WRONG; generated_answer="Last week—around November 3—Caroline had a picnic with friends."; reason="The generated answer places the picnic in early November, which does not match the gold answer’s timeframe of the week before 6 July 2023 and has no overlapping detail."
