# conv0_q20

- Question: When did Melanie go to the museum?
- Category: temporal
- Gold answer: 5 July 2023
- Reference date: 9:55 am on 22 October, 2023

## Evidence turns
- D6:4 (session 6, 8:18 pm on 6 July, 2023), Melanie: "That's awesome, Caroline! Congrats on following your dreams. Yesterday I took the kids to the museum - it was so cool spending time with them and seeing their eyes light up!"

## Stored memory candidates
Candidates by word overlap; whether the needed memory was stored is for the analyst to decide.

### candidates for D6:4
- overlap 0.38; memory: "Melanie took her kids to the museum on November 9, 2026, and enjoyed spending time with them while seeing their excitement at the exhibits."; created_at: 2026-11-10T22:36:08.324037+00:00; rank 1, combined 0.8638, semantic 0.7280, bm25 0.9997, entity_boost 0.0000
- overlap 0.25; memory: "Caroline complimented Melanie on a picture of her kids at the museum, expressing that it must have been an awesome experience and asking what excited them."; created_at: 2026-11-10T22:36:10.151597+00:00; rank 4, combined 0.7999, semantic 0.6001, bm25 0.9997, entity_boost 0.0000
- overlap 0.19; memory: "Caroline praised Melanie for doing an awesome job looking after herself and her family, emphasizing the importance of taking time for oneself."; created_at: 2026-11-10T22:33:34.057035+00:00; not retrieved

## Top 5 retrieved memories
- rank 1: "Melanie took her kids to the museum on November 9, 2026, and enjoyed spending time with them while seeing their excitement at the exhibits."; created_at: 2026-11-10T22:36:08.324037+00:00; combined 0.8638, semantic 0.7280, bm25 0.9997, entity_boost 0.0000
- rank 2: "Melanie took her kids to the museum on November 9, 2026, where they enjoyed the dinosaur exhibit, which excited them and reminded her why she loves being a mom."; created_at: 2026-11-10T22:36:24.109177+00:00; combined 0.8427, semantic 0.6857, bm25 0.9997, entity_boost 0.0000
- rank 3: "Melanie's kids were excited about the dinosaur exhibit at the museum, showing a keen interest in learning about animals and finding the dinosaur bones fascinating."; created_at: 2026-11-10T22:36:11.995698+00:00; combined 0.8225, semantic 0.6453, bm25 0.9997, entity_boost 0.0000
- rank 4: "Caroline complimented Melanie on a picture of her kids at the museum, expressing that it must have been an awesome experience and asking what excited them."; created_at: 2026-11-10T22:36:10.151597+00:00; combined 0.7999, semantic 0.6001, bm25 0.9997, entity_boost 0.0000
- rank 5: "Melanie shared an image of her kids laughing at a dinosaur exhibit in the museum, showcasing their joy during the visit."; created_at: 2026-11-10T22:36:08.326972+00:00; combined 0.7980, semantic 0.5964, bm25 0.9997, entity_boost 0.0000

## Cutoff results
- top_10: judgment=WRONG; generated_answer="November 9, 2026."; reason="The generated date (November 9, 2026) does not match the gold date (5 July 2023) and is far outside the allowed tolerance, so there is no overlap."
- top_20: judgment=WRONG; generated_answer="November 9, 2026."; reason="The generated date (November 9, 2026) does not match the gold date (July 5, 2023) and is far outside the allowed tolerance window."
- top_50: judgment=WRONG; generated_answer="November 9, 2026."; reason="The generated date (November 9, 2026) does not match the gold date (5 July 2023) and is far outside the 14-day tolerance."
- top_200: judgment=WRONG; generated_answer="November 9, 2026."; reason="The generated date (November 9, 2026) does not match the gold date (5 July 2023) and is far outside the 14-day tolerance, so no correct items are present."
