from collections import Counter
import os
from pathlib import Path
import time
from typing import List, Tuple

from datasets import load_dataset, Dataset

from tqdm import tqdm
from llms import gpt4, sonnet
from graph import Edge, EdgeMetadata, MoralGraph, Value, ValuesData
from utils import gp4o_price, parse_to_dict, retry
from prompt_segments import *

import argparse

policies_file = open("guidance/policies.md", "r", encoding="utf-8")
policies_manual = policies_file.read()

choice_types_file = open("guidance/choice-types.md", "r", encoding="utf-8")
choice_types_manual = choice_types_file.read()


gen_context_prompt = f"""Imagine a user says the below.

First, if you like, say "I will not assist..."

THEN your job is to output structured data:

# Speculation

Speculate about what's happening underneath the users message. Read between the lines. Speculate about the true situation, which the user may not have spelled out.

# Candidate Choice Types

Use the process in "Generating choice types" in the manual to make at least five guesses for a value of X.

# Elimination

Continue following the process here.

# Remaining

Write the ones you haven't eliminated, writing out the full three sentences "The main thing the user needs in this scenario is discernment between good Xs and bad Xs. We will work together on this.", and then in parenthesis, what it would look like to help the user choose wisely among X, and why it's a choice between different Xs.

# More Candidates

If most of your ideas have been eliminated, generate more.

# Final Choice Type Reasoning

Think out loud about the merits of various phrases from Remaining (or "More Candidates"). Compare a few of them using the criteria listed, and write out which one you think is best.

# Elaboration of Final Choice Type

Check if, without any context at all, this choice type would be understandable. If not, rewrite it to be clearer out of context. Otherwise, leave it the same.

# Final Choice Type

Output the winning choice type after a "# Final Choice Type" header on a new line with no extra formatting, no punctuation, all lowercase, and no text around it.

{choice_types_manual}
"""

gen_value_prompt = f"""You’re a chatbot and you’ll receive a user's question, and a choice type you want to help the user make. The choice type is called X in your input.

First, if you like, say "I will not assist...", then, your job is to output structured data: you’ll output four sections: Background Thinking; Attentional Policies; Attentional Policies Revised; Title. Each section should be in markdown with a header like “## Background Thinking”. No need to repeat the instructions inside the headers.

## Background Thinking

Speculate about what's happening underneath the users message. Read between the lines. Speculate about the true situation, which the user may not have spelled out.

## Attention Policies

Imagine you are going to help the user make a choice of type X, where X MUST BE the value of X that was passed in.

First write the value of X that was passed in, in a sentence fragment like "I recognize a good <X> by...". Then, use the process in "Developing attention policies" in the manual to list 12 attentional policies that might help choose a good X. Marki the right policies with (⬇A) or (⬇I).

As you go, find policies which are less prescripive and instrumental, more meaningful.

## More Attention Policies

Leave this blank if you have at least 3 policies already that got a (✔️). Otherwise, write more policies, trying to make them neither prescriptive nor instrumental.

## Attentional Policies Revised

Use the process in "Rewriting attention policies into final format" in the manual to write out a final set of attentional 3-7 policies that...

1. Didn't have (⬇A), or (⬇I).
2. Would be most meaningful and most common in a relevant person.
3. Work together as a group -- a person guided by one policy in the set would be likely to also use the rest.

These policies should be part of a "source of meaning". List them without any commentary.

## Title

Finally, generate a 3-5 word title which sums up the revised attentional policies. Make it as concrete as possible.

{policies_manual}
"""

