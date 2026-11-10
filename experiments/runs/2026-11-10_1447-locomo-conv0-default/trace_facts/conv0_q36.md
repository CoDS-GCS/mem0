# conv0_q36

- Question: When did Caroline join a mentorship program?
- Category: temporal
- Gold answer: The weekend before 17 July 2023
- Reference date: 9:55 am on 22 October, 2023

## Evidence turns
- D9:2 (session 9, 2:31 pm on 17 July, 2023), Caroline: "Hey Melanie! That sounds great! Last weekend I joined a mentorship program for LGBTQ youth - it's really rewarding to help the community."

## Stored memory candidates
Candidates by word overlap; whether the needed memory was stored is for the analyst to decide.

### candidates for D9:2
- overlap 0.62; memory: "Caroline joined a mentorship program for LGBTQ youth last weekend, finding it rewarding to help the community."; created_at: 2026-11-10T14:56:55.110120+00:00; rank 5, combined 0.8743, semantic 0.6980, bm25 1.0000, entity_boost 0.4878
- overlap 0.50; memory: "Caroline joined a mentorship program for LGBTQ youth around November 5, 2026, and finds it rewarding to help the community."; created_at: 2026-11-10T14:56:52.880284+00:00; rank 2, combined 0.9066, semantic 0.7788, bm25 1.0000, entity_boost 0.4878
- overlap 0.50; memory: "Caroline joined a mentorship program for LGBTQ youth around November 10, 2026, and finds it rewarding to help the community."; created_at: 2026-11-10T14:56:59.726690+00:00; rank 1, combined 0.9069, semantic 0.7794, bm25 1.0000, entity_boost 0.4878

## Top 5 retrieved memories
- rank 1: "Caroline joined a mentorship program for LGBTQ youth around November 10, 2026, and finds it rewarding to help the community."; created_at: 2026-11-10T14:56:59.726690+00:00; combined 0.9069, semantic 0.7794, bm25 1.0000, entity_boost 0.4878
- rank 2: "Caroline joined a mentorship program for LGBTQ youth around November 5, 2026, and finds it rewarding to help the community."; created_at: 2026-11-10T14:56:52.880284+00:00; combined 0.9066, semantic 0.7788, bm25 1.0000, entity_boost 0.4878
- rank 3: "Caroline joined a mentorship program for LGBTQ youth around November 2026, finding it rewarding to help the community."; created_at: 2026-11-10T14:57:04.930478+00:00; combined 0.9058, semantic 0.7767, bm25 1.0000, entity_boost 0.4878
- rank 4: "Caroline joined a mentorship program for LGBTQ youth around November 2026, finding it rewarding to help the community."; created_at: 2026-11-10T14:57:10.673118+00:00; combined 0.9058, semantic 0.7767, bm25 1.0000, entity_boost 0.4878
- rank 5: "Caroline joined a mentorship program for LGBTQ youth last weekend, finding it rewarding to help the community."; created_at: 2026-11-10T14:56:55.110120+00:00; combined 0.8743, semantic 0.6980, bm25 1.0000, entity_boost 0.4878

## Cutoff results
- top_10: judgment=WRONG; generated_answer="Around November 5, 2026."; reason="The generated date (around November 5, 2026) does not match or fall within the gold timeframe (the weekend before July 17, 2023)."
- top_20: judgment=WRONG; generated_answer="Early November 2026 — around November 5, 2026 (i.e., the weekend just before November 10)."; reason="The generated answer gives a date in November 2026, which does not match the gold answer of the weekend before July 17, 2023."
- top_50: judgment=WRONG; generated_answer="Around November 5, 2026."; reason="The generated date (November 5, 2026) does not match the gold timeframe (the weekend before July 17, 2023) and is far outside the allowed tolerance."
- top_200: judgment=WRONG; generated_answer="Around November 5, 2026."; reason="The generated date (November 5, 2026) does not match or overlap with the gold answer’s timeframe (the weekend before July 17, 2023)."
