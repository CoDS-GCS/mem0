# conv0_q85

- Question: What are Caroline's plans for the summer?
- Category: single-hop
- Gold answer: researching adoption agencies
- Reference date: 9:55 am on 22 October, 2023

## Evidence turns
- D2:8 (session 2, 1:14 pm on 25 May, 2023), Caroline: "Researching adoption agencies — it's been a dream to have a family and give a loving home to kids who need it."

## Stored memory candidates
Candidates by word overlap; whether the needed memory was stored is for the analyst to decide.

### candidates for D2:8
- overlap 0.73; memory: "Caroline is researching adoption agencies as it has been her dream to have a family and provide a loving home to children in need."; created_at: 2026-11-10T14:48:57.880440+00:00; rank 97, combined 0.2205, semantic 0.5031, bm25 0.0464, entity_boost 0.0017
- overlap 0.45; memory: "Caroline's goal is to give children a loving home, and she feels grateful for the support from friends and mentors as she works to turn her dream of adoption into a reality."; created_at: 2026-11-10T14:49:04.046895+00:00; rank 63, combined 0.2293, semantic 0.5253, bm25 0.0462, entity_boost 0.0017
- overlap 0.45; memory: "Caroline is excited to start her adoption journey, viewing it as a dream to provide a safe and loving home for children in need."; created_at: 2026-11-10T15:05:35.668988+00:00; rank 136, combined 0.2124, semantic 0.4829, bm25 0.0463, entity_boost 0.0017

## Top 5 retrieved memories
- rank 1: "Caroline plans to continue her education and explore career options, which she finds exciting."; created_at: 2026-11-10T14:48:19.464588+00:00; combined 0.6655, semantic 0.6822, bm25 0.9816, entity_boost 0.0000
- rank 2: "Caroline expressed enthusiasm about planning their summer outing and is looking forward to making awesome memories with Melanie."; created_at: 2026-11-10T15:00:15.122890+00:00; combined 0.6608, semantic 0.6521, bm25 1.0000, entity_boost 0.0000
- rank 3: "Caroline expressed excitement about making awesome memories with Melanie during their upcoming special outing this summer."; created_at: 2026-11-10T15:00:12.257266+00:00; combined 0.6477, semantic 0.6277, bm25 0.9898, entity_boost 0.0017
- rank 4: "Caroline is feeling inspired by autumn and is planning a few art projects."; created_at: 2026-11-10T15:02:51.303679+00:00; combined 0.6436, semantic 0.6159, bm25 0.9931, entity_boost 0.0000
- rank 5: "Caroline and Melanie are planning a special outing for the summer of 2027, expressing excitement about catching up and exploring nature together."; created_at: 2026-11-10T15:00:15.120553+00:00; combined 0.6426, semantic 0.6047, bm25 1.0000, entity_boost 0.0017

## Cutoff results
- top_10: judgment=WRONG; generated_answer="She’s planning a special just-the-two-of-them summer outing with Melanie to catch up, explore nature, and make awesome memories together."; reason="The generated answer mentions planning an outing with Melanie, which does not overlap with the gold answer of researching adoption agencies."
- top_20: judgment=WRONG; generated_answer="Caroline is planning a special summer outing with Melanie—just the two of them—to catch up, explore nature, and make awesome memories."; reason="The generated answer mentions a summer outing with Melanie, which does not match the gold plan of researching adoption agencies."
- top_50: judgment=WRONG; generated_answer="She’s planning a special outing with Melanie this summer to catch up, explore nature, and make awesome memories together."; reason="The generated answer talks about an outing with Melanie, which does not match the gold answer of researching adoption agencies."
- top_200: judgment=WRONG; generated_answer="She’s planning a special summer outing with Melanie to catch up, explore nature together, and make some great memories."; reason="The generated answer describes a summer outing with Melanie, which does not match the gold answer’s plan of researching adoption agencies and contains no overlapping items."
