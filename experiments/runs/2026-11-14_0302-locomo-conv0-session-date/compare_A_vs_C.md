# Comparison: 2026-11-10_1447-locomo-conv0-default (A) vs 2026-11-14_0302-locomo-conv0-session-date (B)

- A: `experiments/runs/2026-11-10_1447-locomo-conv0-default`
- B: `experiments/runs/2026-11-14_0302-locomo-conv0-session-date`

## 1. J

J = % of questions the judge model labelled CORRECT.

| cutoff | J_A (%) | J_B (%) | diff (pts, B-A) | correct_A/total | correct_B/total | diff (questions, B-A) |
|---|---|---|---|---|---|---|
| top_10 | 67.1 | 80.3 | +13.2 | 102/152 | 122/152 | +20 |
| top_20 | 69.1 | 80.3 | +11.2 | 105/152 | 122/152 | +17 |
| top_50 | 71.7 | 84.2 | +12.5 | 109/152 | 128/152 | +19 |
| top_200 | 71.7 | 85.5 | +13.8 | 109/152 | 130/152 | +21 |

Per-category at top_200:

| category | correct_A/total | correct_B/total | diff (questions, B-A) |
|---|---|---|---|
| multi-hop | 27/32 | 27/32 | +0 |
| open-domain | 13/13 | 13/13 | +0 |
| single-hop | 63/70 | 54/70 | -9 |
| temporal | 6/37 | 36/37 | +30 |

## 2. Flips at top_200 (match by question_id)

- Correct in A, wrong in B: 11
  - multi-hop: 1
  - single-hop: 9
  - temporal: 1
- Wrong in A, correct in B: 32
  - multi-hop: 1
  - temporal: 31

