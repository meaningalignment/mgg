# Think a bit about how this should work.

Moral dimensions exist of a context. A moral dimension could be "The user is a christian". Could it also be something like "When the user is in distress"? "In Distress" is common denominator there.
Either way, I think it's a good idea to deduplicate dimensions like this. A dimension should have only one verb, like "in".

Unclear what the right level of generality should be. Could redo the process with these short strings. Could represent a situtation as a combination of these. Could create perturbations on situations by adding / removing / highlighting these contexts.

I have a sense that something might be lost when doing that. And that these deliberations should be on the context level, not the dimension level. Or rather, that a context is made up of several dimensions that all are important. They are all far more detailed than the ones we used in our initial experiment.

The problem with the current graph structure is that wisdom upgrades are "voted for" in the context of scenarios / situations consisting of many moral dimensions. But this might not necessarily be a problem.

To try:

- [x] generate 10 different user questions asked to chatGPT
- [x] for each, split them into context dimensions
- [x] try regenerate questions from dimensions
- [ ] generate 90 new questions from context perturbations
- [ ] split them into context dimensions, again, cluster, compare?



# Findings
- It is not straightforward to generate good seed questions. Could probably be improved through simulated dialogue.
- Regenerating questions from extracted dimensions works pretty well:
[View Seed Questions](./outputs/seed_questions.csv)


# Questions

How to model contexts? How atomic should we be?

There are some arguments for deliberating on a particular summarized situations. Or you can deliberate on a moral dimension.

The graph is currently working on moral aspects, not situations. Alternatively you could generate a situation for the edges with the moral dimensions. An edge would be drawn for 

A -> [when discussing religious matters, when offering advice, when xyz] -> B

How do you then traverse this graph, when we find ourselves in a situation where this unique combination of moral dimensions doesn't exist?

You could generate stories where the primary moral aspect in question is one in the tuple.


Here are dimensions from abortion question:

```
"The user identifies as Christian.",
"The user is considering an abortion.",
"The user faces a life-altering decision",
"The user is seeking guidance or advice.",
```

They could be reformatted:

```
When advising someone identifying as Christian
When advising someone considering an abortion
When helping someone with a life-altering decision
When helping someone with guidance or advice
```

There is also a "granularity level" question:

```
When advising a christian girl considering an abortion
When advising someone with religious beliefs in conflict with a decision
When advising someone on relgious matters
When advising someone
When advising
```

In this case, the two first ones are kind of important together. A situation someone finds themselves in is arguably a combination of relevant moral dimensions.

Example:
advising someone about abortion / identifying as Christian.

Could be mitigated by having each scenario consist of several moral dimensions. These could change over the course of the discussion.
An edge could be for a collection of dimensions ([When helping someone with guidance or advice, When helping someone with a life-altering decision])
You could trim moral graph "strictly" by 

