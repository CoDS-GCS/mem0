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
- overlap 0.33; memory: "Caroline attended an LGBTQ+ pride parade last week, which made her feel a sense of belonging and showcased the growth of the community."; created_at: 2026-11-10T22:35:39.670580+00:00; rank 20, combined 0.8513, semantic 0.7084, bm25 0.9943, entity_boost 0.0000
- overlap 0.25; memory: "Caroline attended an LGBTQ+ pride parade last week, feeling a sense of belonging and witnessing the growth of the community."; created_at: 2026-11-10T22:35:53.041413+00:00; rank 19, combined 0.8538, semantic 0.7135, bm25 0.9940, entity_boost 0.0000
- overlap 0.21; memory: "Caroline felt proud and grateful at the LGBTQ+ pride parade she attended around November 3-6, 2026, appreciating the amazing vibes and the comforting presence of a supportive community."; created_at: 2026-11-10T22:38:38.543956+00:00; rank 18, combined 0.8574, semantic 0.7218, bm25 0.9931, entity_boost 0.0000

## Top 5 retrieved memories
- rank 1: "Caroline attended a pride parade a few weeks ago around late October 2026 and shared a photo of the event featuring a rainbow flag and people walking down the street."; created_at: 2026-11-10T22:38:30.606774+00:00; combined 0.9035, semantic 0.8140, bm25 0.9931, entity_boost 0.0000
- rank 2: "Caroline attended a pride parade on November 3, 2026, where she felt a lot of energy and love, making her proud and reminding her of the importance of standing up for equality."; created_at: 2026-11-10T22:41:03.613258+00:00; combined 0.8929, semantic 0.7927, bm25 0.9931, entity_boost 0.0000
- rank 3: "Caroline attended a pride parade on November 3, 2026, which inspired her with its energy and love, reminding her of the importance of standing up for equality."; created_at: 2026-11-10T22:41:12.951027+00:00; combined 0.8926, semantic 0.7915, bm25 0.9937, entity_boost 0.0000
- rank 4: "Caroline attended a pride parade on November 3, 2026, which was filled with energy and love, inspiring her to continue advocating for LGBTQ rights."; created_at: 2026-11-10T22:41:27.794215+00:00; combined 0.8903, semantic 0.7871, bm25 0.9936, entity_boost 0.0000
- rank 5: "Caroline attended a pride parade on November 3, 2026, feeling inspired by the crowd celebrating love and acceptance, which motivated her to continue fighting for LGBTQ rights."; created_at: 2026-11-10T22:41:09.517757+00:00; combined 0.8868, semantic 0.7806, bm25 0.9929, entity_boost 0.0000

## Cutoff results
- top_10: judgment=WRONG; generated_answer="She didn’t attend one during the summer; she went to a pride parade on November 3, 2026 (early November)."; reason="The generated answer contradicts the gold timing by denying a summer parade and giving a November 2026 date instead of the week before July 3, 2023."
- top_20: judgment=WRONG; generated_answer="She didn’t go during the summer in these memories. Her attendance is recorded on November 3, 2026 (with other mentions placing it in late October/early November 2026)."; reason="It denies a summer parade and instead places the event in late 2026, not the week before 3 July 2023."
- top_50: judgment=WRONG; generated_answer="November 3."; reason="The generated date (November 3) does not match the gold timeframe (the week before July 3, 2023) and is far outside the 14-day tolerance."
- top_200: judgment=WRONG; generated_answer="Last year (at the Pride festival)."; reason="The generated answer only says “last year” and does not specify the week before 3 July 2023, so it fails to include the gold answer’s specific timeframe."