| question_id | category | question | gold answer | A's answer (top_200) | B's answer (top_200) | trace (A) | trace (B) |
|---|---|---|---|---|---|---|---|
| conv0_q0 | temporal | When did Caroline go to the LGBTQ support group? | 7 May 2023 | November 9, 2026. | May 7, 2023. | [2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q0.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q0.md) | [2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q0.md](../2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q0.md) |
| conv0_q5 | temporal | When did Melanie run a charity race? | The sunday before 25 May 2023 | November 5, 2026. | May 20, 2023. | [2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q5.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q5.md) | [2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q5.md](../2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q5.md) |
| conv0_q6 | temporal | When is Melanie planning on going camping? | June 2023 | Next month, during her kids’ summer break. | June 2023. | [2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q6.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q6.md) | [2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q6.md](../2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q6.md) |
| conv0_q8 | temporal | When did Caroline give a speech at a school? | The week before 9 June 2023 | Around November 3, 2026. | Around June 2, 2023. | [2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q8.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q8.md) | [2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q8.md](../2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q8.md) |
| conv0_q9 | temporal | When did Caroline meet up with her friends, family, and mentors? | The week before 9 June 2023 | Last week (the week before November 10, 2026). | The week before June 9, 2023 (i.e., the previous week in early June 2023). | [2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q9.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q9.md) | [2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q9.md](../2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q9.md) |
| conv0_q16 | temporal | When did Melanie sign up for a pottery class? | 2 July 2023 | November 10, 2026. | July 2, 2023. | [2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q16.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q16.md) | [2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q16.md](../2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q16.md) |
| conv0_q17 | temporal | When is Caroline going to the transgender conference? | July 2023 | November 2026. | July 2023. | [2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q17.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q17.md) | [2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q17.md](../2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q17.md) |
| conv0_q20 | temporal | When did Melanie go to the museum? | 5 July 2023 | November 9, 2026. | July 5, 2023. | [2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q20.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q20.md) | [2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q20.md](../2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q20.md) |
| conv0_q21 | temporal | When did Caroline have a picnic? | The week before 6 July 2023 | Last week (she had a picnic with friends). | The week before July 6, 2023 (i.e., in late June 2023). | [2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q21.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q21.md) | [2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q21.md](../2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q21.md) |
| conv0_q25 | temporal | When did Caroline go to the LGBTQ conference? | 10 July 2023 | November 8, 2026. | July 10, 2023. | [2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q25.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q25.md) | [2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q25.md](../2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q25.md) |
| conv0_q26 | temporal | When did Melanie read the book "nothing is impossible"? | 2022 | Last year. | There’s no memory of Melanie reading a book titled “Nothing Is Impossible.” The only reading noted is in October 2023, when she read a book Caroline recommended (title not specified). | [2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q26.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q26.md) | [2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q26.md](../2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q26.md) |
| conv0_q28 | temporal | When did Caroline go to the adoption meeting? | The friday before 15 July 2023 | November 3. | July 14, 2023. | [2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q28.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q28.md) | [2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q28.md](../2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q28.md) |
| conv0_q29 | temporal | When did Melanie go to the pottery workshop? | The Friday before 15 July 2023 | November 4, 2026. | July 7, 2023 and July 14, 2023. | [2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q29.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q29.md) | [2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q29.md](../2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q29.md) |
| conv0_q31 | temporal | When did Melanie go camping in June? | The week before 27 June 2023 | There isn’t a June camping trip mentioned. The memories list camping: - around Nov 3–4, 2026 (mountains) - around Nov 10, 2026 (forest) - late Oct 2026 (two weekends before Nov 10) - “last year” during the Perseid meteor shower (mid‑August)  No June date is recorded. | Around June 20–26, 2023. | [2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q31.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q31.md) | [2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q31.md](../2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q31.md) |
| conv0_q32 | multi-hop | What LGBTQ+ events has Caroline participated in? | Pride parade, school speech, support group | - Pride parades and Pride events (including attending with her mentee and a prior Pride festival) - An LGBTQ conference - A transgender poetry reading - LGBTQ+ counseling workshops - An LGBTQ support group meeting - A school event where she spoke about her transgender journey - An LGBTQ advocacy event |  | [2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q32.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q32.md) | [2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q32.md](../2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q32.md) |
| conv0_q35 | temporal | When did Melanie go camping in July? | two weekends before 17 July 2023 | There isn’t a memory showing a July camping trip for Melanie. The recorded trips were in late October and early November 2026, plus a memorable “last year” Perseid meteor-shower campout. | The weekend of July 1–2, 2023. | [2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q35.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q35.md) | [2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q35.md](../2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q35.md) |
| conv0_q36 | temporal | When did Caroline join a mentorship program? | The weekend before 17 July 2023 | Around November 5, 2026. | Around July 15–16, 2023 (the weekend before July 17, 2023). | [2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q36.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q36.md) | [2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q36.md](../2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q36.md) |
| conv0_q41 | temporal | When did Caroline join a new activist group? | The Tuesday before 20 July 2023 | November 3, 2026. | July 18, 2023. | [2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q41.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q41.md) | [2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q41.md](../2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q41.md) |
| conv0_q44 | temporal | When is Melanie's daughter's birthday? | 13 August | November 9 | August 13 | [2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q44.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q44.md) | [2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q44.md](../2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q44.md) |
| conv0_q45 | temporal | When did Caroline attend a pride parade in August? | The Friday before 14 August 2023 | There’s no recorded August pride parade attendance for Caroline. Her documented pride parades were in late October and on November 3–4. | August 11, 2023. | [2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q45.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q45.md) | [2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q45.md](../2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q45.md) |
| conv0_q49 | temporal | When did Caroline and Melanie go to a pride fesetival together? | 2022 | Last year (2025). | 2022. | [2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q49.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q49.md) | [2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q49.md](../2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q49.md) |
| conv0_q53 | temporal | When did Caroline apply to adoption agencies? | The week of 23 August 2023 | Around November 10, 2026. | Around August 23, 2023. | [2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q53.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q53.md) | [2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q53.md](../2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q53.md) |
| conv0_q54 | temporal | When did Caroline draw a self-portrait? | The week before 23 August 2023 | Around November 3, 2026 (i.e., the week before November 10, 2026). | Around August 16, 2023. | [2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q54.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q54.md) | [2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q54.md](../2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q54.md) |
| conv0_q57 | temporal | When did Caroline encounter people on a hike and have a negative experience? | The week before 25 August 2023 | - Week of November 3, 2026: Caroline went hiking and had a negative encounter with some people, which bothered her and led her to try to apologize afterward. - November 10, 2026: She again had a negative experience on a hike when she encountered a group of religious conservatives who upset her. | Around August 18, 2023. | [2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q57.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q57.md) | [2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q57.md](../2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q57.md) |
| conv0_q58 | temporal | When did Melanie make a plate in pottery class? | 24 August 2023 | November 9, 2026 | August 24, 2023. | [2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q58.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q58.md) | [2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q58.md](../2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q58.md) |
| conv0_q62 | temporal | When did Melanie go to the park? | 27 August 2023 | November 9, 2026. | August 27, 2023. | [2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q62.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q62.md) | [2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q62.md](../2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q62.md) |
| conv0_q63 | temporal | When is Caroline's youth center putting on a talent show? | September 2023 | December 2026 | September 2023. | [2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q63.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q63.md) | [2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q63.md](../2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q63.md) |
| conv0_q67 | temporal | When did Caroline go biking with friends? | The weekend before 13 September 2023 | Last weekend. | The weekend of September 9–10, 2023. | [2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q67.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q67.md) | [2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q67.md](../2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q67.md) |
| conv0_q68 | temporal | How long has Melanie been practicing art? | Since 2016 | Seven years. | Seven years. | [2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q68.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q68.md) | [2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q68.md](../2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q68.md) |
| conv0_q73 | temporal | When did Melanie get hurt? | September 2023 | October 2026. | September 2023. | [2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q73.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q73.md) | [2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q73.md](../2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q73.md) |
| conv0_q74 | temporal | When did Melanie's family go on a roadtrip? | The weekend before 20 October 2023 | November 10, 2026. | The weekend of October 14–15, 2023. | [2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q74.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q74.md) | [2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q74.md](../2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q74.md) |
| conv0_q76 | multi-hop | When did Melanie go on a hike after the roadtrip? | 19 October 2023 | November 9, 2026. | October 19, 2023. | [2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q76.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q76.md) | [2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q76.md](../2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q76.md) |
| conv0_q79 | temporal | When did Caroline pass the adoption interview? | The Friday before 22 October 2023 | November 3, 2026 | October 20, 2023. | [2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q79.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q79.md) | [2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q79.md](../2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q79.md) |
| conv0_q80 | temporal | When did Melanie buy the figurines? | 21 October 2023 | Recently. | Recently—she said on October 22, 2023 that she had just bought them. | [2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q80.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q80.md) | [2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q80.md](../2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q80.md) |
| conv0_q94 | single-hop | What is Melanie's hand-painted bowl a reminder of? | art and self-expression | Her creativity and self-expression—the joy she gets from pottery and how it helps her express her emotions. | That detail is about Caroline’s bowl, not Melanie’s—Caroline’s hand-painted bowl reminds her of art and self-expression. | [2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q94.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q94.md) | [2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q94.md](../2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q94.md) |
| conv0_q141 | single-hop | What does Caroline's drawing symbolize for her? | Freedom and being true to herself. | Freedom and authenticity—a reminder to stay true to herself and embrace her womanhood. |  | [2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q141.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q141.md) | [2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q141.md](../2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q141.md) |
| conv0_q143 | single-hop | What happened to Melanie's son on their road trip? | He got into an accident | He was involved in a car accident during the trip (thankfully he was okay). |  | [2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q143.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q143.md) | [2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q143.md](../2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q143.md) |
| conv0_q145 | single-hop | How did Melanie feel about her family after the accident? | They are important and mean the world to her | She felt her family was super important and was especially grateful for them—seeing them as her biggest support and motivation, admiring their resilience, and feeling they gave her strength after her son’s accident. |  | [2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q145.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q145.md) | [2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q145.md](../2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q145.md) |
| conv0_q146 | single-hop | How did Melanie's children handle the accident? | They were scared but resilient | They were scared at first, but calmed down after being reassured their brother would be okay. |  | [2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q146.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q146.md) | [2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q146.md](../2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q146.md) |
| conv0_q147 | single-hop | How did Melanie feel after the accident? | Grateful and thankful for her family | She said it was scary, and afterward she felt especially grateful for her family and how important they are to her. |  | [2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q147.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q147.md) | [2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q147.md](../2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q147.md) |
| conv0_q149 | single-hop | What do Melanie's family give her? | Strength and motivation | Love and support—they also keep her motivated and give her strength. |  | [2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q149.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q149.md) | [2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q149.md](../2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q149.md) |
| conv0_q150 | single-hop | How did Melanie feel about her family supporting her? | She appreciated them a lot | She felt grateful and lucky—she thought their support was awesome. It gave her motivation and strength and made hard times easier. |  | [2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q150.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q150.md) | [2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q150.md](../2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q150.md) |
| conv0_q151 | single-hop | What did Melanie do after the road trip to relax? | Went on a nature walk or hike | She went hiking in the mountains with her kids. |  | [2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q151.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q151.md) | [2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q151.md](../2026-11-14_0302-locomo-conv0-session-date/trace_facts/conv0_q151.md) |

