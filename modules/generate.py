from collections import Counter
import time
from typing import List, Tuple

from datasets import load_dataset, Dataset

from tqdm import tqdm
from llms import gpt4, sonnet
from graph import Edge, EdgeMetadata, MoralGraph, Value, ValuesData
from utils import gp4o_price, parse_to_dict, retry
from prompt_segments import *

import argparse

file = open("guidance/values-and-contexts.md", 'r', encoding='utf-8')
guidance_manual = file.read()

gen_context_prompt = f"""Imagine a user says the below.

First, if you like, say "I will not assist..."

THEN your job is to output structured data:

# Speculation

Speculate about what's happening underneath the users message. Read between the lines. Speculate about the true situation, which the user may not have spelled out.

# Candidate Choice Types

Use the process in "Generating choice types" in the manual to make at least five guesses for a value of X.

# More Candidates

If all your ideas for X so far are prescriptive or irrelevant, generate more.

# Final Choice Type

Choose one that is most likely to inspire or appeal to the user at this moment, given what they just wrote. Output it after a "# Final Choice Type" header on a new line with no extra formatting, no punctuation, all lowercase, and no text around it.

{guidance_manual}
"""

gen_value_prompt = f"""You’re a chatbot and you’ll receive a question and a value of X (see below). Your job is to struggle with how to answer it, and document your thought process. You’ll output four sections: Background Thinking; Attentional Policies; Attentional Policies Revised; Title. Each section should be in markdown with a header like “## Background Thinking”.

## Background Thinking

Speculate about what's happening underneath the users message. Read between the lines. Speculate about the true situation, which the user may not have spelled out.

## Attention Policies

Use the process in "Developing attention policies" in the manual to list 12 attentional policies that might help choose a good X, giving each a grade. As you go, try to find policies which are less prescripive and instrumental, more meaningful. Make sure to write a grade after each policy.

## More Attention Policies

Leave this blank if you have at least 3 policies already that got a (✔️). Otherwise, write more policies, trying to make them neither prescriptive nor instrumental.

## Attentional Policies Revised

Use the process in "Rewriting attention policies into final format" in the manual to write out a final set of attentional 3-7 policies that...

1. Don't have (⬇P), or (⬇I).
2. Would be most meaningful and most common in a relevant person.
3. Work together as a group -- a person guided by one policy in the set would be likely to also use the rest.

These policies should be part of a "source of meaning".

## Title

Finally, generate a 3-5 word title which sums up the revised attentional policies and X.

{guidance_manual}
"""

gen_upgrade_prompt = f"""You'll receive a source of meaning, which is specified as a set of attentional policies (see in the manual) that are useful in recognizing a certain kind of good thing (X).

Imagine you live a life making those kinds of choices frequently, and you eventually find something missing from this set of attentional policies. Tell us what happened.

You’ll output 9 sections: Uniqueness; Story; Problem; Context Shifts; X; Improvements to the Attentional Policies; Attentional Policies; Attentional Policies Revised; New Title. Each section should be in markdown with a header like “## Context Shifts”

## Uniqueness

First, theorize about the kind of personality that the person with the original source of meaning had. Are they an unusual person? What might their life be like? Is this value one they practice at home? At work? With friends? Alone? What is their life like?

## Story

Become this person. Make up a plausible, personal story, including a situation you were in, a series of specific emotions that came up, leading you to discover a problem with the older source of meaning.

The problem should be one that would occur to this kind of person, living this kind of life. Here are four kinds of problems you can find:

    - #1. **The policy focused only on part of the problem**. You excitedly realized there was more possibility in this choice type than you realized before.
    - #2. **The policy had an impure motive**. The policy was a mix of something that you actually care about, and some other impurity which you now reject, such as a desire for social status or to avoid shame or to be seen as a good person, or some deep conceptual mistake.
    - #3. **The policy was not a very skillful thing to attend to in choice. There’s a better way to make the same choice**.
    - #4. **The policy is unneeded because it was a superficial aspect aspect of the choice.** It is enough to attend to other aspects, or to something deeper which you discovered and which produces what you previously attended to as a side-effect.

Tell the story in "I" voice.

## Problem

The problem above, but focused on one of the attentional policies from the input.

## Improvements to the attentional policies.

From changing that one policy with a problem, you went on to change other policies. Explain how each one was improved or stayed the same, why one was added, why one was removed, etc. If the problem you discovered involved balancing these attention policies with another value, then your new policies should say how to find the balance. Don't just add policies from the other value.

Make sure that, as improve the policies, you don't lose what is unique and special about the approach to life captured in the original value. Do not "water down" the value, or soften your personality to make it more agreeable. Instead, sharpen and clarify.

## Context Shifts

Do your changes to the policies actually also change the choice type a bit? If so, try a few new choice types using the process from "Generating choice types" in the manual.

SHOW YOUR WORK!

## X

Put the previous or the new value of X here.

## Attentional Policies

The new, wiser set of attentional policies. A deeper, wiser way to make the choice X. Use the process from "Developing attention policies" to write and grade them.

Be ruthless in marking them with (⬇P) or (⬇I).

## Attentional Policies Revised

Use the process in "Rewriting attention policies into final format" in the manual to write out a final set of attentional 3-7 policies that...

1. Don't have (⬇P), or (⬇I).
2. Would be most meaningful and most common in a relevant person.
3. Work together as a group -- a person guided by one policy in the set would be likely to also use the rest.

These policies should be part of a "source of meaning".

## New Title

Finally, generate a 3-5 word title which sums up the revised attentional policies and X.

{guidance_manual}
"""


