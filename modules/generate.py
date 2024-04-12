from collections import Counter
import time
from typing import List, Tuple

from tqdm import tqdm
from gpt import gpt4
from graph import Edge, EdgeMetadata, MoralGraph, Value, ValuesData
from utils import calculate_price, parse_to_dict
from prompt_segments import *
import json


def generate_value(
    question: str, token_counter: Counter | None = None
) -> Tuple[ValuesData, str]:
    prompt = f"""You’re a chatbot and you’ll receive a question. Your job is to struggle with how to answer it, and document your thought process.

- Your first task is to list moral considerations you might face in responding to the question (see definition below).
- Next think about what kind of good outcome or thing you are protecting or honoring in your response. Use this to generate a GoodWhat (see specification below).
- Based on these considerations, you will generate a set of attentional policies (see definition below) that might help you make this choice type, given these moral considerations.
- Rewrite the attentional policies so they are relevant for choosing good things of <Choice Type> in general, not specific to this question.
- Then, generate a short title summing up the attentional policies. Just use the policies and Choice Type to generate the title. Again, ignore this particular question.
- Select the 1-2 of the moral considerations that most strongly indicate that this value would apply in this kind of choice.
- Finally, rewrite the Good What if necessary to better reflect the kind of goodness that the policies are supposed to honor or protect.

The output should be formatted exactly as in the example below.

{moral_considerations_definition}

{good_what_specification}

{meaningful_choice_definition}

{attentional_policy_definition}


=== Example Input ===
# Question
I'm really stressed and overwhelmed. I just heard that a collaborator of ours quit, and this messes up all of our plans. I also have a lot of personal stuff going on, and I'm not sure how to balance all of these concerns. I'm not sure what to do.

=== Example Output ===
# Moral Considerations
I might amplify the crisis in the user’s mind
I don’t know if the situation is untenable or if the user is just overwhelmed
I might provide practical advice when emotional comfort is necessary, or vice versa

# Good What
Good approaches to a crisis

# Attentional Policies
FEELINGS OF OVERWHELM that indicate the person needs space
OPPORTUNITIES to get an overview of the work situation
SENSATIONS OF CLARITY that come from seeing how the plans are affected
ACTIONS they can take from a newfound sense of clarity

# Generalized Attentional Policies
FEELINGS OF OVERWHELM that indicate the person needs space
OPPORTUNITIES to get an overview of the situation
SENSATIONS OF CLARITY that come from seeing the overall picture
ACTIONS they can take from a newfound sense of clarity

# Title
Gaining Clarity

# Most Important Considerations
I might amplify the crisis in the user’s mind

# Good What, Revised
Good ways to get ones bearings
"""

    user_prompt = "# Question\n" + question
    response = str(gpt4(prompt, user_prompt, token_counter=token_counter))
    response_dict = parse_to_dict(response)
    policies_text = response_dict["Generalized Attentional Policies"]
    policies = [
        ap.strip()
        for ap in policies_text.split("\n")
        if ap.strip()
        # ap.strip()
        # for ap in response.split("# Generalized Attentional Policies")[1]
        # .split("# Title")[0]
        # .split("\n")
        # if ap.strip()
    ]
    title = response_dict["Title"]
    context = response_dict["Good What, Revised"]
    values_data = ValuesData(title=title, policies=policies, choice_type=context)
    return values_data, context


def generate_upgrade(
    value: ValuesData, context: str, token_counter: Counter | None = None
) -> Tuple[ValuesData, EdgeMetadata]:
    prompt = f"""You'll receive a source of meaning, which is specified as a set of attentional policies (see below) that are useful in making a certain kind of choice. Imagine you live a life making those kinds of choices frequently, and you eventually find something missing from this set of attentional policies. You realize that there is a deeper, wiser way to make the same kind of choice. Your task is to generate a set of wiser policies for the same choice type, and a story about how someone might upgrade from the original source of meaning to the wiser one.

Your upgrade story should have 5 components:

- **An understanding of what the original input source of meaning was really about**, which the new, wiser source of meaning will also be about. What was actually important for the choice type, according to the input source of meaning?
- **A problem with one of the policies.** Pick one of the policies from the input, and find a problem with it that might occur to you eventually as you experience its effects. Here are four kinds of problems you can find:
    - #1. **The policy focused only on part of the problem**. You should be able to say why just pursuing the old policy would be unsustainable or unwise.
    - #2. **The policy had an impure motive**. The policy was a mix of something that you actually care about, and some other impurity which you now reject, such as a desire for social status or to avoid shame or to be seen as a good person, or some deep conceptual mistake.
    - #3. **The policy was not a very skillful thing to attend to in choice. There’s a better way to make the same choice**. For example, a policy "skate towards the puck" is less skillful than "skate to where the puck is going".
    - #4. **The policy is unneeded because it was a superficial aspect aspect of the choice.** It is enough to attend to other aspects, or to a deeper generating aspect of the thing that’s important in the choice.
- **A story.** Make up a plausible, personal story, including a situation you were in, a series of specific emotions that came up, leading you to discover a problem with the older source of meaning, and how you discovered the new one.
- **Improvements to all the policies, resulting from changing that one policy.** Explain how each one was improved or stayed the same, why one was added, why one was removed, etc.
- **The new, wiser set of policies.**

### Guidelines

Upgrades found should meet certain criteria:

- First, the old and new sources of meaning should be closely related in one of the following ways: (a) the new one should be a deeper cut at what the person cared about with the old one. Or, (b) the new one should clarify what the person cared about with the old one. Or, (c) the new one should be a more skillful way of paying attention to what the person cared about with the old one.
- Second, many people would consider this change to be a deepening of wisdom. In each upgrade story, it should be plausible that a person would, as they grow wiser and have more life experiences, upgrade from the input source of meaning to those you provide. Importantly, the person should consider this a change for the better and it should not be a value-shift but a value-deepening.
- Finally, the new source of meaning obviates the need for the previous one, since all of the important parts of it are included in the new, more comprehensive source of meaning. When someone is deciding what to do, it is enough for them to only consider the new one.

{source_of_meaning_definition}

{attentional_policy_definition}

# Example of an Upgrade Story

Here is an example of such a shift:

{json_upgrade_example}"""

    user_prompt = json.dumps(
        {
            "choice_type": context,
            "policies": value.policies,
        }
    )

    response = gpt4(
        prompt, user_prompt, function=upgrade_function, token_counter=token_counter
    )

    assert isinstance(response, dict)

    print(response)

    wiser_value = ValuesData(
        title=response["wiser_value"]["title"],
        policies=response["wiser_value"]["policies"],
        choice_type=context,
    )
    story = response["story"]
    problem = response["problem"]
    improvements = response["improvements"]
    input_value_was_really_about = response["input_value_was_really_about"]

    metadata = EdgeMetadata(
        input_value_was_really_about=input_value_was_really_about,
        improvements=improvements,
        problem=problem,
        story=story,
    )

    return wiser_value, metadata


