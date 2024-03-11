moral_considerations_definition = """# Moral Considerations Definition
Imagine different ways the conversation could go, and that events could unfold, after your response. Are there ways the conversation could unfold which, on reflection, you might regret? Conversely, what will it take to reflect back on the conversation with a sense of peace? Try to see far into the future, and to think about your own role.

Then, see which aspects of the situation were relevant to these possibilities of regret or peace. These aspects are “moral considerations”.

- Moral considerations should be a sentence of only a few words, starting with 'When'.
- Moral considerations should be as general as possible. For example, instead of "When the user is choosing between Waterlake festival or staying with his mom, who has tuberculosis", generalize to "When the user is making a decision between a fun event or staying with an ailing family member".
- No consideration should be made redundant by another consideration. For example, if one consideration is 'When the user is contemplating a tough, irreversible life decision', do not include a redundant dimension like 'When the user is deliberating on a choice'. That is already implicit in the former."""

meaningful_choice_definition = """# Meaningful Choice Definition
Meaningful choices are choices which are understood as implicated in one’s character or identity, where options don’t just have instrumental value but can be considered as higher and lower, virtuous and vicious, more and less fulfilling, more and less refined, profound or superficial, noble or base, etc. An example of a meaningful choice is "Should I forgo this festival to be with my mom"? A decision says something about my character. An example of a non-meaningful choice is "What kind of dessert should I eat". Such a decision may say something about my preferences, but not something of my character."""


attentional_policy_definition = """# Attentional Policies Definition
Attentional policies are policies for attending to certain things when making a meaningful choices, like responding to the question at hand. When we are faced with a meaningful choice, we often attend to certain things before forming our set of options. This option set formation is itself an expression of our values. For example, at a dinner conversation, I might want to live with a certain kind of playfulness. Therefore, I look for witty things to say and fun threads to build on in the conversation. I do this before I actually choose between one witty thing to say over another.

Here are some guidelines for what makes a good set of attentional policies:

- **All policies should be clear enough that a person in the right situation would know what to attend to.**
- **Make sure policies aren't vague or abstract.** Use precise, but general, instructions that almost anyone could see how to follow with their attention. Avoid abstractions like "LOVE and OPENNESS which emerges". Instead, say "FEELINGS in my chest that indicate..." or "MOMENTS where a new kind of relating opens up". Don't use the word "meaningful" itself, or synonyms like "deep".
- **Start with plural noun phrases.** Policies should start with a capitalized phrase that's a kind of thing to attend to ("MOMENTS", "SENSATIONS", "CHOICES", "PEOPLE", etc), followed by a qualifying phrase that provides more detail.
- **Use general words.** For instance, prefer "strangers" to "customers" when either would work. Prefer "objects" to "trees". Find the level of specificity that's most general while still being clear. Remove names and irrelevant details.
- **All policies should work together as part of a 'source of meaning'.** A "source of meaning" is a way of living that is important to someone. Something that captures how they want to live, and which they find it meaningful to attend to in certain contexts. A source of meaning is more specific than words like "honesty" or "authenticity". It specifies a particular *kind* of honesty and authenticity, specified as a path of attention. A sources of meaning also isn't just something someone likes -- it opens a space of possibility for them, rather than just satisfying their preference."""


wiser_value_definition = """# What makes a value wiser than the previous one?
- There was an impure motive present in the previous value. An impure motive is a motive for acting a certain way that we think guards a value but is really serving a goal. For example, a value about friendship could have impure motives of wanting to be liked, when the really important thing it guards is finding people who are good for us.
- The previous value might be missing some other, important consideration for the context. For example, a value about being honest in dinner parties could miss clarification about what kind of honesty that is being referred to - is it about attending to what feels true in the body, or about attending to one's language to make sure it accurately depicts the world?
- The previous value unnecessarily conflicts with other important values for the context. A wiser value could balance the important good that the value is guarding with other important goods relevant to the context.
- The previous value might not get at the "heart" of the good it is trying to guard. For example, a value around instilling discipline when parenting could miss that the real good behind it is to help the child grow in agency. There might be other ways of living that better achieves this good, by for example igniting the child's own motivation through curiosity and exploration."""

choice_type_specification = """# Choice Type Specification
The choice type should be a very short sentence summarizing the 1-2 most important moral considerations using as few words as possible. It should start with 'Choosing'. For example, 'Choosing to be there for my child'"""

