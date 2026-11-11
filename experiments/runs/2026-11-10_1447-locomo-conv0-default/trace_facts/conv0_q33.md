# conv0_q33

- Question: When did Caroline go to a pride parade during the summer?
- Category: temporal
- Gold answer: The week before 3 July 2023
- Reference date: 9:55 am on 22 October, 2023

## Evidence turns
- D5:1 (session 5, 1:36 pm on 3 July, 2023), Caroline: "Since we last spoke, some big things have happened. Last week I went to an LGBTQ+ pride parade. Everyone was so happy and it made me feel like I belonged. It showed me how much our community has grown, it was amazing!"

## Stored memory candidates
Candidates by word overlap; whether the needed memory was stored is for the analyst to decide.

### candidates for D5:1
- overlap 0.33; memory: "Caroline attended an LGBTQ+ pride parade last week, which made her feel a sense of belonging and showcased the growth of the community."; created_at: 2026-11-10T14:52:15.608724+00:00; rank 16, combined 0.8225, semantic 0.7084, bm25 0.9945, entity_boost 0.3534
- overlap 0.25; memory: "Caroline attended an LGBTQ+ pride parade around November 3, 2026, which made her feel a sense of belonging and showcased the growth of the community."; created_at: 2026-11-10T14:52:21.853021+00:00; rank 10, combined 0.8404, semantic 0.7534, bm25 0.9942, entity_boost 0.3534
- overlap 0.21; memory: "Caroline felt proud and grateful during the LGBTQ+ pride parade around November 3-4, 2026, appreciating the amazing vibes and the comforting presence of a supportive community around her."; created_at: 2026-11-10T14:56:06.691824+00:00; rank 15, combined 0.8238, semantic 0.7126, bm25 0.9935, entity_boost 0.3534

## Top 5 retrieved memories
- rank 1: "Caroline attended a pride parade a few weeks ago around late October 2026 and shared a photo of the event featuring a rainbow flag and people walking down the street."; created_at: 2026-11-10T14:55:56.965119+00:00; combined 0.8658, semantic 0.8140, bm25 0.9933, entity_boost 0.3571
- rank 2: "Caroline attended a pride parade on November 3, 2026, where she felt a lot of energy and love, making her proud and reminding her of the importance of standing up for equality."; created_at: 2026-11-10T14:59:00.549712+00:00; combined 0.8573, semantic 0.7927, bm25 0.9933, entity_boost 0.3571
- rank 3: "Caroline attended a pride parade on November 4, 2026, and felt inspired by the energy and love, reinforcing her commitment to fighting for LGBTQ rights."; created_at: 2026-11-10T14:59:10.700984+00:00; combined 0.8518, semantic 0.7788, bm25 0.9936, entity_boost 0.3571
- rank 4: "Caroline attended a pride parade a few weeks ago and shared it as a special memory."; created_at: 2026-11-10T14:55:59.988735+00:00; combined 0.8514, semantic 0.7765, bm25 0.9949, entity_boost 0.3571
- rank 5: "Caroline attended a pride parade on November 3, 2026, and felt a strong sense of energy and love, which reminded her of the importance of standing up for equality."; created_at: 2026-11-10T14:59:04.100538+00:00; combined 0.8478, semantic 0.7685, bm25 0.9938, entity_boost 0.3571

## Cutoff results
- top_10: judgment=WRONG; generated_answer="She didn’t go during the summer—she went in early November (around November 3–4)."; reason="The generated answer places the event in early November, which does not match the gold answer’s timing of the week before July 3, 2023, and includes no overlapping correct detail."
- top_20: judgment=WRONG; generated_answer="She didn’t go to a pride parade during the summer. Her recorded attendance was in the fall—late October 2026 and specifically on November 3–4, 2026."; reason="The generated answer contradicts the gold answer by denying a summer event and giving unrelated 2026 fall dates, sharing no correct items."
- top_50: judgment=WRONG; generated_answer="Last year, during the summer Pride festival with her friend Melanie."; reason="The generated answer gives only “last year” and lacks the specific timing of the gold answer (“the week before 3 July 2023”), so it does not match the required date window."
- top_200: judgment=CORRECT; generated_answer="Last summer — at last year’s Pride festival."; reason="The generated answer places the event in last summer at Pride, which semantically aligns with late June 2023 (the week before July 3, 2023)."
