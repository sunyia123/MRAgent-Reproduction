# MRAgent 100q Badcase Pack
Generated: 2026-07-09

## Summary
Total questions: 100
- Overall F1: 0.629
- ERRORs: 2


## F1 < 0.3 (26 cases)

- **conv-26 Q3 (cat3)**: Would Melanie be considered a member of the LGBTQ community?
  - Pred: No | Gold: Likely no, she does not refer to herself as part of it
- **conv-26 Q6 (cat2)**: How long has Melanie been practicing art?
  - Pred: Seven years | Gold: Since 2016
- **conv-30 Q1 (cat1)**: What do Jon and Gina both have in common?
  - Pred: They both love dance and use it for stress relief | Gold: They lost their jobs and decided to start their own businesses.
- **conv-30 Q7 (cat4)**: How does Gina describe the feeling that dance brings?
  - Pred: It's like air; all her worries vanish; freedom; joy and thrill; magical; ain't n | Gold: magical
- **conv-30 Q9 (cat5)**: What did Jon want his customers to feel in her store?
  - Pred: cozy and comfortable | Gold: None
- **conv-41 Q2 (cat3)**: What might John's financial status be?
  - Pred: no information available | Gold: Middle-class or wealthy
- **conv-41 Q3 (cat2)**: When did John take a road trip to the Pacific Northwest?
  - Pred: no information available | Gold: 2022
- **conv-41 Q6 (cat3)**: Would John be open to moving to another country?
  - Pred: no information available | Gold: No, he has goals specifically in the U.S. like joining the military and running 
- **conv-41 Q9 (cat5)**: What important values does Maria want to teach her kids through adopting a rescue dog?
  - Pred: Responsibility and compassion | Gold: None
- **conv-42 Q1 (cat3)**: Is it likely that Nate has friends besides Joanna?
  - Pred: Yes | Gold: Yesteammates on hisvideo game team.
- **conv-42 Q4 (cat2)**: When is Nate hosting a gaming party?
  - Pred: the weekend of 18 June 2023 | Gold: The weekend after 3June, 2022.
- **conv-42 Q6 (cat1)**: How many times has Nate taken his turtles on a walk?
  - Pred: 2 | Gold: Twice.
- **conv-42 Q9 (cat5)**: What did Nate think of the caramel ice cream he made?
  - Pred: Super good, rich and creamy | Gold: None
- **conv-43 Q2 (cat1)**: What similar sports collectible do Tim and John own?
  - Pred: no information available | Gold: signed basketball
- **conv-43 Q3 (cat3)**: What could John do after his basketball career?
  - Pred: Start a foundation and do charity work; make a positive difference and inspire o | Gold: become a basketball coach since he likes giving back and leadership

## Evidence Hit but Wrong (14 cases)

- **conv-26 Q3 (cat3)**: Would Melanie be considered a member of the LGBTQ community?
  - Pred: No | Gold: Likely no, she does not refer to herself as part of it
  - F1=0.154, ev_hit=1.00
- **conv-26 Q5 (cat3)**: Would Melanie likely enjoy the song "The Four Seasons" by Vivaldi?
  - Pred: Likely yes | Gold: Yes; it's classical music
  - F1=0.333, ev_hit=1.00
- **conv-26 Q6 (cat2)**: How long has Melanie been practicing art?
  - Pred: Seven years | Gold: Since 2016
  - F1=0.000, ev_hit=1.00
- **conv-26 Q8 (cat4)**: What was Melanie's reaction to her children enjoying the Grand Canyon?
  - Pred: She was thankful and said the kids loved it and it was a nice way to relax after | Gold: She was happy and thankful
  - F1=0.300, ev_hit=1.00
- **conv-30 Q5 (cat4)**: What does Gina's tattoo symbolize?
  - Pred: Freedom - dancing without worrying what people think. A reminder to follow my pa | Gold: Freedom and expressing herself through dance
  - F1=0.316, ev_hit=1.00
- **conv-30 Q7 (cat4)**: How does Gina describe the feeling that dance brings?
  - Pred: It's like air; all her worries vanish; freedom; joy and thrill; magical; ain't n | Gold: magical
  - F1=0.105, ev_hit=1.00
- **conv-41 Q9 (cat5)**: What important values does Maria want to teach her kids through adopting a rescue dog?
  - Pred: Responsibility and compassion | Gold: None
  - F1=0.000, ev_hit=1.00
- **conv-42 Q4 (cat2)**: When is Nate hosting a gaming party?
  - Pred: the weekend of 18 June 2023 | Gold: The weekend after 3June, 2022.
  - F1=0.222, ev_hit=1.00
- **conv-42 Q6 (cat1)**: How many times has Nate taken his turtles on a walk?
  - Pred: 2 | Gold: Twice.
  - F1=0.000, ev_hit=1.00
- **conv-42 Q9 (cat5)**: What did Nate think of the caramel ice cream he made?
  - Pred: Super good, rich and creamy | Gold: None
  - F1=0.000, ev_hit=1.00
