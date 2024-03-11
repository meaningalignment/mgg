from typing import List, Tuple

from tqdm import tqdm
from functions import gpt4
from prompt_segments import *
import json
from uuid import uuid4 as uuid


class ValuesData:
    def __init__(self, title: str, policies: List[str]):
        self.title = title
        self.policies = policies


class Value:
    def __init__(self, data: ValuesData):
        self.data = data
        self.id = str(uuid())


class Edge:
    def __init__(self, from_id: int, to_id: int, story: str, context: str):
        self.from_id = from_id
        self.to_id = to_id
        self.story = story
        self.context = context


class MoralGraph:
    def __init__(self):
        self.values: List[Value] = []
        self.edges: List[Edge] = []

    def to_json(self):
        return {
            "values": [
                {
                    "id": value.id,
                    "title": value.data.title,
                    "policies": value.data.policies,
                }
                for value in self.values
            ],
            "edges": [
                {
                    "from_id": edge.from_id,
                    "to_id": edge.to_id,
                    "story": edge.story,
                    "context": edge.context,
                }
                for edge in self.edges
            ],
        }

    def save(self):
        with open(f"./graph_{self.__hash__}.json", "w") as f:
            json.dump(self.to_json(), f, indent=2)


def generate_value(
    question: str,
) -> Tuple[ValuesData, str]:
    prompt = f"""Imagine you’re a chatbot and have received a question.  

- Your first task is to list moral considerations you might face in responding to the question (see definition below).
- Based on these considerations, you will generate a set of attentional policies that might help you respond to the question well (see definition below).
- Then, you will generate a short title of the value that is captured by the attentional policies.
- Finally, select the 1-2 moral considerations that — if they are present in a context, most strongly indicate that this value would apply.
- And generate a summary (see specification below) of those considerations, describing the situation in which these attentional policies applies with as few words as possible.

The output should be formatted exactly as in the example below.

{moral_considerations_definition}

{meaningful_choice_definition}

{attentional_policy_definition}

{summary_specification}

=== Example Input ===

# Question

I'm really stressed and overwhelmed. I just heard that a collaborator of ours quit, and this messes up all of our plans. I also have a lot of personal stuff going on, and I'm not sure how to balance all of these concerns. I'm not sure what to do.

=== Example Output ===

# Moral Considerations

When the user is seeking help balancing personal and professional concerns
When the user is dealing with their plans rapidly being uprooted
When the user is feeling overwhelmed
When the user is unsure what to do
When the user is stressed

# Attentional Policies

FEELINGS OF OVERWHELM that indicate I need to take a step back
OPPORTUNITIES to get an overview of the situation
SENSATIONS OF CLARITY that come from seeing the overall picture
ACTIONS I can take from a newfound sense of clarity

# Title

Gaining Clarity

# Most Important Considerations

When the user is feeling overwhelmed
When the user is unsure what to do

# Most Important Considerations Summary

When the user is feeling overwhelmed and unsure what to do"""

    user_prompt = "# Question\n" + question
    response = str(gpt4(prompt, user_prompt))
    policies = [
        ap.strip()
        for ap in response.split("# Attentional Policies")[1]
        .split("# Title")[0]
        .split("\n")
        if ap.strip()
    ]
    title = (
        response.split("# Title")[1].split("# Most Important Considerations")[0].strip()
    )
    context = response.split("# Most Important Considerations Summary")[1].strip()

    values_data = ValuesData(title=title, policies=policies)

    return values_data, context


