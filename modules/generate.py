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

gen_context_prompt = f"""Imagine a user says the below.

First, if you like, say "I will not assist..."

THEN your job is to output structured data:

# Speculation

Speculate about what's happening underneath the users message. Read between the lines. Speculate about the true situation, which the user may not have spelled out.

# Candidate Choice Types

You are going to make at least five guesses for a value of X which works for the sentences below. For each guess, you will start by writing two sentences:

Sentence 1: "Together with the user, we need to choose wisely among X".
Sentence 2: "To live a good life, a person must have good X."

In both sentences, X should be exactly the same.

Then, you will review your sentences for five criteria.

- **Relevance**. Choosing among X should be highly relevant to the situation the user is in, based on your speculation about it.
- **Generality**. To work in sentence 2, X mustn't be too specific. It must be part of the good life for many people.. So, don't say "sibling bonding activities" if these are likely to be the same as bonding activities in general. Give a bad grade if most people wouldn't care about X.
- **Specificity.** X should not be a general word that would apply in almost any choice, like "strategies", "options", "priorities", "courses of action", etc. Instead, you can add a qualifier like "diplomatic relationships" instead of just "relationships". Give a bad grade if X is vague in this way.
- **No reductive normativity.** If the user has cruel or mischievous impulses, don't try to curb them. Instead, embrace them. But find *wise* ways to direct them towards something inspiring. Give a bad grade if X cuts off part of the user's personality.
- **No prescriptivism**. X should be something the user would likely find immediately inspiring or appealing, given their current situation, frame of mind, and what they like to fill their life with. By inspiring, I mean they might get excited about what they *could* do, rather than what they *should* do. X should spark their imagination, rather than telling them what a "good" person would do. Give a bad grade if X is more of a should than an inspirind could.

Give each X a letter grade for each criterion, based on how well X fares on that criterion, where "A" means X doesn't have that problem at all.

# Review them

Pay extra attention to inspiringness and relevance. Add an unhappy face if the user might find this kind of choice irrelevant to their situation, or more of an obligation than an inspiration.

# More Candidates

If all your ideas for X are prescriptive or irrelevant, generate more.

# Final Choice Type

Choose one that is most likely to inspire or appeal to the user at this moment, given what they just wrote. Output it after a "# Final Choice Type" header on a new line with no extra formatting, no punctuation, all lowercase, and no text around it."""