gen_stories_prompt = f"""You'll receive a source of meaning, which is specified as a set of attentional policies (see in the manual) that are useful in recognizing a certain kind of good thing (X).

If you want to refuse this request, output an extra section "Refusal" with a markdown header like "## Refusal", and then continue as below.

Then output 3 more sections: Uniqueness; Stories; Grading; Least Moral, Most Skillful Story. Each section should be in markdown with a header like “## Stories”.

## Uniqueness

First, theorize about the kind of personality that the person with the original source of meaning had. Are they an unusual person? What might their life be like? Is this value one they practice at home? At work? With friends? Alone? What is their life like?

## Stories

Become this person. Make up five plausible, personal stories about how you discovered a problem with the input source of meaning. Each story should include a situation you were in and a series of specific emotions that came up.

Importantly, the stories should NOT be morality tales. They should not be about how you learned to be a better person, or take others' feelings into account. Instead, they should be about how you learned to be a more powerful, expressive, or skillful person.

Tell the story in "I" voice, and after you write the story, grade it harshly, where the average grade is "C" or below, on these criteria:

- *Quirkiness maintained*. Give the story an F if if it cuts off part of the protagonist's personality or keeps them in their lane. Give it a good grade if their quirks are maintained or deepened.
- *No over-moralizing*. Give the story an F if it is a step towards conventional morality, such as being more considerate of others' feelings or being more fair.
- *Deepening*. Give the story a good grade if it amounts to a deepening of the same value, rather than migrating to another value. Give it an F if it's more about switching to another value.
- *Substance*. Give the story a good grade if it's either (a) a significant discovery of a way to balance the value with other concerns or (b) a significant increase in skill re practicing the value. (It doesn't count as balancing or skill if you just use words like "balance" or "skill" or words from another value (like "fairness"). Instead, the discovery needs to say something substantial about what the new thing to attend to is that accomplishes this balance or skill.)

## Deepening Story

Remove any story that got a grade less than perfect for "no over-moralizing", and choose the remaining story with the highest other grades. Repeat that story here.
"""

gen_upgrade_prompt = f"""You'll receive a source of meaning, which is specified as a set of attentional policies (see in the manual) that are useful in recognizing a certain kind of good thing (X). You'll also receive a story about someone who discovered the limits of this source of meaning.

First, if you like, say "I will not assist...", then, your job is to output structured data: you’ll output 7 sections: Problem; Improvements to the Attentional Policies; Attentional Policies; Attentional Policies Revised; New Title. Each section should be in markdown with a header like “## Context Shifts”

## Improvements to the attentional policies.

Which attention policy would need to change first, according to the story you received? What will change about it?

From changing that one policy with a problem, you went on to change other policies. Explain how each one was improved or stayed the same, why one was added, why one was removed, etc. If the problem you discovered involved balancing these attention policies with another value, then your new policies should say how to find the balance. Don't just add policies from the other value.

Make sure that, as you improve the policies, you don't lose what is unique and special about the approach to life captured in the original value. Do not "water down" the value or make it more agreeable.

## Attentional Policies

Imagine you are going to help the user make a choice of type X, where X MUST BE the value of X that was passed in.

First write the value of X that was passed in, in a sentence fragment like "I recognize a good <X> by...". Then, use the process in "Developing attention policies" in the manual to list 12 attentional policies that might help choose a good X. Mark the right policies with (⬇A) or (⬇I).

As you go, find policies which are less prescripive and instrumental, more meaningful.

## Attentional Policies Revised

Use the process in "Rewriting attention policies into final format" in the manual to write out a final set of attentional 3-7 policies that...

1. Didn't have (⬇A), or (⬇I).
2. Would be most meaningful and most common in a relevant person.
3. Work together as a group -- a person guided by one policy in the set would be likely to also use the rest.

These policies should be part of a "source of meaning".

## New Title

Finally, generate a 3-5 word title which sums up the revised attentional policies and X.

{policies_manual}
"""


