# conv0_q17

- Question: When is Caroline going to the transgender conference?
- Category: temporal
- Gold answer: July 2023
- Reference date: 9:55 am on 22 October, 2023

## Evidence turns
- D5:13 (session 5, 1:36 pm on 3 July, 2023), Caroline: "Thanks Mel! I'm going to a transgender conference this month. I'm so excited to meet other people in the community and learn more about advocacy. It's gonna be great!"

## Stored memory candidates
Candidates by word overlap; whether the needed memory was stored is for the analyst to decide.

### candidates for D5:13
- overlap 0.42; memory: "Caroline is attending a transgender conference in November 2026, where she is excited to meet others in the community and learn more about advocacy."; created_at: 2026-11-10T22:35:57.891761+00:00; rank 1, combined 0.9160, semantic 0.8322, bm25 0.9998, entity_boost 0.0000
- overlap 0.42; memory: "Caroline is excited to attend a transgender conference in November 2026 to meet others in the community and learn more about advocacy."; created_at: 2026-11-10T22:36:03.700070+00:00; rank 2, combined 0.9086, semantic 0.8174, bm25 0.9998, entity_boost 0.0000
- overlap 0.26; memory: "Melanie believes that volunteering is a great way to meet people and emphasizes the importance of creating community and supporting each other, especially for kids."; created_at: 2026-11-10T22:44:31.969851+00:00; not retrieved

## Top 5 retrieved memories
- rank 1: "Caroline is attending a transgender conference in November 2026, where she is excited to meet others in the community and learn more about advocacy."; created_at: 2026-11-10T22:35:57.891761+00:00; combined 0.9160, semantic 0.8322, bm25 0.9998, entity_boost 0.0000
- rank 2: "Caroline is excited to attend a transgender conference in November 2026 to meet others in the community and learn more about advocacy."; created_at: 2026-11-10T22:36:03.700070+00:00; combined 0.9086, semantic 0.8174, bm25 0.9998, entity_boost 0.0000
- rank 3: "Caroline attended an LGBTQ conference around November 8, 2026, where she connected with people who have gone through similar journeys and felt welcomed in the environment."; created_at: 2026-11-10T22:37:04.340347+00:00; combined 0.8593, semantic 0.7188, bm25 0.9999, entity_boost 0.0000
- rank 4: "Caroline attended an LGBTQ conference on November 8, 2026, where she connected with people who have gone through similar journeys and felt a strong sense of acceptance in a welcoming environment."; created_at: 2026-11-10T22:36:52.690501+00:00; combined 0.8568, semantic 0.7138, bm25 0.9999, entity_boost 0.0000
- rank 5: "Caroline attended an LGBTQ conference on November 8, 2026, where she connected with people who have gone through similar journeys and felt it was a welcoming environment."; created_at: 2026-11-10T22:37:09.684112+00:00; combined 0.8535, semantic 0.7070, bm25 0.9999, entity_boost 0.0000

## Cutoff results
- top_10: judgment=WRONG; generated_answer="November 2026."; reason="The generated date 'November 2026' does not match the gold answer 'July 2023' and is far outside the tolerance window."
- top_20: judgment=WRONG; generated_answer="In November 2026."; reason="The generated date 'November 2026' does not match the gold date 'July 2023' and is far outside the allowed tolerance, so it contains no correct item."
- top_50: judgment=WRONG; generated_answer="November 2026"; reason="The generated date (November 2026) does not match or fall within the allowed tolerance of the gold date (July 2023), so there is no overlap."
- top_200: judgment=WRONG; generated_answer="November 2026."; reason="The generated date of November 2026 does not match the gold answer of July 2023 and is far outside the 14-day tolerance window, providing no correct overlap."
