# conv0_q8

- Question: When did Caroline give a speech at a school?
- Category: temporal
- Gold answer: The week before 9 June 2023
- Reference date: 9:55 am on 22 October, 2023

## Evidence turns
- D3:1 (session 3, 7:55 pm on 9 June, 2023), Caroline: "Hey Melanie! How's it going? I wanted to tell you about my school event last week. It was awesome! I talked about my transgender journey and encouraged students to get involved in the LGBTQ community. It was great to see their reactions. It made me reflect on how far I've come since I started transitioning three years ago."

## Stored memory candidates
Candidates by word overlap; whether the needed memory was stored is for the analyst to decide.

### candidates for D3:1
- overlap 0.44; memory: "Caroline participated in a school event around November 3, 2026, where she talked about her transgender journey and encouraged students to get involved in the LGBTQ community, reflecting on her progress since starting her transition three years ago."; created_at: 2026-11-10T22:34:00.906146+00:00; rank 1, combined 0.8193, semantic 0.6392, bm25 0.9994, entity_boost 0.0000
- overlap 0.15; memory: "Caroline attended an LGBTQ+ pride parade last week, which made her feel a sense of belonging and showcased the growth of the community."; created_at: 2026-11-10T22:35:39.670580+00:00; rank 63, combined 0.2563, semantic 0.4665, bm25 0.0461, entity_boost 0.0000
- overlap 0.15; memory: "Caroline greeted Melanie and mentioned that a lot has been going on since they last talked."; created_at: 2026-11-10T22:36:01.798592+00:00; not retrieved

## Top 5 retrieved memories
- rank 1: "Caroline participated in a school event around November 3, 2026, where she talked about her transgender journey and encouraged students to get involved in the LGBTQ community, reflecting on her progress since starting her transition three years ago."; created_at: 2026-11-10T22:34:00.906146+00:00; combined 0.8193, semantic 0.6392, bm25 0.9994, entity_boost 0.0000
- rank 2: "Caroline attended a poetry reading on November 3, 2026, which she found powerful and impactful."; created_at: 2026-11-10T22:46:53.194351+00:00; combined 0.3070, semantic 0.5678, bm25 0.0462, entity_boost 0.0000
- rank 3: "Caroline attended a pride parade on November 3, 2026, which inspired her with its energy and love, reminding her of the importance of standing up for equality."; created_at: 2026-11-10T22:41:12.951027+00:00; combined 0.3019, semantic 0.5579, bm25 0.0459, entity_boost 0.0000
- rank 4: "Caroline attended a pride parade on November 3, 2026, where she felt a lot of energy and love, making her proud and reminding her of the importance of standing up for equality."; created_at: 2026-11-10T22:41:03.613258+00:00; combined 0.2978, semantic 0.5498, bm25 0.0457, entity_boost 0.0000
- rank 5: "Caroline attended a poetry reading on November 3, 2026, and found it to be a powerful experience."; created_at: 2026-11-10T22:46:49.156400+00:00; combined 0.2975, semantic 0.5488, bm25 0.0462, entity_boost 0.0000

## Cutoff results
- top_10: judgment=WRONG; generated_answer="Around November 3, 2026."; reason="The generated date (around November 3, 2026) does not match the gold timeframe (the week before June 9, 2023) and is far outside the allowed tolerance."
- top_20: judgment=WRONG; generated_answer="Around November 3, 2026."; reason="The generated date (around November 3, 2026) is entirely different from the gold answer (the week before June 9, 2023) and outside any tolerance window."
- top_50: judgment=WRONG; generated_answer="Around November 3, 2026."; reason="The generated date (November 2026) is entirely different from the gold timeframe (the week before 9 June 2023) and not within the allowed tolerance."
- top_200: judgment=WRONG; generated_answer="Around November 3, 2026."; reason="The generated date (Nov 3, 2026) does not match the gold timeframe (the week before June 9, 2023) and contains no overlapping correct item."
