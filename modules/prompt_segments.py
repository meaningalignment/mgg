moral_dimensions_definition = """# Moral Dimension Definition
- A moral dimension is an aspect of a situation that could be the basis for a meaningful choice (see definition below). 
- Moral dimensions should be a sentence of only a few words, starting with 'When'.
- Moral dimensions should be descriptive of the situation – it should not be about what the user is feeling, valuing, wanting or needing. Instead, it should be about the situation or the state the user is in. For instance, instead of 'When the user needs support for feeling a difficult emotion', return 'When the user is struggling with feeling a difficult emotion'.
- Moral dimensions should be as general as possible. For example, instead of "When the user is choosing between Waterlake festival or staying with his mom, who has tuberculosis", generalize to "When the user is making a decision between a fun event or staying with an ailing family member".
- It should be possible to reconstruct the original question, or a close approximation of it, by combining all the moral dimensions. In other words, the dimensions should together cover the entire moral valence of the situation.
- No dimension should be made redundant by another dimension. For example, if one dimension is 'When the user is contemplating a tough, irreversible life decision', do not include a redundant dimension like 'When the user is deliberating on a choice'. That is already implicit in the former."""

meaningful_choice_definition = """# Meaningful Choice Definition
Meaningful choices are choices which are understood as implicated in one’s character or identity, where options don’t just have instrumental value but can be considered as higher and lower, virtuous and vicious, more and less fulfilling, more and less refined, profound or superficial, noble or base, etc. An example of a meaningful choice is "Should I forgo this festival to be with my mom"? A decision says something about my character. An example of a non-meaningful choice is "What kind of dessert should I eat". Such a decision may say something about my preferences, but not something of my character."""


attentional_policy_definition = """# Attentional Policy Definition
Attentional policies are policies for attending to certain things when making a meaningful choices, like responding to the question at hand. When we are faced with a meaningful choice, we often attend to certain things before forming our set of options. This option set formation is itself an expression of our values. For example, at a dinner conversation, I might want to live with a certain kind of playfulness. Therefore, I look for witty things to say and fun threads to build on in the conversation. I do this before I actually choose between one witty thing to say over another.

Here are some guidelines for what makes a good set of attentional policies:

- Precise, but general, instructions that almost anyone could see how to follow with their attention. Don't say "LOVE and OPENNESS which emerges [...]" (too abstract). Instead, say "FEELINGS in my chest that indicate [...]" or "MOMENTS where a new kind of relating opens up". Ask the user questions, until you can achieve this specificity.
- The policies should fit together to form a coherent whole. They should not be unrelated, but should work together.
- Policies should start with a capitalized noun phrase that's the kind of thing to attend to ("MOMENTS", "SENSATIONS", "CHOICES", etc), followed by a qualifier phrase that provides detail on which type of that thing it's meaningful to attend to.
- A person should be able to clearly see how attending to the thing could produce a sense of meaning. Otherwise, specify more.
- Write from the perspective of the actor. These polices can be read as instructions to the person who wants to appreciate something according to this source of meaning. ("SENSATIONS that point to misgivings I have about the current path").
- Use general words. For instance, prefer "strangers" to "customers" when either would work. Prefer "objects" to "trees".
- No vague or abstract language. Don't use the word "meaningful" itself, or synonyms like "deep". Instead, say more precisely what's meaningful about attending to the thing."""


wiser_value_definition = """# What makes a value wiser than the previous one?
- There was an impure motive present in the previous value. An impure motive is a motive for acting a certain way that we think guards a value but is really serving a goal. For example, a value about friendship could have impure motives of wanting to be liked, when the really important thing it guards is finding people who are good for us.
- The previous value might be missing some other, important consideration for the context. For example, a value about being honest in dinner parties could miss clarification about what kind of honesty that is being referred to - is it about attending to what feels true in the body, or about attending to one's language to make sure it accurately depicts the world?
- The previous value unnecessarily conflicts with other important values for the context. A wiser value could balance the important good that the value is guarding with other important goods relevant to the context.
- The previous value might not get at the "heart" of the good it is trying to guard. For example, a value around instilling discipline when parenting could miss that the real good behind it is to help the child grow in agency. There might be other ways of living that better achieves this good, by for example igniting the child's own motivation through curiosity and exploration."""

summary_specification = """# Most Important Dimensions Summary Specification
The summary should be a short sentence summarizing the 1-2 most important moral dimensions using as few words as possible. It should start with 'When'."""
