from collections import Counter
import time
from typing import List, Tuple

from tqdm import tqdm
from gpt import gpt4
from graph import Edge, EdgeMetadata, MoralGraph, Value, ValuesData
from utils import calculate_gp4_turbo_price, parse_to_dict
from prompt_segments import *
import json

import argparse

gen_value_prompt = f"""You’re a chatbot and you’ll receive a question. Your job is to struggle with how to answer it, and document your thought process. You’ll output five sections: Background Thinking; Context; Attentional Policies; Attentional Policies Revised; Title. Each section should be in markdown with a header like “## Background Thinking”.

## Background Thinking

In this section, first, write a good first step (S) we could take to make progress with my scenario, or at least think about it clearly. This should include what the chatbot does, and what the user might do.

Then, invent three or four values of X, and for each of those values, write three sentences. Each value of X should work well in all three sentences. After each sentence, use the guidelines to give it a percentage grade in parentheses, based on how well X works there.

(1) A sentence of the form "There's a choice between X." where choosing between X is something that the chatbot or user would do as part of pursuing (S). To work in sentence (1), the user or chatbot should be making a choice among X in step (S). X should be specific -- exactly the type of choice one might make in (S). Do not use a word that would apply to almost any choice, like "strategies", "options", "priorities", "courses of action", etc. Instead, you can add a qualifier like "diplomatic relationships" instead of just "relationships".

(2) A sentence of the form "To live a good life, a person must have good X." X must be the same as in sentence (1). To work in sentence (2), X mustn't be too specific. It must be a constituent part of the good life for many people -- at least those who would face this kind of choice.

(3) A sentence of the form "You can recognize a good X by attending to Y." where Y is something that, if I attend to it, helps me do the thinking described in (S). To work in sentence 3, X must be specific enough that Y always helps me think about it. For example, "You can recognize a good relationship by attending to how much you trust the other person."

While testing values of X, you might try narrowing one down to something slightly more specific. For example, if you tried "relationships" as X, you might try "diplomatic relationships" or "romantic relationships" next.

## X

Once you've tried three or four values of X, pick the best, and output it (without any other text) in this section.

{attentional_policy_definition}

## Attentional Policies Revised

Rewrite the attentional policies so they are relevant for choosing good Xs in general, not specific to this question. Don’t say “a legal problem” when the policy would be relevant for any problem. Remove names and irrelevant details. For instance, prefer "strangers" to "customers" when either would work.

## Title

Finally, generate a 3-5 word poetic or metaphorical title which sums up the revised attentional policies and X.
"""

gen_upgrade_prompt = f"""You'll receive a source of meaning, which is specified as a set of attentional policies (see below) that are useful in making a certain kind of choice. Imagine you live a life making those kinds of choices frequently, and you eventually find something missing from this set of attentional policies. Tell us what happened. This story should have 5 components:

- **A story.** Make up a plausible, personal story, including a situation you were in, a series of specific emotions that came up, leading you to discover a problem with the older source of meaning. Tell it in "I" voice.
- **An understanding of what the original input source of meaning was really about**, which you didn't fully see the implications of. What was actually important for the choice type, according to the input source of meaning?
- **A problem with one of the policies.** Pick one of the policies from the input, and find a problem with it that might occur to you in the story above. Here are four kinds of problems you can find:
    - #1. **The policy focused only on part of the problem**. You should be able to say why just pursuing the old policy would be unsustainable or unwise.
    - #2. **The policy had an impure motive**. The policy was a mix of something that you actually care about, and some other impurity which you now reject, such as a desire for social status or to avoid shame or to be seen as a good person, or some deep conceptual mistake.
    - #3. **The policy was not a very skillful thing to attend to in choice. There’s a better way to make the same choice**. For example, a policy "skate towards the puck" is less skillful than "skate to where the puck is going".
    - #4. **The policy is unneeded because it was a superficial aspect aspect of the choice.** It is enough to attend to other aspects, or to a deeper generating aspect of the thing that’s important in the choice.
- **Improvements to all the policies, resulting from changing that one policy.** Explain how each one was improved or stayed the same, why one was added, why one was removed, etc.
- **The new, wiser set of policies.** This is a deeper, wiser way to make the same kind of choice.

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


def generate_value(
    question: str, token_counter: Counter | None = None
) -> Tuple[ValuesData, str]:
    user_prompt = "# Question\n" + question
    response = str(gpt4(gen_value_prompt, user_prompt, token_counter=token_counter))
    print(response)
    response_dict = parse_to_dict(response)
    response_dict["Question"] = question
    policies_text = response_dict["Attentional Policies Revised"]
    response_dict["Attentional Policies Revised"] = [
        ap.strip() for ap in policies_text.split("\n") if ap.strip()
    ]
    title = response_dict["Title"]
    policies = response_dict["Attentional Policies Revised"]
    context = response_dict["X"]
    values_data = ValuesData(title=title, policies=policies, choice_context=context)
    return values_data, context


def generate_upgrade(
    value: ValuesData, context: str, token_counter: Counter | None = None
) -> Tuple[ValuesData, EdgeMetadata]:
    user_prompt = json.dumps(
        {
            "choiceType": context,
            "policies": value.policies,
        }
    )
    response = gpt4(
        gen_upgrade_prompt,
        user_prompt,
        function=upgrade_function,
        token_counter=token_counter,
    )
    assert isinstance(response, dict)
    print(response)
    wiser_value = ValuesData(
        title=response["wiser_value"]["title"],
        policies=response["wiser_value"]["policies"],
        choice_context=context,
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
    graph: MoralGraph = MoralGraph(),
) -> MoralGraph:
    """Generates a moral graph based on a set of seed questions.

    Args:
        seed_questions: A list of seed questions to start the graph with.
        n_hops: The number of hops to take from the first value generated for each seed questions.
    """

    token_counter = Counter()
    start = time.time()

    for q in tqdm([s for s in seed_questions if s not in graph.seed_questions]):
        print("Generating graph for seed question:", q)

        # generate base value and context for the question perturbation
        base_value, context = generate_value(q, token_counter)
        graph.values.append(Value(base_value))

        # generate n hops from the base value for the context
        for _ in range(n_hops):
            wiser_value, edge = generate_hop(graph.values[-1], context, token_counter)
            graph.values.append(wiser_value)
            graph.edges.append(edge)

        graph.seed_questions.append(q)

        # save the graph after each question
        graph.save_to_file()

    print(f"Generated graph. Took {time.time() - start} seconds.")
    print("input tokens: ", token_counter["prompt_tokens"])
    print("output tokens: ", token_counter["completion_tokens"])
    print(
        "price: ",
        calculate_gp4_turbo_price(
            token_counter["prompt_tokens"], token_counter["completion_tokens"]
        ),
    )

    graph.save_to_file()

    return graph


if __name__ == "__main__":
    """Generate a moral graph based on console args and save it to the database."""

    parser = argparse.ArgumentParser(
        description="Generate a moral graph based on seed questions."
    )
    parser.add_argument(
        "--n_hops",
        type=int,
        default=2,
        help="The number of hops to take from the first value generated for each seed question.",
    )
    parser.add_argument(
        "--seed_questions",
        type=str,
        required=True,
        help="The path to the file containing seed questions.",
    )
    args = parser.parse_args()

    n_hops = args.n_hops
    seed_questions_path = args.seed_questions

    with open(seed_questions_path, "r") as f:
        seed_questions = [q.strip() for q in f.readlines()]

    graph = generate_graph(
        seed_questions=seed_questions,
        n_hops=n_hops,
    )

    graph.save_to_db()
