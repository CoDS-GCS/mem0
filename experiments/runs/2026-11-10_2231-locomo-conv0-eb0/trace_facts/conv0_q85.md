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
- overlap 0.73; memory: "Caroline is researching adoption agencies as it has been her dream to have a family and provide a loving home to children in need."; created_at: 2026-11-10T22:33:39.331332+00:00; rank 80, combined 0.2746, semantic 0.5032, bm25 0.0461, entity_boost 0.0000
- overlap 0.55; memory: "Melanie expressed that Caroline's decision to give a home to needy kids through adoption is a loving way to build a family, emphasizing that the children will be supported and happy in their new home."; created_at: 2026-11-10T22:48:02.445625+00:00; not retrieved
- overlap 0.45; memory: "Caroline's goal is to give children a loving home through adoption, and she feels grateful for the support from friends and mentors as she works to turn her dream into a reality."; created_at: 2026-11-10T22:33:44.219135+00:00; rank 58, combined 0.2846, semantic 0.5233, bm25 0.0459, entity_boost 0.0000

## Top 5 retrieved memories
- rank 1: "Caroline will start thinking about what activities they can do for their planned summer outing with Melanie in 2027."; created_at: 2026-11-10T22:42:22.037454+00:00; combined 0.8426, semantic 0.6853, bm25 1.0000, entity_boost 0.0000
- rank 2: "Caroline is looking forward to making awesome memories with Melanie during their planned summer outing."; created_at: 2026-11-10T22:42:20.290142+00:00; combined 0.8381, semantic 0.6761, bm25 1.0000, entity_boost 0.0000
- rank 3: "Caroline plans to continue her education and explore career options, which she finds exciting."; created_at: 2026-11-10T22:33:07.439987+00:00; combined 0.8330, semantic 0.6823, bm25 0.9836, entity_boost 0.0000
- rank 4: "Caroline and Melanie are planning a special outing for the summer to catch up and explore nature together."; created_at: 2026-11-10T22:42:31.108493+00:00; combined 0.8185, semantic 0.6371, bm25 1.0000, entity_boost 0.0000
- rank 5: "Melanie agreed with Caroline to plan something special for the summer of 2027."; created_at: 2026-11-10T22:42:18.530535+00:00; combined 0.8128, semantic 0.6256, bm25 1.0000, entity_boost 0.0000

## Cutoff results
- top_10: judgment=WRONG; generated_answer="Caroline is planning a special summer outing with Melanie—just the two of them—to catch up, explore nature, and make memories, and she’s already brainstorming activities for it."; reason="The generated answer describes a summer outing with Melanie, which does not overlap with the gold answer of researching adoption agencies."
- top_20: judgment=WRONG; generated_answer="Caroline plans a special outing with Melanie this summer to catch up and explore nature together; she’s going to brainstorm activities for it and is looking forward to making awesome memories together."; reason="The generated answer mentions a nature outing with Melanie, which does not overlap with the gold answer about researching adoption agencies."
- top_50: judgment=WRONG; generated_answer="She’s planning a special summer outing with Melanie to catch up and explore nature together, and she’ll be brainstorming activities for it so they can make great memories."; reason="The generated answer talks about a summer outing with Melanie, which does not overlap with the gold answer of researching adoption agencies."
- top_200: judgment=WRONG; generated_answer="Caroline is planning a special summer outing with Melanie to catch up and explore nature, and she’s brainstorming activities for it because she’s excited to make memories together."; reason="The generated answer talks about planning an outing with Melanie, which does not match the gold answer about researching adoption agencies."