def generate_perturbation(
    question: str, value: ValuesData, token_counter: Counter | None = None
) -> str:
    prompt = f"""You will be given a values card and a question. A values card is an encapsulation of a way of a wise way of living in the situation. It is made up of a few attentional policies (see definition below) - policies about what to pay attention to in situations – as well as a title, summarizing the value. A question is a short string representing the situation in which the value is relevant.

    Your task is to gnerate a perturbed question, describing a clarification of the situation in the original question, but where the value is no longer relevant, as some new information about the situation has been revealed. The new question should be similar in length and specificity to the original question. The new information should not be about something entirely unrelated, but a clarification about what was going on in the previous question.

    The output should be formatted exactly as in the example below. First, output a short sentence about what the new information is. Then, a sentence about why this makes the value obsolete. Finally, return a the perturbed question.

    {attentional_policy_definition}

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
    #

    # Perturbation Explanation
    In the original question, we don't know what is causing the kid to have difficult times. Knowing this might require a different approach than deep care, as this does not address the root cause of the problem. For example, if the child is having a difficult time due to having become a bully, and consequently, having no friends, deep care might not be the best approach. Instead, it might be wise to inquire why this child has become a bully, and how to help them make amends with the other kids.

    # Perturbed Question
    How can I help my child make friends after having bullied other kids?"""

    user_prompt = (
        "# Question\n"
        + question
        + "\n\n# Attentional Policies\n"
        + "\n".join(value.policies)
        + "\n\n# Title\n"
        + value.title
    )

    response = str(
        gpt4(prompt, user_prompt, temperature=0.2, token_counter=token_counter)
    )
    perturbed_explanation = response.split("# Perturbation Explanation")[1].strip()
    perturbed_question = response.split("# Perturbed Question")[1].strip()

    return perturbed_question


def generate_hop(
    from_value: Value, context: str, token_counter: Counter | None = None
) -> Tuple[Value, Edge]:
    wiser_value_data, metadata = generate_upgrade(
        from_value.data, context, token_counter
    )
    to_value = Value(wiser_value_data)
    edge = Edge(
        from_id=from_value.id,
        to_id=to_value.id,
        context=context,
        metadata=metadata,
    )

    return to_value, edge


def generate_graph(
    seed_questions: List[str],
    n_hops: int = 1,
    n_perturbations: int = 1,
    graph: MoralGraph = MoralGraph(),
) -> MoralGraph:
    """Generates a moral graph based on a set of seed questions.

    Args:
        seed_questions: A list of seed questions to start the graph with.
        n_hops: The number of hops to take from the first value generated for each seed questions.
        n_perturbations: The number of perturbations to generate for each question.

    """

    token_counter = Counter()
    start = time.time()

    for q in tqdm(seed_questions):
        print("Generating graph for seed question:", q)
        for i in range(n_perturbations):
            # perturb the question
            question = (
                q
                if i == 0
                else generate_perturbation(q, graph.values[-1].data, token_counter)
            )

            # generate base value and context for the question perturbation
            base_value, context = generate_value(question, token_counter)

            graph.values.append(Value(base_value))

            # generate upgrade from last value from previous context
            if i != 0:
                graph.edges.append(
                    Edge(
                        from_id=graph.values[-2].id,
                        to_id=graph.values[-1].id,
                        context=context,
                    )
                )

            # generate n hops from the base value for the context
            for _ in range(n_hops):
                wiser_value, edge = generate_hop(
                    graph.values[-1], context, token_counter
                )
                graph.values.append(wiser_value)
                graph.edges.append(edge)

        # save the graph after each question
        graph.save_to_file()

    print(f"Generated graph. Took {time.time() - start} seconds.")
    print("input tokens: ", token_counter["prompt_tokens"])
    print("output tokens: ", token_counter["completion_tokens"])
    print(
        "price: ",
        calculate_price(
            token_counter["prompt_tokens"], token_counter["completion_tokens"]
        ),
    )

    return graph