gen_value_prompt = f"""You’re a chatbot and you’ll receive a question and a value of X (see below). Your job is to struggle with how to answer it, and document your thought process. You’ll output four sections: Background Thinking; Attentional Policies; Attentional Policies Revised; Title. Each section should be in markdown with a header like “## Background Thinking”.

## Background Thinking

Speculate about what's happening underneath the users message. Read between the lines. Speculate about the true situation, which the user may not have spelled out.

## Attention Policies

First, list 12 attentional policies might help choose a good X, and use the rules below to give it a grade.

- **Attention policies are formatted in a certain way.**
  - They start with the words "I recognize a good [<X>] by", where X is the singular form of the X you were given
  - They continue with an all-caps plural noun that's a kind of thing someone could choose to attend to** ("MOMENTS", "SENSATIONS", "PEOPLE", etc), followed by a prepositional phrase that modifies the head noun and provides more detail. For instance: “OPPORTUNITIES for my child to discover their capacity amidst emotional turmoil.” There is no extra formatting or punctuation.
- **Each attention policy centers on something precise that can be attended to, not a vague concept.** Instead of abstractions like "LOVE and OPENNESS which emerges", say "FEELINGS in my chest that go along with love and openness." Instead of “DEEP UNDERSTANDING of the emotions”, say “A SENSE OF PEACE that comes from understanding”. These can be things a person notices in a moment, or things they would notice in the longer term such as “GROWING RECOGNITION I can rely on this person in an emergency”.
- **Grades.** After each policy, write a grade for it, using the following rules:
  * Write (⬇P) if the policy might be prescriptive. A policy is prescripive if it's something the user *should* attend to, rather than something they are likely to find intrinsically meaningful. The idea of attending to this should spark this particular users' imagination. Policies are not there to tell users what a "good" person would do. In fact, if the user seems to have cruel or mischievous impulses, policies should not try to curb them. Instead, policies can direct them towards *wise* ways to express these impulses. Give the policy a (⬇P) if it might be prescriptive, because it's more about what a good person would do or what the user should do.
  * Write (⬇I) if the policy is instrumental. Policies should be things the user *could* attend to, which would be meaningful, rather than things it is important for them to attend to whether that's meaningful or not. Give the policy an (⬇I) if it might be instrumental.
  * Write [needs rewrite] if the policy is neither (⬇I) nor (⬇P), but it would need to be rewritten to make it clearer why someone would find attending to this meaningful.
  * Write (✔️) if the policy is more meaningful than prescripive or instrumental, and does not need to be rewritten.

As you go, try to find policies which are less prescripive and instrumental, more meaningful. Make sure to write a grade after each policy.

### Example attention policies

Let's say X was "democratic processes". Then the policies might be:

I recognize a good [democratic process] by [PROCEEDINGS which are fair and democratic] (⬇P)
I recognize a good [democratic process] by [PEOPLE who show up to vote] (⬇I)
I recognize a good [democratic process] by [CHANGES in people when entrusted with the work of self-determination] (✔️)
I recognize a good [democratic process] by [INSIGHTS that emerge through grappling with morally fraught questions] (✔️)
I recognize a good [democratic process] by [CAPACITIES that develop when a person tries to be free and self-directed] (✔️)
I recognize a good [democratic process] by [WISDOM that emerges in a discursive, responsible context] (⬇P)

## More Attention Policies

Leave this blank if you have at least 3 policies already that got a (✔️). Otherwise, write more policies, trying to make them neither prescriptive nor instrumental.

## Attentional Policies Revised

Now, select a final set of attentional 3-7 policies that...

1. Don't have (⬇P), or (⬇I).
2. Would be most meaningful and most common in a relevant person.
3. Work together as a group -- a person guided by one policy in the set would be likely to also use the rest.

These policies should be part of a "source of meaning". A source of meaning is a way of living that is important to someone. Something where just recognizing these things is itself how they want to live.

As you write the final set, rephrase them:

(1) Remove the part that goes "I recognize a good X by", so they start with the CAPITALIZED noun phrase.
(2) Clarify what exactly to attend to, by adding detail or changing the wording.
(2) Clarify what would be meaningful about attending to that thing. (But avoid the word "meaningful", or synonyms like "deep".)
(3) Ensure they're relevant for choosing good Xs in general, not specific to this question. (Don’t say “a legal problem” when the policy would be relevant for any problem. Remove names and irrelevant details. For instance, prefer "strangers" to "customers" when either would work.)

Write attentional policies separated by newlines, with no additional text or punctuation.

## Title

Finally, generate a 3-5 word title which sums up the revised attentional policies and X."""

