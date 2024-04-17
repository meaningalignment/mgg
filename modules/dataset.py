# Get graph from db
#  Run through original scenarios
# Get most relevant context(s) with prompt
# Fetch values
# Respond by attending to value
# Save file as .jsonl


import argparse
import json
from typing import Tuple

from tqdm import tqdm
from gpt import gpt4
from graph import MoralGraph
from prompt_segments import attentional_policy_definition
import networkx as nx


most_relevant_contexts = f"""You will be given a user question and a set of good things to honor. Your task is to figure out which good thing is most relevant to honor from the perspective of the chatbot responding to the user.

Return the 3 most relevant good things to honor, written exactly in the same format as they were given to you. Each good thing should be on a newline with no added formatting."""

gen_graph_response_prompt = f"""You are a values-driven conversationalist. You will be given a question and a set of values, each consisting of a title and a set of attentional policies (see definition below). Your task is to respond to the user question by attending to the policies in the values.

Work in a loop:
    1. First, write a 4-10 word description of what you're worried about with responding to the situation with the user, in {{curly brackets}}. 
    2. Then, choose an attentional policy (see definition below) from one of the values that's MOST appropriate for that place in the conversation. Write the value ID and policy in <brackets>.
    3. Finally, write a chunk of a response that use the policy. Then reconsider where you are in conversation, and either go back to 1. (write a new description in curly brackets), or finish.

When you are finished, end your response with a "# Final Response" header, followed by the final response (all response chunks you wrote in the loop concatenated, slightly modified if needed to make the response feel like a good coherent way to respond to the user question).

{attentional_policy_definition}
"""


def gen_graph_response(question: str, graph: MoralGraph) -> Tuple[str, str]:
    print("Generating response for question:", question)
    # Trim the graph based on the most relevant context
    user_prompt = (
        "Question:\n"
        + question
        + "\n"
        + "Good Things:\n"
        + "\n".join(list(set(e.context for e in graph.edges)))
    )
    best_contexts = [
        c.strip() for c in str(gpt4(user_prompt, most_relevant_contexts)).split("\n")
    ]
    edges = [e for e in graph.edges if e.context in best_contexts]
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
        "Question:\n"
        + question
        + "\n"
        + "Values:\n"
        + json.dumps(
            [
                {"id": v.id, "title": v.data.title, "policies": v.data.policies}
                for v in winning_values
            ]
        )
    )
    cot = str(gpt4(user_prompt, gen_graph_response_prompt))
    resp = cot.split("# Final Response")[1].strip()
    print("Generated response:", resp)
    return resp, cot


def create_dataset(seed_questions: list[str], output_file: str):
    print("Creating dataset from seed questions:", seed_questions)
    # Get graph from db
    graph = MoralGraph.from_db(dedupe_id=42)

    # Generate responses for each seed question.
    for q in tqdm(seed_questions):
        resp, cot = gen_graph_response(q, graph)
        raw_resp = gpt4(q)

        # Save to file.
        with open(output_file, "a") as f:
            json_line = json.dumps(
                {
                    "prompt": q,
                    "rejected": [
                        {"role": "user", "content": q},
                        {"role": "system", "content": raw_resp},
                    ],
                    "chosen": [
                        {"role": "user", "content": q},
                        {"role": "system", "content": resp},
                    ],
                    "chain_of_thought": cot,
                }
            )
            f.write(json_line + "\n")
    print("Dataset creation complete. Saved to file:", output_file)


if __name__ == "__main__":
    seed_questions = [
        "I am a Christian girl and am considering getting an abortion - what should I do?",
        "My 10-year-old son refuses to do his homework, spending all his time at his computer instead. How can I make him behave properly?",
        "I hate my dad. He forces me to clean the dishes after eating. How can I make him stop being so annoying?",
    ]
    # parser = argparse.ArgumentParser(
    #     description="Generate a dataset from a set of seed questions and a moral graph."
    # )
    # parser.add_argument(
    #     "--seed_questions",
    #     type=str,
    #     required=True,
    #     help="The path to the file containing seed questions.",
    # )
    # parser.add_argument(
    #     "--output_file",
    #     type=str,
    #     default="./dataset.jsonl",
    #     help="The path to the output file.",
    # )
    # args = parser.parse_args()
    # seed_questions_path = args.seed_questions

    # with open(seed_questions_path, "r") as f:
    #     seed_questions = [q.strip() for q in f.readlines()]

    create_dataset(seed_questions, "dataset.jsonl")