- **conv-48 Q8 (cat4)**: What picture did Jolene share related to feeling overwhelmed?
  - Pred: a photo of two notebooks with a blue cover and a white strip; a photo of a notep | Gold: a photo of a desk with a notebook and a computer monitor
  - F1=0.438, ev_hit=1.00
- **conv-50 Q2 (cat3)**: Does Dave's shop employ a lot of people?
  - Pred: No | Gold: Yes
  - F1=0.000, ev_hit=1.00
- **conv-50 Q4 (cat2)**: When did Calvin book flight tickets to Boston?
  - Pred: the week before 2 September 2023 | Gold: last week of August 2023
  - F1=0.400, ev_hit=1.00
- **conv-50 Q7 (cat4)**: How does Dave feel about the reactions of people when they see the finished restoration project?
  - Pred: satisfying and makes all the hard work worth it; he's glad he can make people ha | Gold: satisfying and worth the hard work
  - F1=0.444, ev_hit=1.00

## Miss Gold Evidence (ev_hit=0) (27 cases)

- **conv-26 Q10 (cat5)**: What type of instrument does Caroline play?
  - Pred: Not mentioned in the conversation | Gold: None
  - F1=1.000, ev_hit=0.00
- **conv-30 Q1 (cat1)**: What do Jon and Gina both have in common?
  - Pred: They both love dance and use it for stress relief | Gold: They lost their jobs and decided to start their own businesses.
  - F1=0.105, ev_hit=0.00
- **conv-30 Q9 (cat5)**: What did Jon want his customers to feel in her store?
  - Pred: cozy and comfortable | Gold: None
  - F1=0.000, ev_hit=0.00
- **conv-41 Q2 (cat3)**: What might John's financial status be?
  - Pred: no information available | Gold: Middle-class or wealthy
  - F1=0.000, ev_hit=0.00
- **conv-41 Q3 (cat2)**: When did John take a road trip to the Pacific Northwest?
  - Pred: no information available | Gold: 2022
  - F1=0.000, ev_hit=0.00
- **conv-41 Q6 (cat3)**: Would John be open to moving to another country?
  - Pred: no information available | Gold: No, he has goals specifically in the U.S. like joining the military and running 
  - F1=0.125, ev_hit=0.00
- **conv-42 Q1 (cat3)**: Is it likely that Nate has friends besides Joanna?
  - Pred: Yes | Gold: Yesteammates on hisvideo game team.
  - F1=0.000, ev_hit=0.00
- **conv-42 Q2 (cat3)**: What nickname does Nate use for Joanna?
  - Pred: Jo | Gold: Jo
  - F1=1.000, ev_hit=0.00
- **conv-43 Q2 (cat1)**: What similar sports collectible do Tim and John own?
  - Pred: no information available | Gold: signed basketball
  - F1=0.000, ev_hit=0.00
- **conv-43 Q3 (cat3)**: What could John do after his basketball career?
  - Pred: Start a foundation and do charity work; make a positive difference and inspire o | Gold: become a basketball coach since he likes giving back and leadership
  - F1=0.000, ev_hit=0.00
- **conv-43 Q6 (cat3)**: What is a Star Wars book that Tim might enjoy?
  - Pred: no information available | Gold: Star Wars: Jedi Apprentice by Judy Blundell and David Farland. It is a highly ra
  - F1=0.000, ev_hit=0.00
- **conv-43 Q9 (cat5)**: What new activity has John started learning in August 2023?
  - Pred: no information available | Gold: None
  - F1=1.000, ev_hit=0.00
- **conv-43 Q10 (cat5)**: What special memory does "Fifty Shades of Grey" bring to Tim?
  - Pred: Not mentioned in the conversation | Gold: None
  - F1=1.000, ev_hit=0.00
- **conv-44 Q2 (cat3)**: What is an indoor activity that Andrew would enjoy doing while make his dog happy?
  - Pred: playing board games | Gold: cook dog treats
  - F1=0.000, ev_hit=0.00
- **conv-44 Q3 (cat1)**: Did Audrey and Andrew grow up with a pet dog?
  - Pred: Yes | Gold: Yes
  - F1=1.000, ev_hit=0.00

## ERRORs (2 cases)

- **conv-50 Q5 (cat3)**: Would Dave prefer working on a Dodge Charger or a Subaru Forester?
  - Pred: ERROR | Gold: Dodge Charger
- **conv-50 Q6 (cat1)**: Who supports Calvin in tough times?
  - Pred: ERROR | Gold: friends and team

## Cat5 Null-Gold Over-Answer (3 cases)

- **conv-30 Q9 (cat5)**: What did Jon want his customers to feel in her store?
  - Pred: cozy and comfortable | Gold: None
- **conv-41 Q9 (cat5)**: What important values does Maria want to teach her kids through adopting a rescue dog?
  - Pred: Responsibility and compassion | Gold: None
- **conv-42 Q9 (cat5)**: What did Nate think of the caramel ice cream he made?
  - Pred: Super good, rich and creamy | Gold: None

