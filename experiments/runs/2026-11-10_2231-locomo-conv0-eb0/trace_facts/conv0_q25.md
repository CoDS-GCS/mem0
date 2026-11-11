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
- overlap 0.21; memory: "Caroline attended an LGBTQ conference on November 8, 2026, where she connected with people who have gone through similar journeys and felt a strong sense of acceptance in a welcoming environment."; created_at: 2026-11-10T22:36:52.690501+00:00; rank 3, combined 0.9177, semantic 0.8355, bm25 1.0000, entity_boost 0.0000
- overlap 0.21; memory: "Caroline attended an LGBTQ conference two days prior to November 10, 2026, where she connected with people who have gone through similar journeys and felt welcomed."; created_at: 2026-11-10T22:36:58.006037+00:00; rank 6, combined 0.9079, semantic 0.8158, bm25 1.0000, entity_boost 0.0000
- overlap 0.21; memory: "Caroline attended an LGBTQ conference on November 8, 2026, where she connected with people who have gone through similar journeys and felt it was a welcoming environment."; created_at: 2026-11-10T22:37:09.684112+00:00; rank 2, combined 0.9179, semantic 0.8359, bm25 1.0000, entity_boost 0.0000

## Top 5 retrieved memories
- rank 1: "Caroline attended an LGBTQ conference around November 8, 2026, where she connected with people who have gone through similar journeys and felt welcomed in the environment."; created_at: 2026-11-10T22:37:04.340347+00:00; combined 0.9219, semantic 0.8439, bm25 1.0000, entity_boost 0.0000
- rank 2: "Caroline attended an LGBTQ conference on November 8, 2026, where she connected with people who have gone through similar journeys and felt it was a welcoming environment."; created_at: 2026-11-10T22:37:09.684112+00:00; combined 0.9179, semantic 0.8359, bm25 1.0000, entity_boost 0.0000
- rank 3: "Caroline attended an LGBTQ conference on November 8, 2026, where she connected with people who have gone through similar journeys and felt a strong sense of acceptance in a welcoming environment."; created_at: 2026-11-10T22:36:52.690501+00:00; combined 0.9177, semantic 0.8355, bm25 1.0000, entity_boost 0.0000
- rank 4: "Caroline attended an LGBTQ conference on November 8, 2026, where she felt welcomed and accepted, and had the opportunity to connect with others who have gone through similar journeys."; created_at: 2026-11-10T22:36:41.791631+00:00; combined 0.9108, semantic 0.8216, bm25 1.0000, entity_boost 0.0000
- rank 5: "Caroline attended an LGBTQ conference on November 8, 2026, where she felt welcomed and connected with people who have gone through similar journeys."; created_at: 2026-11-10T22:36:46.849443+00:00; combined 0.9096, semantic 0.8193, bm25 1.0000, entity_boost 0.0000

## Cutoff results
- top_10: judgment=WRONG; generated_answer="November 8, 2026."; reason="The generated date (November 8, 2026) does not match the gold date (10 July 2023) and is far outside the allowed tolerance, with no overlapping correct item."
- top_20: judgment=WRONG; generated_answer="November 8."; reason="The generated date 'November 8' does not match the gold date '10 July 2023' and is not within the allowed tolerance window."
- top_50: judgment=WRONG; generated_answer="November 8, 2026."; reason="The generated date (November 8, 2026) does not match the gold date (10 July 2023) and is far outside the allowed tolerance."
- top_200: judgment=WRONG; generated_answer="November 8"; reason="The generated date 'November 8' does not match the gold date '10 July 2023' nor fall within the 14-day tolerance window."
