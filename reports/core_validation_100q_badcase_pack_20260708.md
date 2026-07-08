# Core Validation 100q — Badcase Pack
Generated: 2026-07-08

Total questions: 100

## Flag Summary

| Flag | Count |
|---|---:|
| oracle_hit_but_wrong | 39 |
| mragent_correct_rag_wrong | 27 |
| temporal_question | 20 |
| cat5_null_gold | 20 |
| mragent_hit_but_wrong | 17 |
| mragent_miss_but_oracle_correct | 5 |
| rag_correct_mragent_wrong | 4 |
| oracle_evidence_count==0 | 2 |

## Cat5 Adversarial (null gold)
Count: 20

| sample | qi | question | mragent_pred | rag_pred | gold | flags |
|---|---|---|---|---|---|---|
| conv-26 | 3 | What did Melanie make for a local church? | Not mentioned in the conversation | Not mentioned in the conversation. | None | cat5_null_gold |
| conv-26 | 5 | What type of instrument does Caroline play? | Not mentioned in the conversation | Not mentioned in the conversation | None | cat5_null_gold |
| conv-30 | 2 | How is Jon's store doing? | Not mentioned in the conversation | Not mentioned in the conversation. | None | cat5_null_gold |
| conv-30 | 3 | What did Jon want his customers to feel in her store? | cozy and comfortable | Not mentioned in the conversation | None | mragent_hit_but_wrong; mragent_miss_but_oracle_correct; rag_correct_mragent_wrong; cat5_null_gold |
| conv-41 | 4 | What important values does Maria want to teach her kids thro | Responsibility and compassion | Responsibility and compassion | None | oracle_hit_but_wrong; mragent_hit_but_wrong; cat5_null_gold |
| conv-41 | 9 | Why does Maria think it's important for younger generations  | Not mentioned in the conversation | Not mentioned in the conversation | None | oracle_hit_but_wrong; cat5_null_gold |
| conv-42 | 4 | What did Nate think of the caramel ice cream he made? | Super good, rich and creamy | Not mentioned in the conversation. | None | oracle_hit_but_wrong; mragent_hit_but_wrong; rag_correct_mragent_wrong; cat5_null_gold |
| conv-42 | 10 | Why did Joanna choose the hair color she did? | Not mentioned in the conversation | Not mentioned in the conversation | None | oracle_hit_but_wrong; cat5_null_gold |
| conv-43 | 5 | What new activity has John started learning in August 2023? | no information available | Not mentioned in the conversation | None | cat5_null_gold |
| conv-43 | 7 | What special memory does "Fifty Shades of Grey" bring to Tim | Not mentioned in the conversation | Not mentioned in the conversation. | None | cat5_null_gold |
| conv-44 | 2 | How does Andrew describe his dogs' response to snow? | Not mentioned in the conversation | Not mentioned in the conversation. | None | oracle_hit_but_wrong; cat5_null_gold |
| conv-44 | 10 | Which type of pizza did Audrey suggest trying first to someo | Not mentioned in the conversation | California | None | mragent_correct_rag_wrong; cat5_null_gold |
| conv-47 | 3 | What happened to James's kitten during the recent visit to t | Not mentioned in the conversation | Not mentioned in the conversation | None | cat5_null_gold |
| conv-47 | 10 | Why did James sign up for a ballet class? | Not mentioned in the conversation | Not mentioned in the conversation | None | cat5_null_gold |
| conv-48 | 1 | How did Jolene and her rival initially meet? | Not mentioned in the conversation | Not mentioned in the conversation | None | cat5_null_gold |

## MRAgent Correct, RAG Wrong (27 cases)

- **conv-26 Q6 (cat4)**: What was Melanie's reaction to her children enjoying the Grand Canyon?
  - Gold: She was happy and thankful | MRAgent: She was thankful and said the kids loved it and it was a nice way to relax after | RAG: no information available
- **conv-26 Q7 (cat2)**: When did Caroline go to the LGBTQ support group?
  - Gold: 7 May 2023 | MRAgent: 7 May 2023 | RAG: Yesterday
- **conv-26 Q8 (cat1)**: Where did Caroline move from 4 years ago?
  - Gold: Sweden | MRAgent: Sweden | RAG: From her home country
