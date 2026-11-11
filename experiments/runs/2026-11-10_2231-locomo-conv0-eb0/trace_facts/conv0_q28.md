# conv0_q28

- Question: When did Caroline go to the adoption meeting?
- Category: temporal
- Gold answer: The friday before 15 July 2023
- Reference date: 9:55 am on 22 October, 2023

## Evidence turns
- D8:9 (session 8, 1:51 pm on 15 July, 2023), Caroline: "That photo is stunning! So glad you bonded over our love of nature. Last Friday I went to a council meeting for adoption. It was inspiring and emotional - so many people wanted to create loving homes for children in need. It made me even more determined to adopt."

## Stored memory candidates
Candidates by word overlap; whether the needed memory was stored is for the analyst to decide.

### candidates for D8:9
- overlap 0.22; memory: "Caroline attended a council meeting for adoption on November 3, 2026, which she found inspiring and emotional, reinforcing her determination to adopt."; created_at: 2026-11-10T22:38:11.367391+00:00; rank 1, combined 0.8750, semantic 0.7500, bm25 1.0000, entity_boost 0.0000
- overlap 0.22; memory: "Caroline's dream is to create a safe and loving home for children in need through adoption, believing that love and acceptance should be everyone's right."; created_at: 2026-11-10T22:48:07.597589+00:00; rank 39, combined 0.7467, semantic 0.5864, bm25 0.9069, entity_boost 0.0000
- overlap 0.19; memory: "Caroline's dream is to create a safe and loving home for children through adoption, emphasizing that love and acceptance should be everyone's right and that she wants these kids to experience it."; created_at: 2026-11-10T22:48:04.216738+00:00; rank 41, combined 0.7441, semantic 0.5838, bm25 0.9044, entity_boost 0.0000

## Top 5 retrieved memories
- rank 1: "Caroline attended a council meeting for adoption on November 3, 2026, which she found inspiring and emotional, reinforcing her determination to adopt."; created_at: 2026-11-10T22:38:11.367391+00:00; combined 0.8750, semantic 0.7500, bm25 1.0000, entity_boost 0.0000
- rank 2: "Caroline passed the adoption agency interviews on November 3, 2026, and is excited about moving towards her goal of having a family through adoption."; created_at: 2026-11-10T22:48:20.976086+00:00; combined 0.8531, semantic 0.7501, bm25 0.9562, entity_boost 0.0000
- rank 3: "Caroline passed the adoption agency interviews on November 3, 2026, and is excited and thankful as this is a significant step towards her goal of having a family."; created_at: 2026-11-10T22:47:58.282237+00:00; combined 0.8205, semantic 0.7327, bm25 0.9082, entity_boost 0.0000
- rank 4: "Caroline passed the adoption agency interviews on November 3, 2026, and feels excited and thankful as this is a significant step towards her goal of having a family."; created_at: 2026-11-10T22:48:07.594857+00:00; combined 0.8126, semantic 0.7182, bm25 0.9069, entity_boost 0.0000
- rank 5: "Caroline passed the adoption agency interviews on November 3, 2026, and feels excited and thankful as this is a significant step towards her goal of having a family."; created_at: 2026-11-10T22:48:26.507517+00:00; combined 0.8126, semantic 0.7182, bm25 0.9069, entity_boost 0.0000

## Cutoff results
- top_10: judgment=WRONG; generated_answer="November 3."; reason="The generated date 'November 3' does not match the gold answer 'the Friday before 15 July 2023' (around July 14, 2023) and contains no correct overlap."
- top_20: judgment=WRONG; generated_answer="November 3, 2026."; reason="The generated date (November 3, 2026) does not match or fall near the gold answer of the Friday before July 15, 2023."
- top_50: judgment=WRONG; generated_answer="November 3, 2026."; reason="The generated date (Nov 3, 2026) does not match or fall within 14 days of the gold reference (the Friday before July 15, 2023), so it contains no correct items."
- top_200: judgment=WRONG; generated_answer="November 3, 2026."; reason="The generated date (November 3, 2026) does not match or fall within the tolerance of the gold date (the Friday before 15 July 2023)."
