# conv0_q29

- Question: When did Melanie go to the pottery workshop?
- Category: temporal
- Gold answer: The Friday before 15 July 2023
- Reference date: 9:55 am on 22 October, 2023

## Evidence turns
- D8:2 (session 8, 1:51 pm on 15 July, 2023), Melanie: "Hey Caroline, it's been super busy here. So much since we talked! Last Fri I finally took my kids to a pottery workshop. We all made our own pots, it was fun and therapeutic!"

## Stored memory candidates
Candidates by word overlap; whether the needed memory was stored is for the analyst to decide.

### candidates for D8:2
- overlap 0.45; memory: "Melanie took her kids to a pottery workshop on November 10, 2026, where they all made their own pots, describing the experience as fun and therapeutic."; created_at: 2026-11-10T22:37:47.086210+00:00; rank 2, combined 0.8747, semantic 0.7494, bm25 1.0000, entity_boost 0.0000
- overlap 0.45; memory: "Melanie took her kids to a pottery workshop on November 3, 2026, where they all made their own pots, describing the experience as fun and therapeutic."; created_at: 2026-11-10T22:37:49.887788+00:00; rank 1, combined 0.8761, semantic 0.7522, bm25 1.0000, entity_boost 0.0000
- overlap 0.45; memory: "Melanie took her kids to a pottery workshop on November 4, 2026, where they made their own pots, finding the experience fun and therapeutic."; created_at: 2026-11-10T22:38:05.925527+00:00; rank 4, combined 0.8729, semantic 0.7458, bm25 1.0000, entity_boost 0.0000

## Top 5 retrieved memories
- rank 1: "Melanie took her kids to a pottery workshop on November 3, 2026, where they all made their own pots, describing the experience as fun and therapeutic."; created_at: 2026-11-10T22:37:49.887788+00:00; combined 0.8761, semantic 0.7522, bm25 1.0000, entity_boost 0.0000
- rank 2: "Melanie took her kids to a pottery workshop on November 10, 2026, where they all made their own pots, describing the experience as fun and therapeutic."; created_at: 2026-11-10T22:37:47.086210+00:00; combined 0.8747, semantic 0.7494, bm25 1.0000, entity_boost 0.0000
- rank 3: "Melanie took her kids to a pottery workshop on November 3, 2026, where they made their own pots, finding it fun and therapeutic."; created_at: 2026-11-10T22:38:11.358483+00:00; combined 0.8745, semantic 0.7491, bm25 1.0000, entity_boost 0.0000
- rank 4: "Melanie took her kids to a pottery workshop on November 4, 2026, where they made their own pots, finding the experience fun and therapeutic."; created_at: 2026-11-10T22:38:05.925527+00:00; combined 0.8729, semantic 0.7458, bm25 1.0000, entity_boost 0.0000
- rank 5: "Melanie's kids loved the pottery workshop on November 10, 2026, where they were excited to get their hands dirty and create with clay, showcasing their creativity and imagination."; created_at: 2026-11-10T22:37:52.119250+00:00; combined 0.8682, semantic 0.7363, bm25 1.0000, entity_boost 0.0000

## Cutoff results
- top_10: judgment=WRONG; generated_answer="November 3, 2026; November 4, 2026; and November 10, 2026."; reason="The generated dates in November 2026 do not match or fall near the gold date of the Friday before 15 July 2023, so none of the items are correct."
- top_20: judgment=WRONG; generated_answer="November 3, 2026; November 4, 2026; and November 10, 2026."; reason="The generated dates in November 2026 do not match or approximate the gold answer of the Friday before 15 July 2023, providing no overlap."
- top_50: judgment=WRONG; generated_answer="November 3, 2026; November 4, 2026; and November 10, 2026."; reason="The generated dates are in November 2026 and do not match the gold answer of the Friday before 15 July 2023."
- top_200: judgment=WRONG; generated_answer="- November 3, 2026
- November 4, 2026
- November 10, 2026"; reason="The generated dates are all in November 2026 and none match the gold answer's 'Friday before 15 July 2023' timeframe."
