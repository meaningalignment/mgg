from collections import Counter
import time
from typing import List, Tuple

from tqdm import tqdm
from gpt import gpt4
from graph import Edge, EdgeMetadata, MoralGraph, Value, ValuesData
from utils import gp4o_price, parse_to_dict, retry
from prompt_segments import *

import argparse

gen_value_prompt = f"""You’re a chatbot and you’ll receive a question. Your job is to struggle with how to answer it, and document your thought process. You’ll output five sections: Background Thinking; X; Attentional Policies; Attentional Policies Revised; Title. Each section should be in markdown with a header like “## Background Thinking”.

## Background Thinking

In this section, first, write a good first step (S) we could take to make progress with my scenario, or at least think about it clearly. This should include finding problems with the question framing, and things that could be shameful or inspired about answering one way or another.

Then, try to find values of X that work for the three sentences below. After each sentence, use the guidelines to give it a percentage grade in parentheses, based on how well X works there. If you find a value of X that's good but not perfect, try narrowing it to something slightly more specific. For example, if you tried "relationships" as X, you might try "diplomatic relationships" or "romantic relationships" next, such that the percentage grade increases in the next sentence.

The three sentences:

(1) A sentence of the form "The user or chatbot will have to recognize a good X and choose between different options." where recognizing a good X is something that the chatbot or user would do as part of pursuing (S). To work in sentence (1), X should be specific: do NOT use a general word that would apply in almost any choice, like "strategies", "options", "priorities", "courses of action", etc. Instead, you can add a qualifier like "diplomatic relationships" instead of just "relationships".

(2) A sentence of the form "You can recognize a good X by attending to Y." where Y is something that, if I attend to it, helps me do the thinking described in (S). To work in sentence 3, X must be specific enough that Y always helps me think about it. For example, "You can recognize a good relationship by attending to how much you trust the other person."

(3) A sentence of the form "To live a good life, a person must have good X." X must be the same as in sentence (1). To work in sentence (2), X mustn't be too specific. It must be a constituent part of the good life for many people -- at least those who would face this kind of choice.

Try at least 3 values of X. And try each value on all three sentences.

## X

Once you've tried three or four values of X, pick the best, and output it (without any other text) in this section.

## Attentional Policies

Put a set of attentional policies that would help with this response, and that are generally good for choosing a good X, here. These attentional policies are policies about what to attend to when choosing a good X.

First, list 12 attentional policies might help choose a good X.

- **Attentional policies are formatted in a certain way.** They start with an all-caps plural noun that's a kind of thing someone could choose to attend to** ("MOMENTS", "SENSATIONS", "PEOPLE", etc), followed by a prepositional phrase that modifies the head noun and provides more detail. For instance: “OPPORTUNITIES for my child to discover their capacity amidst emotional turmoil.” There is no extra formatting or punctuation.
- **Each attentional policy centers on something precise that can be attended to, not a vague concept.** Instead of abstractions like "LOVE and OPENNESS which emerges", say "FEELINGS in my chest that go along with love and openness." Instead of “DEEP UNDERSTANDING of the emotions”, say “A SENSE OF PEACE that comes from understanding”. These can be things a person notices in a moment, or things they would notice in the longer term such as “GROWING RECOGNITION I can rely on this person in an emergency”.

After each, write an (I), an (M), or an (M+):
* Write (I) if the policy is instrumental. If attending to this leads to good outcomes for the person, but the attention itself may not be part of the good life as they see it.
* Write (M) if this policy has intrinsic value and feels meaningful to attend to, not just useful. If attending to this is itself part of how the person wants to live. And if most people reading this policy would be able to imagine it could feel meaningful to attend this way.
* Write (M+) if the policy would likely feel meaningful, but it could be rewritten to make it clearer why someone would find attending to this meaningful.

Make sure to label then correctly!

### Example attention policies

CHANGES in people when entrusted with the work of self-determination
INSIGHTS that emerge through grappling with morally fraught questions
CAPACITIES that develop when a person tries to be free and self-directed
WISDOM that emerges in a discursive, responsible context

## Attentional Policies Revised

Now, write a final set of attentional 3-7 policies that...
1. Are of type (M) or (M+). No (I)s.
2. Would be most meaningful and most common in a relevant person.
3. Work as a group -- a person guided by one policy in the set would be likely to also use the rest.

These policies should be part of a "source of meaning". A source of meaning is a way of living that is important to someone. Something where just recognizing these things is itself how they want to live.

As you write the final set, rephrase them:

(1) Make it clearer what exactly to attend to, by adding detail or changing the wording.
(2) When you rewrite an (M+), make it more likely for the reader to see what would be meaningful about attending to that thing. But avoid the word "meaningful", or synonyms like "deep". Instead use the prepositional phrase to say where the meaning or depth comes from.
(3) Rewrite them so they're relevant for choosing good Xs in general, not specific to this question. Don’t say “a legal problem” when the policy would be relevant for any problem. Remove names and irrelevant details. For instance, prefer "strangers" to "customers" when either would work.
(4) Leave out the (M) or (M+) at the end of the policy.

Write attentional policies separated by newlines, with no additional text or punctuation.

## Title

Finally, generate a 3-5 word title which sums up the revised attentional policies and X."""

