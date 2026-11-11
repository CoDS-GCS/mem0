# conv0_q67

- Question: When did Caroline go biking with friends?
- Category: temporal
- Gold answer: The weekend before 13 September 2023
- Reference date: 9:55 am on 22 October, 2023

## Evidence turns
- D16:1 (session 16, 12:09 am on 13 September, 2023), Caroline: "Hey Mel, long time no chat! I had a wicked day out with the gang last weekend - we went biking and saw some pretty cool stuff. It was so refreshing, and the pic I'm sending is just stunning, eh?"

## Stored memory candidates
Candidates by word overlap; whether the needed memory was stored is for the analyst to decide.

### candidates for D16:1
- overlap 0.39; memory: "Caroline had a day out with friends last weekend where they went biking and saw some cool sights, describing the experience as refreshing."; created_at: 2026-11-10T22:45:23.720475+00:00; rank 1, combined 0.8582, semantic 0.7164, bm25 1.0000, entity_boost 0.0000
- overlap 0.22; memory: "Caroline had a day out biking with friends last weekend, which she found refreshing and enjoyable."; created_at: 2026-11-10T22:45:29.745131+00:00; rank 2, combined 0.8577, semantic 0.7154, bm25 1.0000, entity_boost 0.0000
- overlap 0.13; memory: "Melanie is carving out some me-time each day by running, reading, or playing her violin, which refreshes her and helps her stay present for her family."; created_at: 2026-11-10T22:33:32.307386+00:00; not retrieved

## Top 5 retrieved memories
- rank 1: "Caroline had a day out with friends last weekend where they went biking and saw some cool sights, describing the experience as refreshing."; created_at: 2026-11-10T22:45:23.720475+00:00; combined 0.8582, semantic 0.7164, bm25 1.0000, entity_boost 0.0000
- rank 2: "Caroline had a day out biking with friends last weekend, which she found refreshing and enjoyable."; created_at: 2026-11-10T22:45:29.745131+00:00; combined 0.8577, semantic 0.7154, bm25 1.0000, entity_boost 0.0000
- rank 3: "Caroline shared a stunning photo of a beach with a fence and a sunset from her biking trip with friends."; created_at: 2026-11-10T22:45:23.722908+00:00; combined 0.8171, semantic 0.6343, bm25 1.0000, entity_boost 0.0000
- rank 4: "Caroline shared a stunning photo of a sunset lake from her biking trip."; created_at: 2026-11-10T22:45:29.747043+00:00; combined 0.7593, semantic 0.5206, bm25 0.9980, entity_boost 0.0000
- rank 5: "Caroline had a picnic with friends around November 3, 2026, and shared a photo of a group of women sitting on a blanket in a park."; created_at: 2026-11-10T22:36:26.615525+00:00; combined 0.7173, semantic 0.6557, bm25 0.7789, entity_boost 0.0000

## Cutoff results
- top_10: judgment=WRONG; generated_answer="Last weekend."; reason="“Last weekend” does not specify or align with “the weekend before 13 September 2023,” so it contains no matching item from the gold answer."
- top_20: judgment=WRONG; generated_answer="Last weekend before Tuesday, Nov 10, 2026 — the weekend of Nov 7–8, 2026."; reason="The generated answer gives a date in November 2026, which does not match the gold answer of the weekend before 13 September 2023 and is far outside the allowed tolerance."
- top_50: judgment=WRONG; generated_answer="Last weekend — the weekend immediately before November 10."; reason="The generated answer cites the weekend before November 10, which does not match the gold answer’s weekend before September 13, 2023 and is far outside the 14-day tolerance."
- top_200: judgment=WRONG; generated_answer="Last weekend."; reason="“Last weekend” does not correspond to or paraphrase “the weekend before 13 September 2023,” so there is no overlap with the gold answer."