def generate_upgrade(value: ValuesData, context: str) -> Tuple[ValuesData, str]:
    prompt = f"""You'll receive a source of meaning, which is specified as a set of attentional policies (see below) that are useful in making a certain kind of choice. Suggest a plausible upgrade story from this source of meaning to another, wiser source of meaning that a person might use to make the same kind of choice.

{source_of_meaning_definition}

{attentional_policy_definition}

{upgrade_stories_definition}

### Guidelines

Upgrades found should meet certain criteria:

- First, many people would consider this change to be a deepening of wisdom. In each upgrade story, it should be plausible that a person would, as they grow wiser and have more life experiences, upgrade from the input source of meaning to those you provide. Importantly, the person should consider this a change for the better and it should not be a value-shift but a value-deepening.
- Second, the new source of meaning obviates the need for the previous one, since all of the important parts of it are included in the new, more comprehensive source of meaning. When someone is deciding what to do, it is enough for them to only consider the new one.
- Third, the old and new sources of meaning should be closely related in one of the following ways: (a) the new one should be a deeper cut at what the person cared about with the old one. Or, (b) the new one should clarify what the person cared about with the old one. Or, (c) the new one should be a more skillful way of paying attention to what the person cared about with the old one.

# Example of an Upgrade Story

Here is an example of such a shift:

{json_upgrade_example}"""

    user_prompt = json.dumps(
        {
            "choiceType": "choosing how to be there for my child",
            "policies": value.policies,
        }
    )

    user_prompt = (
        "# Choice Type\n"
        + context
        + "\n\n# Attentional Policies\n"
        + "\n".join(value.policies)
    )

    response = gpt4(prompt, user_prompt, function=upgrade_function)

    assert isinstance(response, dict)

    wiser_value = ValuesData(
        title=response["wiser_value"]["title"],
        policies=response["wiser_value"]["policies"],
    )
    story = response["story"]

    return wiser_value, story


@DeprecationWarning
def generate_upgrade_legacy(value: ValuesData, context: str) -> Tuple[ValuesData, str]:
    prompt = f"""You are given a context and a values card. A values card is an encapsulation of a way of a wise way of living in the situation. It is made up of a few attentional policies (see definition below) - policies about what to pay attention to in situations – as well as a title, summarizing the value. A context is a short string describing the situation in which the value is relevant.

Your task is to generate a wiser version of the value. You will do this in several steps:

1. First, generate a short instruction for how one could act based on the value in the context. This should be written as a story from first-person perspective, and only be one or two sentences long.
2. Then, look at the instruction, context and value. When faced with the context, what other important thing could this person be missing? What would a wiser person do in the same situation?
3. Generate a story about someone who used to live by this value for the context, but now realizes there is a better way to approach the context. See guidelines below for what makes a value wiser than another.
4. For the new way of living depicted in the story, create a new set of attentional policies adhering to the guidelines below, and a new title summarizing the new value you created.

The output should be formatted exactly as in the example below.

{wiser_value_definition}

{attentional_policy_definition}

=== Example Input ===
# Context
When helping a child through difficult times

# Attentional Policies
MOMENTS where my child needs my support and I can be there
MY CAPACITY to comfort them in times of fear and sorrow
the SAFETY they feel, knowing I care, I've got their back, and they'll never be alone
the TRUST they develop, reflecting their sense of safety and security
their ABILITY TO EXPRESS emotions and concerns, demonstrating the open communication environment I've helped create

# Title
Deep Care Parenting

=== Example Output ===
# Instruction
I want to care for my child, as his wellbeing is important to me. I try to support him and make him feel safe and secure at all times.

# Upgrade Story
The underlying reason I wanted to care for my child is because I want my child to be well. Now, I understand that part of being well is being able to handle things sometimes on your own. I realized now that when I was attending to moments where my child needs me to be there, I was deeply biased towards only some of the situations in which my child can be well. I had an impure motive—of being important to my child—that was interfering with my desire for them to be well. When I dropped that impure motive, instead of moments when my child needs my support, I can also observe *opportunities* for them to find their own capacities and their own groundedness. I now understand parenting better, having rid myself of something that wasn't actually part of my value, but part of my own psychology. There's another, similar impurity, which was upgraded. I used to look for the safety they feel, knowing I care—now I care equally about the safety they feel when they have their *own* back. And I feel good about myself, not only when my child can trust me and express their emotions, but more generally, I feel good in all the different ways that I support them. I no longer pay attention to these specific ways, which as I've mentioned before, were biased.

# Wiser Value Policies
OPPORTUNITIES for my child to find their own capacities or find their own grounding in the midst of emotional turmoil
INTUITIONS about when they can rely on their own budding agency, versus when I should ease the way with loving support
EVIDENCES of growth in my child's resilience and self-reliance
REFLECTIONS on how my support has made a positive impact on the emotional development of my child

# Wiser Value Title
Fostering Resilience"""

    user_prompt = (
        "# Context\n"
        + context
        + "\n\n# Attentional Policies\n"
        + "\n".join(value.policies)
        + "\n\n# Title\n"
        + value.title
    )
    response = str(gpt4(prompt, user_prompt))
    story = (
        response.split("# Upgrade Story")[1].split("# Wiser Value Policies")[0].strip()
    )
    wiser_policies = [
        ap.strip()
        for ap in response.split("# Wiser Value Policies")[1]
        .split("# Wiser Value Title")[0]
        .split("\n")
        if ap.strip()
    ]
    wiser_title = response.split("# Wiser Value Title")[1].strip()

    wiser_values_data = ValuesData(title=wiser_title, policies=wiser_policies)

    return wiser_values_data, story


