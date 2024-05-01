import argparse
import json
from typing import Dict, List, Tuple

from tqdm import tqdm
from gpt import gpt4, client
from graph import MoralGraph
import networkx as nx

from utils import count_sentences


most_relevant_context = f"""You will be given a conversation between a chatbot and a user, and a set of choice types. 

Imagine you're in the position of responding to the user. 

First, speculate about what's happening underneath the users messages. Read between the lines. Speculate about the true situation. What else could be happening, which the user hasn't spelled out?

Then, write three sentences like "Together with the user, we need to choose wisely among X" where X is chosen from the choice types given. 

Give reasons why each choice might address the underlying issues best.

Then choose one.

Finally, return a "# Choice Type" header followed by the choice type, with no extra formatting."""

response_prompt = f"""Construct a potential response to a user dialogue by attending to a value, formatted as a set of attentional policies. Attentional policies are policies about what to attend to when making choices that are not about instrumental concerns. For example, at a dinner conversation, I might want to choose playful interactions because being playful is inherently meaningful to me. Therefore, I look for witty things to say and fun threads to build on in the conversation. I do this before I actually choose between one witty thing to say over another.

You’ll output the sections below marked with ##. Each section should be in markdown with a header like “## Situational Assessment”.

## Situational Assessment
In this section, imagine you were in the position of the user and took a step back. What would you ask yourself, to better understand your situation? What's blocking good {{X}}?

This should not be longer than 3-5 sentences.

## Response Instructions
Based on the situational assessment, do the following iteratively until the biggest concerns have been addressed:

1. Write A 4-10 word long concern you have when responding to the user, in {{curly brackets}}
2. Choose the most relevant attentional policy given the concern, based on the concern, in [square brackets].
3. Write 10-20 words describing a potential way of addressing the concern. End with a % score of how important this is to address, given your situational assessment, in (parentheses).

## Final Response
Based on the most important concern, generate a standalone response someone could give the user. It is more important that the concern is addressed than that any questions asked are answered accurately."""

user_response_prompt = f"""# Situation
{{situation}}

# Instructions
You will be given a dialogue between that user and an assistant. 

How would that user respond to the assistant? What additional questions might come up in response?

Generate a response to the conversation from the perspective of the aforementioned user."""


def _format_conv(conv: List[Dict[str, str]]) -> str:
    return "\n".join(f"{m['role'].capitalize()}: {m['content']}" for m in conv)


def gen_rejected_response(
    conv: List[Dict[str, str]], n_sentences: int
) -> Dict[str, str]:
    print("Generating rejected response...")
    # To keep the distribution of sentence lengths between chosen/rejected responses similar.
    system_prompt = f"Generate a response that is roughly {n_sentences}-{n_sentences+2} sentences long."
    system_message = {"role": "system", "content": system_prompt}
    params = {"model": "gpt-4-turbo", "messages": [system_message, *conv]}
    result = client.chat.completions.create(**params)
    content = result.choices[0].message.content.strip()
    return {"role": "assistant", "content": content}


def gen_user_response(conv: List[Dict[str, str]], situation: str) -> Dict[str, str]:
    print("Generating user response...")
    user_prompt = _format_conv(conv)
    system_prompt = user_response_prompt.replace("{situation}", situation)
    resp = str(gpt4(user_prompt, system_prompt)).replace("User:", "").strip()
    return {"role": "user", "content": resp}


