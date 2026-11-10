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
- overlap 0.45; memory: "Melanie took her kids to a pottery workshop on November 4, 2026, where they all made their own pots, describing the experience as fun and therapeutic."; created_at: 2026-11-10T14:55:14.450510+00:00; rank 2, combined 0.8983, semantic 0.7503, bm25 1.0000, entity_boost 0.4955
- overlap 0.45; memory: "Melanie took her kids to a pottery workshop on November 3, 2026, where they all made their own pots, describing the experience as fun and therapeutic."; created_at: 2026-11-10T14:55:16.618435+00:00; rank 1, combined 0.8991, semantic 0.7523, bm25 1.0000, entity_boost 0.4955
- overlap 0.20; memory: "Caroline reached out to Melanie, mentioning that a lot has been going on since they last talked."; created_at: 2026-11-10T14:52:45.692889+00:00; rank 92, combined 0.2462, semantic 0.4494, bm25 0.1601, entity_boost 0.0059

## Top 5 retrieved memories
- rank 1: "Melanie took her kids to a pottery workshop on November 3, 2026, where they all made their own pots, describing the experience as fun and therapeutic."; created_at: 2026-11-10T14:55:16.618435+00:00; combined 0.8991, semantic 0.7523, bm25 1.0000, entity_boost 0.4955
- rank 2: "Melanie took her kids to a pottery workshop on November 4, 2026, where they all made their own pots, describing the experience as fun and therapeutic."; created_at: 2026-11-10T14:55:14.450510+00:00; combined 0.8983, semantic 0.7503, bm25 1.0000, entity_boost 0.4955
- rank 3: "Melanie's kids loved the pottery workshop, getting excited to work with clay and create their own pieces, showcasing their creativity and imagination."; created_at: 2026-11-10T14:55:19.327408+00:00; combined 0.8856, semantic 0.7184, bm25 1.0000, entity_boost 0.4955
- rank 4: "Melanie shared a photo of her kids making clay sculptures in a pottery workshop."; created_at: 2026-11-10T14:55:14.453941+00:00; combined 0.8649, semantic 0.6666, bm25 1.0000, entity_boost 0.4955
- rank 5: "Melanie made a plate in pottery class on November 9, 2026, and finds pottery to be relaxing and creative, expressing love for the craft."; created_at: 2026-11-10T15:01:24.017297+00:00; combined 0.8459, semantic 0.7237, bm25 0.9930, entity_boost 0.3979

## Cutoff results
- top_10: judgment=WRONG; generated_answer="November 3, 2026 and November 4, 2026."; reason="The generated dates (November 3–4, 2026) do not match or fall within tolerance of the gold answer’s “Friday before 15 July 2023,” so there is no overlap with the correct item."
- top_20: judgment=WRONG; generated_answer="Melanie went to the pottery workshop on November 3, 2026, and also on November 4, 2026 (with her kids)."; reason="The generated dates in November 2026 do not match the gold answer of the Friday before 15 July 2023 and are not within the allowed tolerance."
- top_50: judgment=WRONG; generated_answer="November 4"; reason="November 4 is a completely different date and not within 14 days of the Friday before 15 July 2023."
- top_200: judgment=WRONG; generated_answer="November 4, 2026."; reason="The generated date (November 4, 2026) does not match or paraphrase the gold answer’s timeframe (the Friday before 15 July 2023), so none of the correct items are present."