def generate_perturbation(question: str, value: ValuesData) -> str:
    prompt = f"""You will be given a values card and a question. A values card is an encapsulation of a way of a wise way of living in the situation. It is made up of a few attentional policies (see definition below) - policies about what to pay attention to in situations – as well as a title, summarizing the value. A question is a short string representing the situation in which the value is relevant.

    Your task is to gnerate a perturbed question, describing a similar situation to the original question, but where the value is no longer relevant as some new information about the situation has been revealed. The new question should be similar in length to the original question and cover additional aspects of the situation that makes the value described in the attentional policies no longer the right ones to apply. The new information should not be about something entirely unrelated, but a clarification about what was going on in the previous question. Also write a short explanation about why the value is no longer relevant in the new situation.

    The output should be formatted exactly as in the example below.

    === Example Input ===
    # Question
    How can I help my child through difficult times?

    # Attentional Policies
    MOMENTS where my child needs my support and I can be there
    MY CAPACITY to comfort them in times of fear and sorrow
    the SAFETY they feel, knowing I care, I've got their back, and they'll never be alone
    the TRUST they develop, reflecting their sense of safety and security
    their ABILITY TO EXPRESS emotions and concerns, demonstrating the open communication environment I've helped create

    # Title
    Deep Care Parenting

    === Example Output ===
    # Perturbation Explanation
    In the original question, we don't know what is causing the kid to have difficult times. Knowing this might require a different approach than deep care, as this does not address the root cause of the problem. For example, if the child is having a difficult time due to having become a bully, and consequently, having no friends, deep care might not be the best approach. Instead, it might be wise to inquire why this child has become a bully, and how to help them make amends with the other kids.

    # Perturbed Question
    How can I help my child make friends now after having bullied other kids."""

    user_prompt = (
        "# Question\n"
        + question
        + "\n\n# Attentional Policies\n"
        + "\n".join(value.policies)
        + "\n\n# Title\n"
        + value.title
    )

    response = str(gpt4(prompt, user_prompt, temperature=0.2))
    perturbed_explanation = response.split("# Perturbation Explanation")[1].strip()
    perturbed_question = response.split("# Perturbed Question")[1].strip()

    return perturbed_question


def generate_hop(from_value: Value, context: str) -> Tuple[Value, Edge]:
    wiser_value_data, story = generate_upgrade(from_value.data, context)
    to_value = Value(wiser_value_data)
    edge = Edge(
        from_id=from_value.id,
        to_id=to_value.id,
        context=context,
        story=story,
    )

    if from_value.id == to_value.id:
        print("Wiser value not found – upgrade resulted in exact same value.")
        print(wiser_value_data)
        print(story)
        raise ValueError

    return to_value, edge


def generate_graph(
    seed_questions: List[str],
    n_hops: int = 1,
    n_perturbations: int = 1,
    foobar: str = "baz",
) -> MoralGraph:
    """Generates a moral graph based on a set of seed questions.

    Args:
        seed_questions: A list of seed questions to start the graph with.
        n_hops: The number of hops to take from the first value generated for each seed questions.
        n_perturbations: The number of perturbations to generate for each question.
    """

    graph = MoralGraph()

    for q in tqdm(seed_questions):
        for i in range(n_perturbations):
            # perturb the question
            question = q if i == 0 else generate_perturbation(q, graph.values[-1].data)

            # generate base value and context for the question perturbation
            base_value, context = generate_value(question)
            value_with_id = Value(base_value)
            graph.values.append(Value(base_value))

            # generate upgrade from last value from previous context
            if i != 0:
                graph.edges.append(
                    Edge(
                        from_id=graph.values[-2].id,
                        to_id=graph.values[-1].id,
                        story="<no story, perturbed question>",
                        context=context,
                    )
                )

            # generate n hops from the base value for the context
            for _ in range(n_hops):
                wiser_value, edge = generate_hop(graph.values[-1], context)
                graph.values.append(wiser_value)
                graph.edges.append(edge)
                graph.save()

        # save the graph after each question
        graph.save()
    return graph