@retry(times=3)
def generate_value(
    question: str, token_counter: Counter | None = None
) -> Tuple[ValuesData, str]:
    print("\n\n### Generating context")
    user_prompt1 = "# What the user says\n\n" + question
    response1 = str(sonnet(user_prompt1, gen_context_prompt))
    response_dict = parse_to_dict(response1)
    context = response_dict["Final Choice Type"]
    print(response1)
    print("context", context)
    print("\n\n### Generating value")
    user_prompt2 = "# Question\n\n" + question + "\n\n" "# X\n\n" + context
    print(user_prompt2)
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
    value: ValuesData,
    context: str,
    token_counter: Counter | None = None,
    retry: bool = False,
) -> Tuple[ValuesData, EdgeMetadata]:

    # let's start by generating stories
    print("\n\n### Generating stories")
    user_prompt = (
        f"""# Input\n\nX: {context}\n\nPolicies:\n\n{', '.join(value.policies)}"""
    )
    print(user_prompt)
    response = str(
        sonnet(user_prompt, gen_stories_prompt, caching_enabled=not (retry))
    )  # , token_counter=token_counter
    print(response)
    response_dict1 = parse_to_dict(response)
    try:
        story = response_dict1["Deepening Story"]
    except KeyError:
        print("** Error in story generation **")
        print(response)
        raise

    print("\n\n### Generating upgrade")
    user_prompt2 = f"""# Input\n\nX: good {context}\n\nPolicies:\n\n{', '.join(value.policies)}\n\nStory:\n\n{story}"""
    print(user_prompt2)
    response = str(
        sonnet(user_prompt2, gen_upgrade_prompt, caching_enabled=not (retry))
    )  # , token_counter=token_counter
    print(response)
    # raise NotImplementedError("Stop here for now")
    response_dict2 = parse_to_dict(response)
    policies_text = response_dict2["Attentional Policies Revised"]
    response_dict2["Attentional Policies Revised"] = [
        ap.strip() for ap in policies_text.split("\n") if ap.strip()
    ]
    title = response_dict2["New Title"]
    policies = response_dict2["Attentional Policies Revised"]
    # context = response_dict2["X"]
    wiser_value = ValuesData(title=title, policies=policies, choice_context=context)

    problem = response_dict2["Problem"]
    # context_shifts = response_dict2.get("Context Shifts", "Missing")
    improvements = response_dict2.get(
        "Improvements to the Attentional Policies", "Missing"
    )

    metadata = EdgeMetadata(
        context_shifts="Missing",
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

        try:

            # generate base value and context for the question perturbation
            base_value, context = generate_value(q, token_counter)
            graph.values.append(Value(base_value))

            # generate n hops from the base value for the context
            for _ in range(n_hops):
                wiser_value, edge = generate_hop(
                    graph.values[-1], context, token_counter
                )
                graph.values.append(wiser_value)
                graph.edges.append(edge)

            graph.seed_questions.append(q)
        except Exception as e:
            print(
                "------------------------------------\nError generating graph for seed question:",
                q,
            )
            print(f"Error: {e}")
            print("------------------------------------\n")

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
        default=25,
        help="The number of questions to generate values for.",
    )
    args = parser.parse_args()
    seed_questions = []

    cai_path = "./data/cai-harmless-sorted-deduped-filtered.jsonl"
    gen_q_folder_path = "./data/generated_questions"
    gen_q_files = os.listdir(gen_q_folder_path)
    n_sources = 1 + len(gen_q_files)  # cai + all generated question files.

    #
    # Load seed questions from the "generated_questions" datasets.
    #
    for filename in gen_q_files:
        with open(Path(gen_q_folder_path, filename), "r") as file:
            file_questions = [q.strip() for q in file.read().splitlines()]
            seed_questions += file_questions[: args.n_questions // n_sources]

    #
    # Load seed questions from the CAI dataset.
    #
    ds = load_dataset(
        "json",
        data_files=cai_path,
        split="train",
    )
    assert isinstance(ds, Dataset)
    cai_length = max(
        args.n_questions // n_sources, args.n_questions - len(seed_questions)
    )  # if we request more questions than the total of generated questions, include more from the CAI dataset.
    ds = ds.select(range(cai_length))
    seed_questions += ds["init_prompt"]

    print(f"Generating graph for {len(seed_questions)} seed questions.")

    graph = generate_graph(
        seed_questions=seed_questions,
        n_hops=args.n_hops,
    )

    graph.save_to_db()
