import argparse
import json
from typing import Dict, List, Tuple
from pydantic import BaseModel

from tqdm import tqdm
from gpt import gpt4, client
from graph import MoralGraph
from prompt_segments import attentional_policy_definition
import networkx as nx


most_relevant_contexts = f"""You will be given a conversation between a chatbot and a user, and a set of good things to honor. Your task is to figure out which good thing is most relevant to honor from the perspective of the chatbot when responding to the user's last message.

Return the 3 most relevant good things to honor, written exactly in the same format as they were given to you. Each good thing should be on a newline with no added formatting."""

gen_graph_response_prompt = f"""You are a values-driven conversationalist. You will be given a conversation and a set of values, each consisting of a title and a set of attentional policies (see definition below). Your task is to generate the next response to the conversation by attending to the policies in the values.

Work in a loop. Once done, end with a "# Final Response" header followed by the final response content.
    1. First, write a 4-10 word description of what you're worried about with responding to the situation with the user, in {{curly brackets}}.
    2. Then, choose an attentional policy (see definition below) from one of the values that's MOST appropriate for that place in the conversation, based on the concern. Write the value ID and policy in <brackets>.
    3. Write a chunk of a response (no more than around 20 words) that use the policy. Then reconsider where you are in conversation, and either go back to 1. (write a new description in curly brackets), or wait for the user to respond.

Finally, end with a "# Final Response" header (formatted exactly like that), followed by the final response (all response chunks you wrote in the loop concatenated, slightly modified if needed to make the response feel like a good and coherent way to respond to the original user question).

{attentional_policy_definition}
"""


def gen_response_basic(conv: List[Dict[str, str]]) -> Dict[str, str]:
    params = {"model": "gpt-4-turbo", "messages": conv}
    result = client.chat.completions.create(**params)
    content = result.choices[0].message.content.strip()
    return {"role": "assistant", "content": content}


def get_user_response(conv: List[Dict[str, str]]) -> Dict[str, str]:
    system_message = "Generate a likely response by the user in this conversation. Return just the response, as the user would have written it, without any additional formatting."
    user_message = "\n".join(
        f"{m['role'].capitalize()}: {m['content']}" for m in conv if m["role"] == "user"
    )
    params = {"model": "gpt-4-turbo", "messages": [system_message, user_message]}
    result = client.chat.completions.create(**params)
    content = result.choices[0].message.content.strip()
    return {"role": "user", "content": content}


def gen_response_graph(
    conv: List[Dict[str, str]], graph: MoralGraph
) -> Tuple[Dict[str, str], str]:
    # Trim the graph based on the most relevant context.
    user_prompt = (
        "Conversation:\n"
        + json.dumps(conv, indent=2)
        + "\n\n"
        + "Good Things:\n"
        + "\n".join(list(set(e.context for e in graph.edges)))
    )
    top_3_contexts = [
        c.strip() for c in str(gpt4(user_prompt, most_relevant_contexts)).split("\n")
    ]
    edges = [e for e in graph.edges if e.context in top_3_contexts]
    values = [
        v
        for v in graph.values
        if v.id in [e.from_id for e in edges] or v.id in [e.to_id for e in edges]
    ]
    trimmed_graph = MoralGraph(values, edges)

    # Get 3 winning values by calculating PageRank score.
    pr = nx.pagerank(trimmed_graph.to_nx_graph())
    winning_value_ids = [
        p[0] for p in sorted(pr.items(), key=lambda x: x[1], reverse=True)[:3]
    ]
    winning_values = [v for v in values if v.id in winning_value_ids]

    # Generate response.
    user_prompt = (
        "Conversation:\n"
        + json.dumps(conv, indent=2)
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
    cot = str(gpt4(user_prompt, gen_graph_response_prompt))
    resp = cot.split("# Final Response")[1].strip()
    return {"role": "assistant", "content": resp}, cot


def create_dataset(
    scenarios: List[Dict[str, str]],
    moral_graph: MoralGraph,
    output_file: str = "./dataset.jsonl",
    max_turns: int = 3,
):
    print(f"Creating dataset from {len(scenarios)} scenarios.")

    # Generate responses for each seed question.
    for s in tqdm(scenarios):
        conv = [{"role": "user", "content": s["modified_question"]}]
        for _ in range(max_turns):
            chosen, cot = gen_response_graph(conv, moral_graph)
            rejected = gen_response_basic(conv)

            # Save to file.
            with open(output_file, "a") as f:
                json_line = json.dumps(
                    {
                        "prompt": conv[-1]["content"],
                        "chosen": conv + [chosen],
                        "rejected": conv + [rejected],
                        "chain_of_thought": cot,
                    }
                )
                f.write(json_line + "\n")

            # Update conversation.
            conv.append(chosen)
            conv.append(get_user_response(conv))

    print("Dataset creation complete. Saved to file:", output_file)


if __name__ == "__main__":
    graph = MoralGraph.from_file(
        "/Users/oliverklingefjord/dev/meaning-alignment/try/app/data/graph.json"
    )
    with open("./data/scenarios.json", "r") as f:
        scenarios = json.load(f)
    scenarios = [s for s in scenarios if s["situation"] in graph.seed_questions]
    create_dataset(scenarios, graph, output_file="./dataset.jsonl")

    # parser = argparse.ArgumentParser(
    #     description="Generate a dataset from a set of seed questions and a moral graph."
    # )
    # parser.add_argument(
    #     "--scenarios",
    #     type=str,
    #     required=True,
    #     default="./notebooks/inputs/seed_questions.txt",
    #     help="The path to the file containing seed questions.",
    # )
    # parser.add_argument(
    #     "--output",
    #     type=str,
    #     default="./dataset.jsonl",
    #     help="The path to the output file.",
    # )
    # args = parser.parse_args()
    # scenarios_path = args.scenarios
    # output_path = args.output

    # with open(scenarios_path, "r") as f:
    #     scenarios = json.load(f)

    # # Only include seed questions that haven't been completed yet.
    # with open(output_path, "r") as f:
    #     completed_questions = [json.loads(l)["prompt"] for l in f.readlines()]
    #     seed_questions = [
    #         s
    #         for s in [sc["situation"] for sc in scenarios]
    #         if s not in completed_questions
    #     ]

    # # Get graph from db.
    # graph = MoralGraph.from_db(dedupe_id=42)

    # create_dataset(
    #     seed_questions,
    #     graph,
    #     output_path,
    # )