## 3. Tokens

Estimate of retrieved-memory context only (tiktoken o200k_base, memory texts of the first N search_results per cutoff); excludes prompts, answers and judge calls.

| cutoff | mean_A | median_A | mean_B | median_B |
|---|---|---|---|---|
| top_10 | 280.8 | 281.0 | 261.4 | 278.0 |
| top_20 | 558.1 | 554.0 | 517.7 | 561.0 |
| top_50 | 1375.9 | 1386.5 | 1275.0 | 1379.0 |
| top_200 | 5315.2 | 5242.5 | 4931.2 | 5207.5 |

API calls by design:

| call type | A | B | formula |
|---|---|---|---|
| answer calls | 608 | 608 | questions x 4 cutoffs |
| judge calls | 608 | 608 | questions x 4 cutoffs |
| Mem0 add requests | 419 | 419 | ingestion chunks processed |

Billed tokens: not recorded by the benchmark.

- A: check the OpenAI usage dashboard for the time window `2026-11-10T14:47:50Z` to `2026-11-13T17:23:20Z` (UTC).
- B: check the OpenAI usage dashboard for the time window `2026-11-14T03:02:35Z` to `2026-11-14T06:04:33Z` (UTC).

## 4. Latency

Search latency per question (`retrieval.search_latency_ms`), milliseconds:

| run | median | mean | p90 | max |
|---|---|---|---|---|
| A | 702.1 | 725.2 | 922.3 | 3002.7 |
| B | 580.5 | 4778.4 | 1055.4 | 58691.5 |

Whole-run wall time (results file timestamp minus manifest `started_utc`):

- A: `2026-11-10T14:47:50Z` to `2026-11-13T17:23:20Z` = 74h35m30s (268530s)
- B: `2026-11-14T03:02:35Z` to `2026-11-14T06:04:33Z` = 3h01m58s (10918s)

Phase times, final progress line from console.log for each phase:

- A, ingestion: `Ingest conv 0: 100%|██████████| 419/419 [20:33<00:00,  2.94s/it]`
- A, evaluation: `Questions conv 0: 100%|██████████| 152/152 [4:21:27<00:00, 103.21s/it]`
- B, ingestion: `Ingest conv 0: 100%|██████████| 419/419 [24:03<00:00,  3.45s/it]`
- B, evaluation: `Questions conv 0: 100%|██████████| 152/152 [2:37:52<00:00, 62.32s/it] `

Only search latency is measured per query. Add, answer and judge calls are not timed individually.

## 5. Storage

| | A | B |
|---|---|---|
| Memories | 736 | 771 |
| Entities | 371 | 386 |
| Links per entity, median | 1.0 | 2.0 |
| Links per entity, mean | 5.36 | 5.41 |
| Links per entity, max | 538 | 551 |

## 6. Note

Each run ingested conversation 0 separately with an LLM, so their stored memories differ (see Storage). A flip can come from the weight change or from a different stored memory; this comparison does not separate the two.

