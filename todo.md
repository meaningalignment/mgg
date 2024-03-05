# To try:

- [x] get 10 seed questions
- [x] can we generate lots of good questions from those 10?
- [x] can we split questions into moral dimensions
- [x] can we somewhat robustly recreate question from dimensions
- [x] can we identify 1-2 most relevant moral dimensions and summarize into a generalized context string
- [x] can we identify edge cases, perturb questions, and make sure context string changes appropriately?
- [x] can we use a context, expand to a story about transitioning from one value to another, and expand of each of these values to full sets of APs?


# Findings
- Given a few examples and maxed-out temperature, generating good seed questions is trivial.
- Regenerating questions from extracted dimensions works pretty well
- Including the definition of a "meaningful choice" helps with creating good dimensions
- Identifying moral contexts and getting to a context string works pretty well when perturbing the story, adding detail etc.


