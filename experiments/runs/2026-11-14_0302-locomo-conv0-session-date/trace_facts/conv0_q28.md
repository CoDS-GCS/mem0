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
- overlap 0.63; memory: "Caroline attended a council meeting for adoption on July 14, 2023, which she found inspiring and emotional, as many people expressed their desire to create loving homes for children in need. This experience made her even more determined to adopt."; created_at: 2023-07-15T13:51:00+00:00; rank 4, combined 0.8002, semantic 0.7370, bm25 1.0000, entity_boost 0.2634
- overlap 0.59; memory: "Caroline attended a council meeting for adoption on July 7, 2023, which she found inspiring and emotional, as many people wanted to create loving homes for children in need, making her more determined to adopt."; created_at: 2023-07-15T13:51:00+00:00; rank 8, combined 0.7974, semantic 0.7301, bm25 1.0000, entity_boost 0.2634
- overlap 0.59; memory: "Caroline attended a council meeting for adoption on July 7, 2023, which she found inspiring and emotional, as many people wanted to create loving homes for children in need, making her more determined to adopt."; created_at: 2023-07-15T13:51:00+00:00; rank 9, combined 0.7974, semantic 0.7301, bm25 1.0000, entity_boost 0.2634

## Top 5 retrieved memories
- rank 1: "Caroline passed the adoption agency interviews on October 20, 2023, and is excited about moving towards her goal of having a family through adoption."; created_at: 2023-10-22T09:55:00+00:00; combined 0.8292, semantic 0.7466, bm25 0.9559, entity_boost 0.3706
- rank 2: "Caroline passed the adoption agency interviews on October 20, 2023, and is excited about moving towards her goal of having a family through adoption."; created_at: 2023-10-22T09:55:00+00:00; combined 0.8292, semantic 0.7466, bm25 0.9559, entity_boost 0.3706
- rank 3: "Caroline received help from an adoption advice and assistance group she attended while preparing for the adoption process."; created_at: 2023-08-23T15:31:00+00:00; combined 0.8046, semantic 0.6791, bm25 0.9568, entity_boost 0.3756
- rank 4: "Caroline attended a council meeting for adoption on July 14, 2023, which she found inspiring and emotional, as many people expressed their desire to create loving homes for children in need. This experience made her even more determined to adopt."; created_at: 2023-07-15T13:51:00+00:00; combined 0.8002, semantic 0.7370, bm25 1.0000, entity_boost 0.2634
- rank 5: "Caroline attended a council meeting for adoption on July 7, 2023, which she found inspiring and emotional, reinforcing her determination to adopt."; created_at: 2023-07-15T13:51:00+00:00; combined 0.7996, semantic 0.7356, bm25 1.0000, entity_boost 0.2634

## Cutoff results
- top_10: judgment=CORRECT; generated_answer="July 7, 2023, and again on July 14, 2023."; reason="It includes July 14, 2023, which is the Friday before July 15, 2023."
- top_20: judgment=CORRECT; generated_answer="July 14, 2023."; reason="July 14, 2023 is the Friday before July 15, 2023, matching the gold answer."
- top_50: judgment=CORRECT; generated_answer="July 14, 2023. (She also attended one on July 7, 2023.)"; reason="July 14, 2023 is exactly the Friday before July 15, 2023, matching the gold answer, and extra details are acceptable."
- top_200: judgment=CORRECT; generated_answer="July 14, 2023."; reason="July 14, 2023 is the Friday before July 15, 2023, matching the gold answer."
