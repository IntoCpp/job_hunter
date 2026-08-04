Score how well a job posting matches the candidate profile on a 0.00 to 1.00 scale.

The posting may be in English or French; evaluate fit regardless of language. Interpret equivalent job titles and responsibilities across languages (for example, "Directeur de développement logiciel" and "Software Development Manager").

User job search preferences indicate what the candidate wants to prioritize, accept, or avoid. Increase the score for preferred roles, keep acceptable roles competitive, and lower the score for roles that conflict with user preferences or excluded roles.

Software relevance is critical:
- The position MUST involve software development.
- The presence of the word "Development" alone is NOT sufficient.
- Reject or heavily penalize roles such as Manufacturing Development Manager, Business Development Manager, non-software Product Development Manager, Process Engineer, Manufacturing Engineering, Industrial Engineering, Construction, Mechanical Engineering, and any non-software development role.

Only evaluate complete postings with company, title, and description present.

Return JSON with keys:
- overall (number, 0.00 to 1.00)
- software_relevance (number, 0.00 to 1.00)
- leadership (number, 0.00 to 1.00)
- management (number, 0.00 to 1.00)
- location (number, 0.00 to 1.00)
- reason (string)

If the posting is incomplete or not a software development role, set overall to 0.00 and explain why in reason.
