# conv0_q25

- Question: When did Caroline go to the LGBTQ conference?
- Category: temporal
- Gold answer: 10 July 2023
- Reference date: 9:55 am on 22 October, 2023

## Evidence turns
- D7:1 (session 7, 4:33 pm on 12 July, 2023), Caroline: "Hey Mel, great to chat with you again! So much has happened since we last spoke - I went to an LGBTQ conference two days ago and it was really special. I got the chance to meet and connect with people who've gone through similar journeys. It was such a welcoming environment and I felt totally accepted. I'm really thankful for this amazing community - it's shown me how important it is to fight for trans rights and spread awareness."

## Stored memory candidates
Candidates by word overlap; whether the needed memory was stored is for the analyst to decide.

### candidates for D7:1
- overlap 0.23; memory: "Caroline attended an LGBTQ conference on November 8, 2026, where she met and connected with people who have gone through similar journeys, feeling totally accepted in a welcoming environment."; created_at: 2026-11-10T14:53:46.381614+00:00; rank 3, combined 0.9283, semantic 0.8330, bm25 1.0000, entity_boost 0.4878
- overlap 0.23; memory: "Caroline attended an LGBTQ conference two days prior to November 10, 2026, where she felt welcomed and connected with people who have gone through similar journeys, emphasizing the importance of community support during her transition."; created_at: 2026-11-10T14:53:48.313576+00:00; rank 6, combined 0.9140, semantic 0.7971, bm25 1.0000, entity_boost 0.4878
- overlap 0.23; memory: "Caroline attended an LGBTQ conference two days prior to November 10, 2026, where she connected with people who have gone through similar journeys and felt welcomed in the environment."; created_at: 2026-11-10T14:54:08.745081+00:00; rank 5, combined 0.9226, semantic 0.8187, bm25 1.0000, entity_boost 0.4878

## Top 5 retrieved memories
- rank 1: "Caroline attended an LGBTQ conference on November 8, 2026, where she connected with people who have gone through similar journeys and felt welcomed in the environment."; created_at: 2026-11-10T14:54:00.190557+00:00; combined 0.9310, semantic 0.8398, bm25 1.0000, entity_boost 0.4878
- rank 2: "Caroline attended an LGBTQ conference on November 8, 2026, where she connected with people who have gone through similar journeys and felt it was a welcoming environment."; created_at: 2026-11-10T14:54:15.349014+00:00; combined 0.9295, semantic 0.8359, bm25 1.0000, entity_boost 0.4878
- rank 3: "Caroline attended an LGBTQ conference on November 8, 2026, where she met and connected with people who have gone through similar journeys, feeling totally accepted in a welcoming environment."; created_at: 2026-11-10T14:53:46.381614+00:00; combined 0.9283, semantic 0.8330, bm25 1.0000, entity_boost 0.4878
- rank 4: "Caroline attended an LGBTQ conference on November 8, 2026, where she connected with people who have gone through similar journeys and felt welcomed."; created_at: 2026-11-10T14:53:54.404369+00:00; combined 0.9267, semantic 0.8289, bm25 1.0000, entity_boost 0.4878
- rank 5: "Caroline attended an LGBTQ conference two days prior to November 10, 2026, where she connected with people who have gone through similar journeys and felt welcomed in the environment."; created_at: 2026-11-10T14:54:08.745081+00:00; combined 0.9226, semantic 0.8187, bm25 1.0000, entity_boost 0.4878

## Cutoff results
- top_10: judgment=WRONG; generated_answer="November 8, 2026."; reason="The generated date (November 8, 2026) does not match the gold date (July 10, 2023) and is far outside the 14-day tolerance."
- top_20: judgment=WRONG; generated_answer="November 8, 2026."; reason="The generated date (November 8, 2026) does not match or fall within the tolerance of the gold date (10 July 2023), providing no correct item."
- top_50: judgment=WRONG; generated_answer="November 8, 2026."; reason="The generated date (November 8, 2026) does not match the gold date (10 July 2023) or fall within the tolerance window, providing no correct items."
- top_200: judgment=WRONG; generated_answer="November 8, 2026."; reason="The generated date (November 8, 2026) does not match the gold date (10 July 2023) and is far outside the 14-day tolerance window."