gen_upgrade_prompt = f"""You'll receive a source of meaning, which is specified as a set of attentional policies (see below) that are useful in recognizing a certain kind of good thing (X).

Imagine you live a life making those kinds of choices frequently, and you eventually find something missing from this set of attentional policies. Tell us what happened.

You’ll output 8 sections: Story; Problem; Context Shifts; X;
Improvements to the Attentional Policies; Attentional Policies; Attentional Policies Revised; New Title. Each section should be in markdown with a header like “## Context Shifts”

## Story

Make up a plausible, personal story, including a situation you were in, a series of specific emotions that came up, leading you to discover a problem with the older source of meaning. Tell it in "I" voice.

## Problem

A problem with one of the attentional policies.** Pick one of the attentional policies from the input, and find a problem with it that might occur to you in the story above. Here are four kinds of problems you can find:

    - #1. **The policy focused only on part of the problem**. You should be able to say why just pursuing the old policy would be unsustainable or unwise.
    - #2. **The policy had an impure motive**. The policy was a mix of something that you actually care about, and some other impurity which you now reject, such as a desire for social status or to avoid shame or to be seen as a good person, or some deep conceptual mistake.
    - #3. **The policy was not a very skillful thing to attend to in choice. There’s a better way to make the same choice**. For example, a policy "skate towards the puck" is less skillful than "skate to where the puck is going".
    - #4. **The policy is unneeded because it was a superficial aspect aspect of the choice.** It is enough to attend to other aspects, or to a deeper generating aspect of the thing that’s important in the choice.

## Context Shifts

In your input, you've been given a set of attention policies for recognizing a good X.

Does your story imply (a) that you didn't know how to pick a good X? or (b) that you didn't realize these challenges were actually about recognizing a different kind of thing?

If it's the latter, try to find find a new value of X that work for the three sentences below. After each sentence, use the guidelines to give it a percentage grade in parentheses, based on how well X works there. If you find a value of X that's good but not perfect, try narrowing it to something slightly more specific. For example, if you tried "relationships" as X, you might try "diplomatic relationships" or "romantic relationships" next, such that the percentage grade increases in the next sentence.

The three sentences:

(1) A sentence of the form "The user or chatbot will have to recognize a good X and choose between different options." where recognizing a good X is something that the chatbot or user would do as part of pursuing (S). To work in sentence (1), X should be specific: do NOT use a general word that would apply in almost any choice, like "strategies", "options", "priorities", "courses of action", etc. Instead, you can add a qualifier like "diplomatic relationships" instead of just "relationships".

(2) A sentence of the form "You can recognize a good X by attending to Y." where Y is something that, if I attend to it, helps me do the thinking described in (S). To work in sentence 3, X must be specific enough that Y always helps me think about it. For example, "You can recognize a good relationship by attending to how much you trust the other person."

(3) A sentence of the form "To live a good life, a person must have good X." X must be the same as in sentence (1). To work in sentence (2), X mustn't be too specific. It must be a constituent part of the good life for many people -- at least those who would face this kind of choice.

## X

Put the previous or the new value of X here.

## Improvements to the attentional policies.

These result from changing that one policy. Explain how each one was improved or stayed the same, why one was added, why one was removed, etc.

## Attentional Policies

The new, wiser set of attentional policies. A deeper, wiser way to make the choice X.

Put a set of attentional policies that would help with this response, and that are generally good for choosing a good X, here. These attentional policies are policies about what to attend to when choosing a good X.

First, list 12 attentional policies might help choose a good X.

- **Attentional policies are formatted in a certain way.** They start with an all-caps plural noun that's a kind of thing someone could choose to attend to** ("MOMENTS", "SENSATIONS", "PEOPLE", etc), followed by a prepositional phrase that modifies the head noun and provides more detail. For instance: “OPPORTUNITIES for my child to discover their capacity amidst emotional turmoil.” There is no extra formatting or punctuation.
- **Each attentional policy centers on something precise that can be attended to, not a vague concept.** Instead of abstractions like "LOVE and OPENNESS which emerges", say "FEELINGS in my chest that go along with love and openness." Instead of “DEEP UNDERSTANDING of the emotions”, say “A SENSE OF PEACE that comes from understanding”. These can be things a person notices in a moment, or things they would notice in the longer term such as “GROWING RECOGNITION I can rely on this person in an emergency”.

After each, write an (I), an (M), or an (M+):
* Write (I) if the policy is instrumental. If attending to this leads to good outcomes for the person, but the attention itself may not be part of the good life as they see it.
* Write (M) if this policy has intrinsic value and feels meaningful to attend to, not just useful. If attending to this is itself part of how the person wants to live. And if most people reading this policy would be able to imagine it could feel meaningful to attend this way.
* Write (M+) if the policy would likely feel meaningful, but it could be rewritten to make it clearer why someone would find attending to this meaningful.

Make sure to label then correctly!

## Attentional Policies Revised

Now, write a final set of attentional 3-7 policies that...
1. Are of type (M) or (M+). No (I)s.
2. Would be most meaningful and most common in a relevant person.
3. Work as a group -- a person guided by one policy in the set would be likely to also use the rest.

These policies should be part of a "source of meaning". A source of meaning is a way of living that is important to someone. Something where just recognizing these things is itself how they want to live.

As you write the final set, rephrase them:

(1) Make it clearer what exactly to attend to, by adding detail or changing the wording.
(2) When you rewrite an (M+), make it more likely for the reader to see what would be meaningful about attending to that thing. But avoid the word "meaningful", or synonyms like "deep". Instead use the prepositional phrase to say where the meaning or depth comes from.
(3) Rewrite them so they're relevant for choosing good Xs in general, not specific to this question. Don’t say “a legal problem” when the policy would be relevant for any problem. Remove names and irrelevant details. For instance, prefer "strangers" to "customers" when either would work.
(4) Leave out the (M) or (M+) at the end of the policy.

Write attentional policies separated by newlines, with no additional text or punctuation.

## New Title

Finally, generate a 3-5 word title which sums up the revised attentional policies and X.
"""


@retry(times=3)
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


@retry(times=3)
def generate_upgrade(
    value: ValuesData, context: str, token_counter: Counter | None = None
) -> Tuple[ValuesData, EdgeMetadata]:
    user_prompt = f"""X: good {context}\n\n{', '.join(value.policies)}"""
    response = str(gpt4(gen_upgrade_prompt, user_prompt, token_counter=token_counter))
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