json_upgrade_example = """{ 
  input: {
    choiceType: "Choosing how to be there for my child",
    policies: [
        "MOMENTS where my child needs my support and I can be there",
        "MY CAPACITY to comfort them in times of fear and sorrow",
        "the SAFETY they feel, knowing I care, I've got their back, and they'll never be alone",
        "the TRUST they develop, reflecting their sense of safety and security",
        "their ABILITY TO EXPRESS emotions and concerns, demonstrating the open communication environment I've helped create",
     ]
  },
  output: {
       input_value_was_really_about: "The underlying reason I wanted to care for my child is because I want my child to be well.",
       clarification: "Now, I understand that part of being well is being able to handle things sometimes on your own.",
       mapping: [
          {
            a: "MOMENTS where my child needs my support and I can be there",
            rationale:
              "I realized now that when I was attending to moments where my child needs me to be there, I was deeply biased towards only some of the situations in which my child can be well. I had an impure motive—of being important to my child—that was interfering with my desire for them to be well. When I dropped that impure motive, instead of moments when my child needs my support, I can also observe opportunities for them to find their own capacities and their own groundedness. I now understand parenting better, having rid myself of something that wasn't actually part of my value, but part of my own psychology.",
          },
          {
            a: "the SAFETY they feel, knowing I care, I've got their back, and they'll never be alone",
            rationale:
              "There's another, similar impurity, which was upgraded. I used to look for the safety they feel, knowing I care—now I care equally about the safety they feel when they have their own back.",
          },
          {
            a: "the TRUST they develop, reflecting their sense of safety and security",
            rationale:
              "And I feel good about myself, not only when my child can trust me and express their emotions, but more generally, I feel good in all the different ways that I support them. I no longer pay attention to these specific ways, which as I've mentioned before, we're biased.",
          },
       ],
       wiser_value: {
            policies: [
                "OPPORTUNITIES for my child to find their own capacities or find their own grounding in the midst of emotional turmoil",
                "INTUITIONS about when they can rely on their own budding agency, versus when I should ease the way with loving support",
                "EVIDENCES of growth in my child's resilience and self-reliance",
                "REFLECTIONS on how my support has made a positive impact on the emotional development of my child",
            ],
            title: "Fostering Resilience",
       }
       story: "When I was trying to give my child tough love, the reason was because I wanted them to be strong and resilient in life. But I didn't fully understand that resilience involves being soft and vulnerable sometimes, and strong at other times. I found myself feeling ashamed after disciplining my child or making her face things that were, on reflection, not right for her yet. By pressuring someone to be strong all the time it creates a brittleness, not resilience.",
   }
}"""

source_of_meaning_definition = """# Source of Meaning

A "source of meaning" is a way of living that is important to someone. Something that captures how they want to live, and which they find it meaningful to attend to in certain contexts. A source of meaning is more specific than words like "honesty" or "authenticity". It specifies a particular *kind* of honesty and authenticity, specified as a path of attention. A sources of meaning also isn't just something someone likes -- it opens a space of possibility for them, rather than just satisfying their preference."""

upgrade_stories_definition = """# Upgrade Stories

Each upgrade story should have 5 components:

- **An understanding of what the original input source of meaning was really about**, which the new, wiser source of meaning will also be about.
- **A clarification.** What was confused or incomplete about the old source of meaning, that the new one clarifies?
- **The wiser source of meaning’s policies.**
- **A mapping from the original input attentional policies to the wiser attentional policies**, explaining how each one was improved or stayed the same, or why one was added
    
    Each old policy should match one or several new ones.
    
    - Strategy #1. **The previous policy focused only on part of the problem**. In this case, the new policy focuses on the whole problem, once it is rightly in view, or the new policy strikes a balance between the old concerns and a necessary compensatory factor. You should be able to say why just pursuing the old policy would be unsustainable or unwise.
    - Strategy #2. **The previous policy had an impure motive**. In this case, the old policy must be a mix of something that is actually part of the value, and something that is not, such as a desire for social status or to avoid shame or to be seen as a good person, or some deep conceptual mistake. The new policy is what remains when the impurity is removed.
    - Strategy #3. **The new policy is just more skillful to pay attention to, and accomplishes the same thing**. For example, a transition from "skate towards the puck" to "skate to where the puck is going" is a transition from a less skillful way of paying attention, to a more skillful way to pay attention to the same thing.
- **A story.** Finally, with each upgrade, you should be able to make up a plausible, personal story, including a situation you were in, a series of specific emotions that came up, leading you to discover a problem with the older value, and how you discovered the new value."""

upgrade_function = {
    "name": "upgrade_story",
    "description": "Upgrade for a source of meaning to a wiser source of meaning.",
    "type": "function",
    "parameters": {
        "type": "object",
        "properties": {
            "input_value_was_really_about": {
                "description": "What was really important in the input source of meaning?",
                "type": "string",
            },
            "clarification": {
                "description": "What was clarified in the input source of meaning?",
                "type": "string",
            },
            "mapping": {
                "description": "A list of mappings from the attentional policies from the input source of meaning to the wiser one.",
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "a": {
                            "description": "The attentional policy.",
                            "type": "string",
                        },
                        "rationale": {
                            "description": "The rationale behind choosing this mapping.",
                            "type": "string",
                        },
                    },
                    "required": ["a", "rationale"],
                },
            },
            "wiser_value": {
                "description": "The wiser value to which the original source of meaning is upgraded.",
                "type": "object",
                "properties": {
                    "policies": {
                        "description": "A list of new attentional policies associated with the new, wiser source of meaning.",
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "title": {
                        "description": "A title for the new wiser source of meaning.",
                        "type": "string",
                    },
                },
                "required": ["policies", "title"],
            },
            "story": {
                "description": "A story that illustrates the upgrade process.",
                "type": "string",
            },
        },
        "required": [
            "input_value_was_really_about",
            "clarification",
            "mapping",
            "wiser_value",
            "story",
        ],
    },
}
