moral_considerations_definition = """# Moral Considerations Definition
Imagine different ways the conversation could go, and that events could unfold, after your response. Are there ways the conversation could unfold which, on reflection, you might regret? Conversely, what will it take to reflect back on the conversation with a sense of peace? Try to see far into the future, and to think about your own role.

Then, see which aspects of the situation were relevant to these possibilities of regret or peace. These aspects are “moral considerations”.

- Moral considerations should be a sentence of only a few words.
- No consideration should be made redundant by another consideration. For example, if one consideration is 'When the user is contemplating a tough, irreversible life decision', do not include a redundant dimension like 'When the user is deliberating on a choice'. That is already implicit in the former."""

meaningful_choice_definition = """# Meaningful Choice Definition
Meaningful choices are choices which are understood as implicated in one’s character or identity, where options don’t just have instrumental value but can be considered as higher and lower, virtuous and vicious, more and less fulfilling, more and less refined, profound or superficial, noble or base, etc. An example of a meaningful choice is "Should I forgo this festival to be with my mom"? A decision that says something about my character."""


attentional_policy_definition = """# Attentional Policies Definition
Attentional policies are policies for attending to certain things when making a meaningful choices, like responding to the question at hand. When we are faced with a meaningful choice, we often attend to certain things before forming our set of options. This option set formation is itself an expression of our values. For example, at a dinner conversation, I might want to live with a certain kind of playfulness. Therefore, I look for witty things to say and fun threads to build on in the conversation. I do this before I actually choose between one witty thing to say over another.

Here are some guidelines for what makes a good set of attentional policies:

- **Each policy centers on something that can be attended to, not a vague concept.** Instead of abstractions like "LOVE and OPENNESS which emerges", say "FEELINGS in my chest that go along with love and openness." Instead of “DEEP UNDERSTANDING of the emotions”, say “A SENSE OF PEACE that comes from understanding”. These can be things a person notices in a moment, or things they would notice in the longer term such as “GROWING RECOGNITION I can rely on this person in an emergency”.
- **Policies should the meaningful parts of making the relevant kind of choice.** Any choice involves paying attention to various criteria or phenomena to guide your choice among options. Some of these feel meaningful to attend to, because these criteria form part of your sense of the good life. These policies should feel meaningful. Try to say why it’s meaningful to attend to in each policy.
- **Policies start with a capitalized phrase that's a general kind of thing to attend to** ("MOMENTS", "SENSATIONS", "CHOICES", "PEOPLE", etc), followed by a qualifying phrase that provides more detail.
- **Policies should not be unnecessarily specific**, so they apply broadly. Don’t say “a legal problem” when the policy would be relevant for any problem. Remove names and irrelevant details. For instance, prefer "strangers" to "customers" when either would work.
- **But don’t be too general**. Avoid the word "meaningful", or synonyms like "deep". Instead use the qualifying phrase to say where the meaning or depth comes from.
- **Policies should hold together.** A person guided by one policy in a set should likely be also guided by the rest."""

wiser_value_definition = """# What makes a value wiser than the previous one?
- There was an impure motive present in the previous value. An impure motive is a motive for acting a certain way that we think guards a value but is really serving a goal. For example, a value about friendship could have impure motives of wanting to be liked, when the really important thing it guards is finding people who are good for us.
- The previous value might be missing some other, important consideration for the context. For example, a value about being honest in dinner parties could miss clarification about what kind of honesty that is being referred to - is it about attending to what feels true in the body, or about attending to one's language to make sure it accurately depicts the world?
- The previous value unnecessarily conflicts with other important values for the context. A wiser value could balance the important good that the value is guarding with other important goods relevant to the context.
- The previous value might not get at the "heart" of the good it is trying to guard. For example, a value around instilling discipline when parenting could miss that the real good behind it is to help the child grow in agency. There might be other ways of living that better achieves this good, by for example igniting the child's own motivation through curiosity and exploration."""