- **conv-30 Q1 (cat4)**: How does Gina describe the feeling that dance brings?
  - Gold: magical | MRAgent: It's like air; all her worries vanish; freedom; joy and thrill; magical; ain't n | RAG: As soon as Gina starts dancing, all her worries vanish.
- **conv-30 Q6 (cat4)**: What does Jon plan to do at the grand opening of his dance studio?
  - Gold: savor all the good vibes | MRAgent: make some awesome memories and savor all the good vibes | RAG: No information available.
- **conv-30 Q9 (cat2)**: When did Jon start to go to the gym?
  - Gold: March, 2023 | MRAgent: the week before 16 March 2023 | RAG: Last week
- **conv-41 Q5 (cat4)**: What is the name of Maria's second puppy?
  - Gold: Shadow | MRAgent: Shadow | RAG: Coco
- **conv-41 Q8 (cat2)**: When did Maria go to the beach?
  - Gold: December 2022 | MRAgent: December 2022 | RAG: Last month.
- **conv-42 Q3 (cat4)**: What did Nate do while Joanna was on her road trip?
  - Gold: Won a video game tournament | MRAgent: won his fourth video game tournament | RAG: Nate was winning.
- **conv-42 Q5 (cat3)**: What nickname does Nate use for Joanna?
  - Gold: Jo | MRAgent: Jo | RAG: no information available
- **conv-42 Q8 (cat2)**: When is Nate hosting a gaming party?
  - Gold: The weekend after 3June, 2022. | MRAgent: the weekend of 18 June 2023 | RAG: Next month
- **conv-43 Q9 (cat2)**: What year did John start surfing?
  - Gold: 2018 | MRAgent: 2018 | RAG: Based on the context, John started surfing five years ago from the time of the c
- **conv-43 Q10 (cat2)**: When did John take a trip to the Rocky Mountains?
  - Gold: 2022 | MRAgent: 2022 | RAG: Last year
- **conv-44 Q1 (cat1)**: Did Audrey and Andrew grow up with a pet dog?
  - Gold: Yes | MRAgent: Yes | RAG: no information available
- **conv-44 Q7 (cat2)**: When did Audrey get into an accident in the park?
  - Gold: between October 19 and 24, 2023 | MRAgent: 22 September 2023 | RAG: Last Friday

## RAG Correct, MRAgent Wrong (4 cases)

- **conv-30 Q3 (cat5)**: What did Jon want his customers to feel in her store?
  - Gold: None | MRAgent: cozy and comfortable | RAG: Not mentioned in the conversation
- **conv-42 Q4 (cat5)**: What did Nate think of the caramel ice cream he made?
  - Gold: None | MRAgent: Super good, rich and creamy | RAG: Not mentioned in the conversation.
- **conv-43 Q4 (cat3)**: What is a Star Wars book that Tim might enjoy?
  - Gold: Star Wars: Jedi Apprentice by Judy Blundell and David Farland. It is a highly rated and immersive series about his favorite movies. | MRAgent: no information available | RAG: Based on the context, Tim might enjoy "A Dance with Dragons" since he highly rec
- **conv-43 Q6 (cat1)**: What similar sports collectible do Tim and John own?
  - Gold: signed basketball | MRAgent: no information available | RAG: Basketball signed by a favorite player

## Temporal Questions — Both MRAgent & RAG Wrong (4 cases)

- **conv-26 Q1**: How long has Melanie been practicing art?
  - Gold: Since 2016 | MRAgent: Seven years | RAG: Seven years
- **conv-41 Q7**: When did John take a road trip to the Pacific Northwest?
  - Gold: 2022 | MRAgent: no information available | RAG: No information available
- **conv-44 Q3**: How many pets did Andrew have, as of September 2023?
  - Gold: one | MRAgent: no information available | RAG: As of September 2023, Andrew had no pets.
- **conv-48 Q7**: When did Deborah go to an art show with Anna?
  - Gold: on 9 April, 2023 | MRAgent: no information available | RAG: no information available

## ERRORs (2 total)

| sample | qi | method | question | gold_answer |
|---|---|---|---|---|
| conv-50 | 9 | mragent | Who supports Calvin in tough times? | friends and team |
| conv-50 | 10 | mragent | Would Dave prefer working on a Dodge Charger or a Subaru For | Dodge Charger |