## Temporal Wrong (cat2, F1<0.3) (6 cases)

- **conv-26 Q6 (cat2)**: How long has Melanie been practicing art?
  - Pred: Seven years | Gold: Since 2016
- **conv-41 Q3 (cat2)**: When did John take a road trip to the Pacific Northwest?
  - Pred: no information available | Gold: 2022
- **conv-42 Q4 (cat2)**: When is Nate hosting a gaming party?
  - Pred: the weekend of 18 June 2023 | Gold: The weekend after 3June, 2022.
- **conv-44 Q4 (cat2)**: When did Audrey get into an accident in the park?
  - Pred: 22 September 2023 | Gold: between October 19 and 24, 2023
- **conv-44 Q6 (cat2)**: How many pets did Andrew have, as of September 2023?
  - Pred: no information available | Gold: one
- **conv-48 Q6 (cat2)**: When did Deborah go to an art show with Anna?
  - Pred: no information available | Gold: on 9 April, 2023

## Category 3 Reasoning Fail (F1<0.3) (10 cases)

- **conv-26 Q3 (cat3)**: Would Melanie be considered a member of the LGBTQ community?
  - Pred: No | Gold: Likely no, she does not refer to herself as part of it
- **conv-41 Q2 (cat3)**: What might John's financial status be?
  - Pred: no information available | Gold: Middle-class or wealthy
- **conv-41 Q6 (cat3)**: Would John be open to moving to another country?
  - Pred: no information available | Gold: No, he has goals specifically in the U.S. like joining the military and running 
- **conv-42 Q1 (cat3)**: Is it likely that Nate has friends besides Joanna?
  - Pred: Yes | Gold: Yesteammates on hisvideo game team.
- **conv-43 Q3 (cat3)**: What could John do after his basketball career?
  - Pred: Start a foundation and do charity work; make a positive difference and inspire o | Gold: become a basketball coach since he likes giving back and leadership
- **conv-43 Q6 (cat3)**: What is a Star Wars book that Tim might enjoy?
  - Pred: no information available | Gold: Star Wars: Jedi Apprentice by Judy Blundell and David Farland. It is a highly ra
- **conv-44 Q2 (cat3)**: What is an indoor activity that Andrew would enjoy doing while make his dog happy?
  - Pred: playing board games | Gold: cook dog treats
- **conv-44 Q5 (cat3)**: Which national park could Audrey and Andrew be referring to in their conversations?
  - Pred: no information available | Gold: Voyageurs National Park
- **conv-50 Q2 (cat3)**: Does Dave's shop employ a lot of people?
  - Pred: No | Gold: Yes
- **conv-50 Q5 (cat3)**: Would Dave prefer working on a Dodge Charger or a Subaru Forester?
  - Pred: ERROR | Gold: Dodge Charger

## Single-Hop Low F1 (cat4, F1<0.3) (1 cases)

- **conv-30 Q7 (cat4)**: How does Gina describe the feeling that dance brings?
  - Pred: It's like air; all her worries vanish; freedom; joy and thrill; magical; ain't n | Gold: magical

## ERROR Detail (conv-50)

### ERROR #1 — API Timeout
- **Question**: Would Dave prefer working on a Dodge Charger or a Subaru Forester?
- **Sample**: conv-50, question_index=5, orig_idx=39
- **Error Type**: api_timeout
- **Error Message**: Request timed out
- **Root Cause**: The API call to SiliconFlow timed out (600s) during the extract_question_keys phase, before the agent loop started. tool_calls=0, runtime_sec=0.
- **Evidence**: Run log line: [ERROR] question5 (orig idx 39) failed: Request timed out.

### ERROR #2 — JSON Parse Failure
- **Question**: Who supports Calvin in tough times?
- **Sample**: conv-50, question_index=6, orig_idx=53
- **Error Type**: json_parse_failure
- **Error Message**: chat_text: all 3 JSON parse attempts exhausted.
- **Root Cause**: The model returned a valid-looking but truncated/incomplete JSON output (a tag_scores dict with support-related keywords). The JSON was cut off mid-structure, causing all 3 parse attempts to fail. tool_calls=0, runtime_sec=0.
- **Raw Output Head**: {"keyword": "Calvin", "tag_scores": {"support": 1.0, "support system": 1.0, ... (truncated)
- **Fix**: Set ENABLE_JSON_REPAIR=1 to enable auto-repair, or increase max_tokens.

## Badcase Count Summary

| Category | Count |
|---|---|
| F1 < 0.3 | 26 |
| Evidence Hit but Wrong Answer | 14 |
| Miss Gold Evidence (ev_hit=0) | 27 |
| Cat5 Null-Gold Over-Answer | 3 |
| Temporal Wrong (cat2, F1<0.3) | 6 |
| Category 3 Reasoning Fail (F1<0.3) | 10 |
| Single-Hop Low F1 (cat4, F1<0.3) | 1 |
| ERRORs | 2 |