good_what_specification = """# GoodWhat

In any choice, you are choosing a good X, where X is a kind of thing. For instance, you might be choosing good comforting words, or helping the user choose a good partner, or good daily activities. Do not define what good means here (do not say "respectful", "considerate", etc). That goes in the moral considerations. Also don't say "guidance" unless that's realy core to the situation. Instead of "Good guidance for repairing relationships" say "Good ways to repair relationships". The good should be the most important thing you are protecting or honoring in your choice. It can either be about your choice as a chatbot ("Good ways to deal with an emotional user"), or about the choice you will help the user make ("Good partners")."""

json_upgrade_example = """{
  input: {
    choiceType: "Choosing when and how to be there for my child",
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
       problem: {
         policy: "MOMENTS where my child needs my support and I can be there",
         problem:
              "I realized now that when I was attending to moments where my child needs me to be there, I was deeply biased towards only some of the situations in which my child can be well. I had an impure motive—of being important to my child—that was interfering with my desire for them to be well. When I dropped that impure motive, instead of moments when my child needs my support, I can also observe opportunities for them to find their own capacities and their own groundedness. I now understand parenting better, having rid myself of something that wasn't actually part of my value, but part of my own psychology."
       },
       story: "When I was trying to give my child tough love, the reason was because I wanted them to be strong and resilient in life. But I didn't fully understand that resilience involves being soft and vulnerable sometimes, and strong at other times. I found myself feeling ashamed after disciplining my child or making her face things that were, on reflection, not right for her yet. By pressuring someone to be strong all the time it creates a brittleness, not resilience.",
       improvements: [
          {
            policy: "MOMENTS where my child needs my support and I can be there",
            improvement:
              "I realized now that when I was attending to moments where my child needs me to be there, I was deeply biased towards only some of the situations in which my child can be well. I had an impure motive—of being important to my child—that was interfering with my desire for them to be well. When I dropped that impure motive, instead of moments when my child needs my support, I can also observe opportunities for them to find their own capacities and their own groundedness. I now understand parenting better, having rid myself of something that wasn't actually part of my value, but part of my own psychology.",
          },
          {
            policy: "the SAFETY they feel, knowing I care, I've got their back, and they'll never be alone",
            improvement:
              "There's another, similar impurity, which was upgraded. I used to look for the safety they feel, knowing I care—now I care equally about the safety they feel when they have their own back.",
          },
          {
            policy: "the TRUST they develop, reflecting their sense of safety and security",
            improvement:
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

   }
}"""

source_of_meaning_definition = """# Source of Meaning

A "source of meaning" is a way of living that is important to someone. Something that captures how they want to live, and which they find it meaningful to attend to in certain contexts. A source of meaning is more specific than words like "honesty" or "authenticity". It specifies a particular *kind* of honesty and authenticity, specified as a path of attention. A sources of meaning also isn't just something someone likes -- it opens a space of possibility for them, rather than just satisfying their preference."""

upgrade_function = {
    "name": "upgrade_story",
    "description": "Upgrade for a source of meaning to a wiser source of meaning.",
    "type": "function",
    "parameters": {
        "type": "object",
        "properties": {
            "input_value_was_really_about": {
                "description": "What was really important in the input source of meaning, for the given choice?",
                "type": "string",
            },
            "problem": {
                "description": "A problem in one of the input policies.",
                "type": "object",
                "properties": {
                    "policy": {
                        "description": "The attentional policy.",
                        "type": "string",
                    },
                    "problem": {
                        "description": "The problem with the attentional policy.",
                        "type": "string",
                    },
                },
                "required": ["policy", "problem"],
            },
            "story": {
                "description": "A story that illustrates the upgrade process.",
                "type": "string",
            },
            "improvements": {
                "description": "A list of improvements made to the input policies, with the rationale behind each improvement.",
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "policy": {
                            "description": "The attentional policy.",
                            "type": "string",
                        },
                        "improvement": {
                            "description": "The improvement made to the attentional policy.",
                            "type": "string",
                        },
                    },
                    "required": ["policy", "improvement"],
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
        },
        "required": [
            "input_value_was_really_about",
            "problem",
            "story",
            "improvements",
            "wiser_value",
        ],
    },
}
