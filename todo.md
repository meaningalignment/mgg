To try:

- [x] generate 10 different user questions asked to chatGPT
- [x] for each, split them into moral dimensions
- [x] try regenerate questions from dimensions
- [ ] see if we can summarize the dimensions into a context 
- [ ] see if we can create perturbations of a context summary by adding / removing dimensions

Later:

- [ ] generate 90 new questions from context perturbations
- [ ] split them into context dimensions, again, cluster, compare?



# Findings
- It is not straightforward to generate good seed questions. Could probably be improved through simulated dialogue.
- Regenerating questions from extracted dimensions works pretty well:
[View Seed Questions](./outputs/seed_questions.csv)