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
- overlap 0.63; memory: "Caroline attended a council meeting for adoption on November 3, 2026, which she found inspiring and emotional, as many people expressed their desire to create loving homes for children in need. This experience made her even more determined to adopt."; created_at: 2026-11-10T14:55:34.906149+00:00; rank 2, combined 0.8038, semantic 0.7441, bm25 1.0000, entity_boost 0.2655
- overlap 0.59; memory: "Caroline attended a council meeting for adoption on November 3, 2026, which she found inspiring and emotional, as many people wanted to create loving homes for children in need, making her more determined to adopt."; created_at: 2026-11-10T14:55:52.272053+00:00; rank 4, combined 0.8033, semantic 0.7428, bm25 1.0000, entity_boost 0.2655
- overlap 0.19; memory: "Caroline's dream is to create a safe and loving home for children through adoption, believing that love and acceptance should be everyone's right."; created_at: 2026-11-10T15:07:58.024850+00:00; rank 44, combined 0.5961, semantic 0.5829, bm25 0.9056, entity_boost 0.0017

## Top 5 retrieved memories
- rank 1: "Caroline passed the adoption agency interviews on November 3, 2026, which is a significant step towards her goal of having a family and providing a loving home for children in need."; created_at: 2026-11-10T15:08:15.509759+00:00; combined 0.8058, semantic 0.7448, bm25 0.8991, entity_boost 0.3706
- rank 2: "Caroline attended a council meeting for adoption on November 3, 2026, which she found inspiring and emotional, as many people expressed their desire to create loving homes for children in need. This experience made her even more determined to adopt."; created_at: 2026-11-10T14:55:34.906149+00:00; combined 0.8038, semantic 0.7441, bm25 1.0000, entity_boost 0.2655
- rank 3: "Caroline passed the adoption agency interviews on November 3, 2026, and is excited and thankful as this is a significant step towards her goal of having a family."; created_at: 2026-11-10T15:07:46.605813+00:00; combined 0.8036, semantic 0.7328, bm25 0.9056, entity_boost 0.3706
- rank 4: "Caroline attended a council meeting for adoption on November 3, 2026, which she found inspiring and emotional, as many people wanted to create loving homes for children in need, making her more determined to adopt."; created_at: 2026-11-10T14:55:52.272053+00:00; combined 0.8033, semantic 0.7428, bm25 1.0000, entity_boost 0.2655
- rank 5: "Caroline passed the adoption agency interviews on November 3, 2026, and feels excited and thankful as this is a significant step towards her goal of having a family."; created_at: 2026-11-10T15:07:58.022445+00:00; combined 0.7972, semantic 0.7182, bm25 0.9043, entity_boost 0.3706

## Cutoff results
- top_10: judgment=WRONG; generated_answer="November 3, 2026."; reason="The generated date (November 3, 2026) does not match or paraphrase the gold answer’s timeframe (the Friday before July 15, 2023), providing no overlapping correct item."
- top_20: judgment=WRONG; generated_answer="November 3, 2026"; reason="The generated date (November 3, 2026) does not match the gold date window (the Friday before July 15, 2023, i.e., July 14, 2023) and is far outside the allowed tolerance."
- top_50: judgment=WRONG; generated_answer="November 3, 2026."; reason="The generated date (November 3, 2026) does not match or fall within the tolerance of the gold date (the Friday before July 15, 2023)."
- top_200: judgment=WRONG; generated_answer="November 3."; reason="The answer 'November 3' does not match or paraphrase 'the Friday before 15 July 2023' and contains no overlapping correct detail."
