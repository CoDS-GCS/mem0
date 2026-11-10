# conv0_q45

- Question: When did Caroline attend a pride parade in August?
- Category: temporal
- Gold answer: The Friday before 14 August 2023
- Reference date: 9:55 am on 22 October, 2023

## Evidence turns
- D11:4 (session 11, 2:24 pm on 14 August, 2023), Caroline: "Wow, Mel, glad you had a blast at the concert. A lot's happened since we talked. I went to a pride parade last Friday and it was awesome - so much energy and love everywhere. Really made me proud and reminded me how important it is to keep standing up for equality."

## Stored memory candidates
Candidates by word overlap; whether the needed memory was stored is for the analyst to decide.

### candidates for D11:4
- overlap 0.26; memory: "Caroline attended a pride parade on November 3, 2026, where she felt a lot of energy and love, making her proud and reminding her of the importance of standing up for equality."; created_at: 2026-11-10T14:59:00.549712+00:00; rank 3, combined 0.8709, semantic 0.8203, bm25 0.9999, entity_boost 0.3571
- overlap 0.26; memory: "Caroline attended a pride parade on November 3, 2026, and felt a strong sense of energy and love, which reminded her of the importance of standing up for equality."; created_at: 2026-11-10T14:59:04.100538+00:00; rank 5, combined 0.8627, semantic 0.7997, bm25 0.9999, entity_boost 0.3571
- overlap 0.19; memory: "Caroline's city held a pride parade last weekend around November 5-6, 2026, where many people marched through the streets waving flags and holding signs to celebrate love and diversity. Although she missed it, it served as a powerful reminder of the ongoing fight for equality and inclusivity."; created_at: 2026-11-10T14:57:52.061454+00:00; rank 10, combined 0.8504, semantic 0.7774, bm25 0.9914, entity_boost 0.3571

## Top 5 retrieved memories
- rank 1: "Caroline attended a pride parade a few weeks ago around late October 2026 and shared a photo of the event featuring a rainbow flag and people walking down the street."; created_at: 2026-11-10T14:55:56.965119+00:00; combined 0.8786, semantic 0.8395, bm25 0.9999, entity_boost 0.3571
- rank 2: "Caroline attended a pride parade on November 4, 2026, and felt inspired by the energy and love, reinforcing her commitment to fighting for LGBTQ rights."; created_at: 2026-11-10T14:59:10.700984+00:00; combined 0.8711, semantic 0.8207, bm25 0.9999, entity_boost 0.3571
- rank 3: "Caroline attended a pride parade on November 3, 2026, where she felt a lot of energy and love, making her proud and reminding her of the importance of standing up for equality."; created_at: 2026-11-10T14:59:00.549712+00:00; combined 0.8709, semantic 0.8203, bm25 0.9999, entity_boost 0.3571
- rank 4: "Caroline attended an LGBTQ+ pride parade around November 3-4, 2026, where she felt a sense of belonging and was amazed by the happiness of the community and its growth."; created_at: 2026-11-10T14:52:02.315924+00:00; combined 0.8645, semantic 0.8081, bm25 0.9999, entity_boost 0.3534
- rank 5: "Caroline attended a pride parade on November 3, 2026, and felt a strong sense of energy and love, which reminded her of the importance of standing up for equality."; created_at: 2026-11-10T14:59:04.100538+00:00; combined 0.8627, semantic 0.7997, bm25 0.9999, entity_boost 0.3571

## Cutoff results
- top_10: judgment=WRONG; generated_answer="She didn’t attend one in August. Her recorded attendances were in late October 2026 and early November 2026 (specifically Nov 3–4, 2026)."; reason="The generated answer denies any August attendance and gives unrelated October–November 2026 dates, sharing no correct item with the gold answer."
- top_20: judgment=WRONG; generated_answer="Around November 3–4, 2026."; reason="The generated date (around November 3–4, 2026) does not match or approximate the gold date (the Friday before August 14, 2023)."
- top_50: judgment=WRONG; generated_answer="She didn’t attend a pride parade in August; her documented parade attendance was in early November (Nov 3–4)."; reason="The generated answer contradicts the gold answer by denying an August parade and giving November dates, with no overlap with 'the Friday before 14 August 2023.'"
- top_200: judgment=WRONG; generated_answer="There’s no recorded August pride parade attendance for Caroline. Her documented pride parades were in late October and on November 3–4."; reason="The generated answer denies any August pride parade and instead cites October/November dates, containing none of the gold information about “the Friday before 14 August 2023.”"