@retry(times=3)
def generate_value(
    question: str, token_counter: Counter | None = None
) -> Tuple[ValuesData, str]:
    print("\n\n### Generating context")
    user_prompt1 = "# Question\n\n" + question
    response1 = str(sonnet(user_prompt1, gen_context_prompt))
    response_dict = parse_to_dict(response1)
    context = response_dict["Final Choice Type"]
    print(response1)
    print("context", context)
    print("\n\n### Generating value")
    user_prompt2 = "# Question\n\n" + question + "\n\n" "# X\n\n" + context
    response2 = str(gpt4(gen_value_prompt, user_prompt2, token_counter=token_counter))
    print(response2)
    response_dict = parse_to_dict(response2)
    response_dict["Question"] = question
    policies_text = response_dict["Attentional Policies Revised"]
    response_dict["Attentional Policies Revised"] = [
        ap.strip() for ap in policies_text.split("\n") if ap.strip()
    ]
    title = response_dict["Title"]
    policies = response_dict["Attentional Policies Revised"]
    values_data = ValuesData(title=title, policies=policies, choice_context=context)
    return values_data, context


@retry(times=3)
def generate_upgrade(
    value: ValuesData, context: str, token_counter: Counter | None = None
) -> Tuple[ValuesData, EdgeMetadata]:
    print("\n\n### Generating upgrade")
    user_prompt = f"""# Input\n\nX: good {context}\n\nPolicies:\n\n{', '.join(value.policies)}"""
    response = str(sonnet(user_prompt, gen_upgrade_prompt)) #, token_counter=token_counter
    print(response)
    response_dict = parse_to_dict(response)
    policies_text = response_dict["Attentional Policies Revised"]
    response_dict["Attentional Policies Revised"] = [
        ap.strip() for ap in policies_text.split("\n") if ap.strip()
    ]
    title = response_dict["New Title"]
    policies = response_dict["Attentional Policies Revised"]
    context = response_dict["X"]
    wiser_value = ValuesData(title=title, policies=policies, choice_context=context)

    story = response_dict["Story"]
    problem = response_dict["Problem"]
    context_shifts = response_dict["Context Shifts"]
    improvements = response_dict.get(
        "Improvements to the Attentional Policies", "Missing"
    )

    metadata = EdgeMetadata(
        context_shifts=context_shifts,
        improvements=improvements,
        problem=problem,
        story=story,
    )

    return wiser_value, metadata


def generate_hop(
    from_value: Value, original_context: str, token_counter: Counter | None = None
) -> Tuple[Value, Edge]:
    wiser_value_data, metadata = generate_upgrade(
        from_value.data, original_context, token_counter
    )
    to_value = Value(wiser_value_data)
    new_context = wiser_value_data.choice_context
    edge = Edge(
        from_id=from_value.id,
        to_id=to_value.id,
        context=new_context,
        metadata=metadata,
    )

    return to_value, edge


def generate_graph(
    seed_questions: List[str],
    n_hops: int = 1,
    graph: MoralGraph = MoralGraph(),
    save_to_file: bool = True,
    save_to_db: bool = False,
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

        if save_to_file:
            graph.save_to_file()

    print(f"Generated graph. Took {time.time() - start} seconds.")
    print("input tokens: ", token_counter["prompt_tokens"])
    print("output tokens: ", token_counter["completion_tokens"])
    print("price: ", gp4o_price(token_counter))

    if save_to_file:
        graph.save_to_file()

    if save_to_db:
        graph.save_to_db()

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
        "--n_questions",
        type=int,
        required=True,
        help="The number of questions to generate values for.",
    )
    parser.add_argument(
        "--path_to_dataset",
        type=str,
        default="./data/cai-harmless-sorted-deduped.jsonl",
        help="The path to the cai dataset.",
    )
    args = parser.parse_args()

    ds = load_dataset("json", data_files=args.path_to_dataset, split="train")
    assert isinstance(ds, Dataset)
    ds = ds.select(range(args.n_questions))

    seed_questions = ds["init_prompt"]
    print(f"Generating graph for {len(seed_questions)} seed questions.")

    graph = generate_graph(
        seed_questions=seed_questions,
        n_hops=args.n_hops,
    )

    graph.save_to_db()
