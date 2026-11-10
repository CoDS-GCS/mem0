# conv0_q41

- Question: When did Caroline join a new activist group?
- Category: temporal
- Gold answer: The Tuesday before 20 July 2023
- Reference date: 9:55 am on 22 October, 2023

## Evidence turns
- D10:3 (session 10, 8:56 pm on 20 July, 2023), Caroline: "Hey Mel! A lot's happened since we last chatted - I just joined a new LGBTQ activist group last Tues. I'm meeting so many cool people who are as passionate as I am about rights and community support. I'm giving my voice and making a real difference, plus it's fulfilling in so many ways. It's just great, you know?"

## Stored memory candidates
Candidates by word overlap; whether the needed memory was stored is for the analyst to decide.

### candidates for D10:3
- overlap 0.37; memory: "Caroline joined a new LGBTQ activist group on November 3, 2026, where she is meeting many passionate individuals about rights and community support, and feels fulfilled by making a real difference."; created_at: 2026-11-10T14:57:41.612579+00:00; rank 1, combined 0.8285, semantic 0.7515, bm25 1.0000, entity_boost 0.3198
- overlap 0.37; memory: "Caroline joined a new LGBTQ activist group on November 3, 2026, where she is meeting passionate people about rights and community support, feeling fulfilled by making a real difference."; created_at: 2026-11-10T14:57:43.852515+00:00; rank 2, combined 0.8281, semantic 0.7505, bm25 1.0000, entity_boost 0.3198
- overlap 0.34; memory: "Caroline joined a new LGBTQ activist group called 'Connected LGBTQ Activists' on November 3, 2026, where she is meeting passionate people and making a difference in rights and community support."; created_at: 2026-11-10T14:58:00.733029+00:00; rank 3, combined 0.8182, semantic 0.7257, bm25 1.0000, entity_boost 0.3198

## Top 5 retrieved memories
- rank 1: "Caroline joined a new LGBTQ activist group on November 3, 2026, where she is meeting many passionate individuals about rights and community support, and feels fulfilled by making a real difference."; created_at: 2026-11-10T14:57:41.612579+00:00; combined 0.8285, semantic 0.7515, bm25 1.0000, entity_boost 0.3198
- rank 2: "Caroline joined a new LGBTQ activist group on November 3, 2026, where she is meeting passionate people about rights and community support, feeling fulfilled by making a real difference."; created_at: 2026-11-10T14:57:43.852515+00:00; combined 0.8281, semantic 0.7505, bm25 1.0000, entity_boost 0.3198
- rank 3: "Caroline joined a new LGBTQ activist group called 'Connected LGBTQ Activists' on November 3, 2026, where she is meeting passionate people and making a difference in rights and community support."; created_at: 2026-11-10T14:58:00.733029+00:00; combined 0.8182, semantic 0.7257, bm25 1.0000, entity_boost 0.3198
- rank 4: "Caroline joined a new LGBTQ activist group called 'Connected LGBTQ Activists' on November 3, 2026, where she is meeting passionate individuals dedicated to rights and community support."; created_at: 2026-11-10T14:57:49.324464+00:00; combined 0.8177, semantic 0.7244, bm25 1.0000, entity_boost 0.3198
- rank 5: "Caroline joined a new LGBTQ activist group called 'Connected LGBTQ Activists' around November 3, 2026, where she is meeting passionate people and making a difference in rights and community support."; created_at: 2026-11-10T14:58:10.313934+00:00; combined 0.8173, semantic 0.7235, bm25 1.0000, entity_boost 0.3198

## Cutoff results
- top_10: judgment=WRONG; generated_answer="November 3, 2026."; reason="The generated date (November 3, 2026) does not match or fall within the tolerated window of the gold date (the Tuesday before July 20, 2023)."
- top_20: judgment=WRONG; generated_answer="November 3, 2026."; reason="The generated date (November 3, 2026) does not match the gold date (the Tuesday before July 20, 2023) and is far outside the allowed tolerance."
- top_50: judgment=WRONG; generated_answer="November 3, 2026."; reason="The generated date (November 3, 2026) does not match or fall within 14 days of the gold timeframe (the Tuesday before 20 July 2023)."
- top_200: judgment=WRONG; generated_answer="November 3, 2026."; reason="The generated date (November 3, 2026) does not match the gold date (the Tuesday before July 20, 2023) and is not within the allowed tolerance."