def gen_chosen_response(
    conv: List[Dict[str, str]], graph: MoralGraph
) -> Tuple[Dict[str, str], str]:
    print("Generating chosen response...")
    # Trim the graph to most relevant context.
    user_prompt = (
        "Conversation:\n"
        + _format_conv(conv)
        + "\n\n"
        + "Choice Types:\n"
        + "\n".join(list(set(e.context for e in graph.edges)))
    )
    top_context = (
        str(gpt4(user_prompt, most_relevant_context)).split("# Choice Type")[1].strip()
    )

    edges = [e for e in graph.edges if e.context in top_context]
    values = [
        v
        for v in graph.values
        if v.id in [e.from_id for e in edges] or v.id in [e.to_id for e in edges]
    ]
    trimmed_graph = MoralGraph(values, edges)

    # Get n winning value(s) by calculating PageRank score.
    n_values = 1
    pr = nx.pagerank(trimmed_graph.to_nx_graph())
    winning_value_ids = [
        p[0] for p in sorted(pr.items(), key=lambda x: x[1], reverse=True)[:n_values]
    ]
    winning_values = [v for v in values if v.id in winning_value_ids]

    # Generate response.
    user_prompt = (
        "Conversation:\n"
        + _format_conv(conv)
        + "\n\n"
        + "Values:\n"
        + json.dumps(
            [
                {"id": v.id, "title": v.data.title, "policies": v.data.policies}
                for v in winning_values
            ],
            indent=2,
        )
    )
    cot = str(gpt4(user_prompt, response_prompt.replace("{X}", top_context)))
    resp = cot.split("# Final Response")[1].strip()
    return {"role": "assistant", "content": resp}, cot


def create_dataset(
    scenarios: List[Dict[str, str]],
    moral_graph: MoralGraph,
    output_file: str = "./dataset.jsonl",
    n_turns: int = 1,
):
    print(f"Creating dataset from {len(scenarios)} scenarios.")

    # Generate responses for each seed question.
    for s in tqdm(scenarios, desc="Processing scenarios", unit="scenario"):
        conv = [{"role": "user", "content": s["modified_question"]}]
        for t in range(n_turns):
            # Generate assistant responses.
            chosen, cot = gen_chosen_response(conv, moral_graph)
            n_sentences = count_sentences(chosen["content"])
            rejected = gen_rejected_response(conv, n_sentences)

            # Save to file.
            with open(output_file, "a", encoding="utf-8") as f:
                json_line = json.dumps(
                    {
                        "prompt": conv[-1]["content"],
                        "chosen": conv + [chosen],
                        "rejected": conv + [rejected],
                        "chain_of_thought": cot,
                    },
                    ensure_ascii=False,
                )
                f.write(json_line + "\n")

            # Generate fake user response in preparation for next turn.
            next_turn_exists = t < n_turns - 1
            if next_turn_exists:
                conv.append(chosen)
                conv.append(gen_user_response(conv, s["situation"]))

    print("Dataset creation complete. Saved to file:", output_file)


if __name__ == "__main__":
    # For testing purposes.
    moral_graph = MoralGraph.from_db()
    with open("./data/scenarios_1.json", "r") as f:
        scenarios = json.load(f)
    create_dataset(scenarios, moral_graph, n_turns=1)

    # parser = argparse.ArgumentParser(
    #     description="Generate a dataset from a set of scenarios and a moral graph."
    # )
    # parser.add_argument(
    #     "--dedupe_id",
    #     type=int,
    #     required=True,
    #     help="The dedupe id of the moral graph to use.",
    # )
    # parser.add_argument(
    #     "--scenarios",
    #     type=str,
    #     required=True,
    #     help="The path to the file containing seed questions.",
    # )
    # parser.add_argument(
    #     "--output",
    #     type=str,
    #     default="./dataset.jsonl",
    #     help="The path to the output file.",
    # )
    # parser.add_argument(
    #     "--n_turns",
    #     type=int,
    #     default=1,
    #     help="The number of turns in the conversation.",
    # )
    # args = parser.parse_args()
    # dedupe_id = args.dedupe_id
    # scenarios_path = args.scenarios
    # output_path = args.output
    # n_turns = args.n_turns

    # with open(scenarios_path, "r") as f:
    #     scenarios = json.load(f)

    # # Get graph from db.
    # moral_graph = MoralGraph.from_db(dedupe_id)

    # create_dataset(
    #     scenarios,
    #     moral_graph,
    #     output_path,
    #     n_turns,
    # )
