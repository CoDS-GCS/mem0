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
- overlap 0.62; memory: "Caroline joined a mentorship program for LGBTQ youth last weekend, finding it rewarding to help the community."; created_at: 2026-11-10T22:39:22.404748+00:00; rank 6, combined 0.8490, semantic 0.6979, bm25 1.0000, entity_boost 0.0000
- overlap 0.56; memory: "Caroline joined a mentorship program for LGBTQ youth around the weekend of November 5, 2026, and finds it rewarding to help the community."; created_at: 2026-11-10T22:39:31.248529+00:00; rank 4, combined 0.8734, semantic 0.7468, bm25 1.0000, entity_boost 0.0000
- overlap 0.50; memory: "Caroline joined a mentorship program for LGBTQ youth around November 5, 2026, finding it rewarding to help the community."; created_at: 2026-11-10T22:39:20.369298+00:00; rank 1, combined 0.8926, semantic 0.7852, bm25 1.0000, entity_boost 0.0000

## Top 5 retrieved memories
- rank 1: "Caroline joined a mentorship program for LGBTQ youth around November 5, 2026, finding it rewarding to help the community."; created_at: 2026-11-10T22:39:20.369298+00:00; combined 0.8926, semantic 0.7852, bm25 1.0000, entity_boost 0.0000
- rank 2: "Caroline joined a mentorship program for LGBTQ youth around November 2026, finding it rewarding to help the community."; created_at: 2026-11-10T22:39:36.146427+00:00; combined 0.8883, semantic 0.7767, bm25 1.0000, entity_boost 0.0000
- rank 3: "Caroline joined a mentorship program for LGBTQ youth around November 5, 2026, and finds it rewarding to help the community, noting the resilience and strength of the young individuals she supports."; created_at: 2026-11-10T22:39:26.412207+00:00; combined 0.8804, semantic 0.7608, bm25 1.0000, entity_boost 0.0000
- rank 4: "Caroline joined a mentorship program for LGBTQ youth around the weekend of November 5, 2026, and finds it rewarding to help the community."; created_at: 2026-11-10T22:39:31.248529+00:00; combined 0.8734, semantic 0.7468, bm25 1.0000, entity_boost 0.0000
- rank 5: "Caroline is participating in a mentorship program for LGBTQ youth, which she finds rewarding and inspiring as she helps young individuals build confidence and positive strategies."; created_at: 2026-11-10T22:39:40.803572+00:00; combined 0.8597, semantic 0.7193, bm25 1.0000, entity_boost 0.0000

## Cutoff results
- top_10: judgment=WRONG; generated_answer="Around the weekend of November 5, 2026 (i.e., last weekend before Nov 10, 2026)."; reason="The generated answer gives a date in November 2026, which does not match or fall within 14 days of the gold answer’s weekend before July 17, 2023, so it contains no correct item."
- top_20: judgment=WRONG; generated_answer="Around the weekend of November 5, 2026."; reason="The generated date (November 2026) is entirely different from the gold timeframe (the weekend before 17 July 2023) and far outside the allowed tolerance."
- top_50: judgment=WRONG; generated_answer="Around November 5, 2026 (the weekend of November 5, 2026)."; reason="The generated date in November 2026 does not match the gold answer of the weekend before 17 July 2023 and shares no overlapping item."
- top_200: judgment=WRONG; generated_answer="Around November 5th (the weekend of Nov 5)."; reason="The answer gives the weekend of November 5, which does not match the gold date of the weekend before 17 July 2023."
