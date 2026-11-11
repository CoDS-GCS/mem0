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
- overlap 0.26; memory: "Caroline attended a pride parade on November 3, 2026, where she felt a lot of energy and love, making her proud and reminding her of the importance of standing up for equality."; created_at: 2026-11-10T22:41:03.613258+00:00; rank 2, combined 0.9101, semantic 0.8203, bm25 0.9999, entity_boost 0.0000
- overlap 0.26; memory: "Caroline attended a pride parade on November 3, 2026, and felt a strong sense of energy and love, which reminded her of the importance of standing up for equality."; created_at: 2026-11-10T22:41:06.593452+00:00; rank 8, combined 0.8998, semantic 0.7997, bm25 0.9999, entity_boost 0.0000
- overlap 0.22; memory: "Caroline attended a pride parade on November 3, 2026, which inspired her with its energy and love, reminding her of the importance of standing up for equality."; created_at: 2026-11-10T22:41:12.951027+00:00; rank 4, combined 0.9082, semantic 0.8164, bm25 0.9999, entity_boost 0.0000

## Top 5 retrieved memories
- rank 1: "Caroline attended a pride parade a few weeks ago around late October 2026 and shared a photo of the event featuring a rainbow flag and people walking down the street."; created_at: 2026-11-10T22:38:30.606774+00:00; combined 0.9197, semantic 0.8395, bm25 0.9999, entity_boost 0.0000
- rank 2: "Caroline attended a pride parade on November 3, 2026, where she felt a lot of energy and love, making her proud and reminding her of the importance of standing up for equality."; created_at: 2026-11-10T22:41:03.613258+00:00; combined 0.9101, semantic 0.8203, bm25 0.9999, entity_boost 0.0000
- rank 3: "Caroline attended a pride parade on November 3, 2026, which was filled with energy and love, inspiring her to continue advocating for LGBTQ rights."; created_at: 2026-11-10T22:41:27.794215+00:00; combined 0.9093, semantic 0.8187, bm25 0.9999, entity_boost 0.0000
- rank 4: "Caroline attended a pride parade on November 3, 2026, which inspired her with its energy and love, reminding her of the importance of standing up for equality."; created_at: 2026-11-10T22:41:12.951027+00:00; combined 0.9082, semantic 0.8164, bm25 0.9999, entity_boost 0.0000
- rank 5: "Caroline attended a pride parade on November 3, 2026, feeling inspired by the crowd celebrating love and acceptance, which motivated her to continue fighting for LGBTQ rights."; created_at: 2026-11-10T22:41:09.517757+00:00; combined 0.9079, semantic 0.8160, bm25 0.9999, entity_boost 0.0000

## Cutoff results
- top_10: judgment=WRONG; generated_answer="She didn’t attend one in August; she attended the pride parade on November 3."; reason="The generated answer contradicts the gold answer by denying an August parade and giving a different date (November 3), matching none of the gold details."
- top_20: judgment=WRONG; generated_answer="She didn’t attend a pride parade in August. Her documented attendance was on November 3, 2026 (some notes also place it in late October 2026)."; reason="The generated answer contradicts the gold date and provides no matching item from the gold answer."
- top_50: judgment=WRONG; generated_answer="She didn’t attend one in August; the documented pride parade she attended was on November 3."; reason="The generated answer denies an August parade and cites November 3, which does not match the gold date of the Friday before 14 August 2023."
- top_200: judgment=WRONG; generated_answer="She didn’t attend one in August. The memories show her attending pride parades in late October and on November 3."; reason="The answer denies any August attendance and cites October/November dates, which do not match the gold date of the Friday before 14 August 2023, so there is no overlap."
