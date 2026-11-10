# conv0_q63

- Question: When is Caroline's youth center putting on a talent show?
- Category: temporal
- Gold answer: September 2023
- Reference date: 9:55 am on 22 October, 2023

## Evidence turns
- D15:11 (session 15, 3:19 pm on 28 August, 2023), Caroline: "We're putting together a talent show for the kids next month. I'm looking forward to seeing how much fun everyone has and how proud they'll feel of their talents!"

## Stored memory candidates
Candidates by word overlap; whether the needed memory was stored is for the analyst to decide.

### candidates for D15:11
- overlap 0.79; memory: "Caroline is putting together a talent show for the kids next month, expressing excitement about seeing how much fun everyone will have and how proud they'll feel of their talents."; created_at: 2026-11-10T15:03:29.965116+00:00; rank 4, combined 0.6872, semantic 0.7163, bm25 1.0000, entity_boost 0.0017
- overlap 0.58; memory: "Caroline is looking forward to putting together a talent show for the kids at the youth center next month, excited to see their fun and pride in showcasing their talents."; created_at: 2026-11-10T15:03:51.281117+00:00; rank 2, combined 0.7142, semantic 0.7838, bm25 1.0000, entity_boost 0.0017
- overlap 0.53; memory: "Caroline is helping to organize a talent show for the kids at the youth center next month, looking forward to the fun and pride the kids will feel in showcasing their talents."; created_at: 2026-11-10T15:03:38.107179+00:00; rank 1, combined 0.7207, semantic 0.8000, bm25 1.0000, entity_boost 0.0017

## Top 5 retrieved memories
- rank 1: "Caroline is helping to organize a talent show for the kids at the youth center next month, looking forward to the fun and pride the kids will feel in showcasing their talents."; created_at: 2026-11-10T15:03:38.107179+00:00; combined 0.7207, semantic 0.8000, bm25 1.0000, entity_boost 0.0017
- rank 2: "Caroline is looking forward to putting together a talent show for the kids at the youth center next month, excited to see their fun and pride in showcasing their talents."; created_at: 2026-11-10T15:03:51.281117+00:00; combined 0.7142, semantic 0.7838, bm25 1.0000, entity_boost 0.0017
- rank 3: "Caroline is looking forward to organizing a talent show for the kids at the youth center next month, excited to see their enjoyment and pride in showcasing their talents."; created_at: 2026-11-10T15:03:42.449468+00:00; combined 0.7139, semantic 0.7830, bm25 1.0000, entity_boost 0.0017
- rank 4: "Caroline is putting together a talent show for the kids next month, expressing excitement about seeing how much fun everyone will have and how proud they'll feel of their talents."; created_at: 2026-11-10T15:03:29.965116+00:00; combined 0.6872, semantic 0.7163, bm25 1.0000, entity_boost 0.0017
- rank 5: "Caroline is looking forward to a talent show for the kids at the LGBTQ+ youth center next month, excited about the fun and pride it will bring to everyone involved."; created_at: 2026-11-10T15:03:35.117093+00:00; combined 0.6827, semantic 0.7051, bm25 1.0000, entity_boost 0.0017

## Cutoff results
- top_10: judgment=WRONG; generated_answer="Next month—December."; reason="The generated answer says December, which does not match the gold answer of September 2023 and has no overlapping correct item."
- top_20: judgment=WRONG; generated_answer="Next month — in December."; reason="The generated answer says December, which does not match the gold answer of September 2023 and is not within the date tolerance."
- top_50: judgment=WRONG; generated_answer="Next month—in December."; reason="The generated answer says December, which does not match the gold date of September 2023 and is not within the 14-day tolerance."
- top_200: judgment=WRONG; generated_answer="December 2026"; reason="The generated date of December 2026 does not match the gold answer of September 2023 and is far outside the allowed tolerance, containing no correct items."