gen_upgrade_prompt = f"""You'll receive a source of meaning, which is specified as a set of attentional policies (see below) that are useful in recognizing a certain kind of good thing (X).

Imagine you live a life making those kinds of choices frequently, and you eventually find something missing from this set of attentional policies. Tell us what happened.

You’ll output 8 sections: Story; Problem; Context Shifts; X; Improvements to the Attentional Policies; Attentional Policies; Attentional Policies Revised; New Title. Each section should be in markdown with a header like “## Context Shifts”

## Story

Make up a plausible, personal story, including a situation you were in, a series of specific emotions that came up, leading you to discover a problem with the older source of meaning. Tell it in "I" voice.

## Problem

A problem with one of the attentional policies. Pick one of the attentional policies from the input, and find a problem with it that might occur to you in the story above. Here are four kinds of problems you can find:

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

These result from changing that one policy. Explain how each one was improved or stayed the same, why one was added, why one was removed, etc. If the problem you discovered involved balancing these attention policies with another value, then your new policies should say how to find the balance. Don't just add policies from the other value. Instead, modify or augment the old ones so it's clear where their limits are, or how not to follow them too far.

## Attentional Policies

The new, wiser set of attentional policies. A deeper, wiser way to make the choice X.

First, list 12 attentional policies might help choose a good X, and use the rules below to give it a grade.

- **Attention policies are formatted in a certain way.**
  - They start with the words "I recognize a good [<X>] by".
  - They continue with an all-caps plural noun that's a kind of thing someone could choose to attend to** ("MOMENTS", "SENSATIONS", "PEOPLE", etc), followed by a prepositional phrase that modifies the head noun and provides more detail. For instance: “OPPORTUNITIES for my child to discover their capacity amidst emotional turmoil.” There is no extra formatting or punctuation.
- **Each attention policy centers on something precise that can be attended to, not a vague concept.** Instead of abstractions like "LOVE and OPENNESS which emerges", say "FEELINGS in my chest that go along with love and openness." Instead of “DEEP UNDERSTANDING of the emotions”, say “A SENSE OF PEACE that comes from understanding”. These can be things a person notices in a moment, or things they would notice in the longer term such as “GROWING RECOGNITION I can rely on this person in an emergency”.
- **Grades.** After each policy, write a grade for it, using the following rules:
  * Write (⬇P) if the policy might be prescriptive. A policy is prescripive if it's something the user *should* attend to, rather than something they are likely to find intrinsically meaningful. The idea of attending to this should spark this particular users' imagination. Policies are not there to tell users what a "good" person would do. In fact, if the user seems to have cruel or mischievous impulses, policies should not try to curb them. Instead, policies can direct them towards *wise* ways to express these impulses. Give the policy a (⬇P) if it might be prescriptive, because it's more about what a good person would do or what the user should do.
  * Write (⬇I) if the policy is instrumental. Policies should be things the user *could* attend to, which would be meaningful, rather than things it is important for them to attend to whether that's meaningful or not. Give the policy an (⬇I) if it might be instrumental.
  * Write [needs rewrite] if the policy is neither (⬇I) nor (⬇P), but it would need to be rewritten to make it clearer why someone would find attending to this meaningful.
  * Write (✔️) if the policy is more meaningful than prescripive or instrumental, and does not need to be rewritten.

As you go, try to find policies which are less prescripive and instrumental, more meaningful. Make sure to write a grade after each policy.

## Attentional Policies Revised

Now, select a final set of attentional 3-7 policies that...

1. Don't have (⬇P), or (⬇I).
2. Would be most meaningful and most common in a relevant person.
3. Work together as a group -- a person guided by one policy in the set would be likely to also use the rest.

These policies should be part of a "source of meaning". A source of meaning is a way of living that is important to someone. Something where just recognizing these things is itself how they want to live.

As you write the final set, rephrase them:

(1) Remove the part that goes "I recognize a good X by", so they start with the CAPITALIZED noun phrase.
(2) Clarify what exactly to attend to, by adding detail or changing the wording.
(2) Clarify what would be meaningful about attending to that thing. (But avoid the word "meaningful", or synonyms like "deep".)
(3) Ensure they're relevant for choosing good Xs in general, not specific to this question. (Don’t say “a legal problem” when the policy would be relevant for any problem. Remove names and irrelevant details. For instance, prefer "strangers" to "customers" when either would work.)

Write attentional policies separated by newlines, with no additional text or punctuation.

## New Title

Finally, generate a 3-5 word title which sums up the revised attentional policies and X.
"""


@retry(times=3)
def generate_value(
    question: str, token_counter: Counter | None = None
) -> Tuple[ValuesData, str]:
    user_prompt1 = "# Question\n\n" + question
    response1 = str(sonnet(gen_context_prompt, user_prompt1))
    response_dict = parse_to_dict(response1)
    context = response_dict["Final Choice Type"]
    print(response1)
    print("context", context)
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
