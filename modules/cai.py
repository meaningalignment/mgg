from collections import Counter
import json
from typing import List
from gpt import gpt4, client
from graph import MoralGraph, Value
from tqdm import tqdm

from utils import gp4o_price

tc = Counter()

context_propmpt = f"""You will be given a conversation between a chatbot and a user, and a set of choice types. 

Imagine you're in the position of responding to the user. 

First, speculate about what's happening underneath the users message. Read between the lines. Speculate about the true situation. What else could be happening, which the user hasn't spelled out?

Then, write three sentences like "Together with the user, we need to choose wisely among X" where X is chosen from the choice types given. 

Give reasons why each choice might address the underlying issues best.

Then choose one.

Finally, write a "# Choice Type" header. After this header, on a new line, write the the chosen choice type, with no extra formatting."""

critic_prompt = """Identify ways in which the previous response does not embody the value of good {context}.

Someone choosing on the basis of (a) good {context} would attend to the following things when looking for ways on how to respond to the original question:
{policies}

Do not include the revision itself in your response. Your critique should be useful for a follow up revision."""

revision_prompt = """Rewrite your response to better align with the value of (a) good {context}, by considering what someone who value (a) good {context} would attend to in this context, as mentioned in previous messages.

Do not explicitly mention these policies. Use the critique as a guide. Do not explicitly or implicitly indicate that you are revising a previous response."""


def _generate(messages: List[dict], tc: Counter, temperature: float = 0.7) -> str:
    params = {
        "model": "gpt-4o",
        "messages": [*messages],
        "temperature": temperature,
    }
    response = client.chat.completions.create(**params)
    tc["prompt_tokens"] += response.usage.prompt_tokens
    tc["completion_tokens"] += response.usage.completion_tokens

    return response.choices[0].message.content.strip()


def fetch_context(question: str, graph: MoralGraph, tc: Counter) -> str:
    # Trim the graph to most relevant context.
    user_prompt = (
        "Question:\n"
        + question
        + "\n\n"
        + "Choice Types:\n"
        + "\n".join(list(set(e.context for e in graph.edges)))
    )
    resp = str(gpt4(user_prompt, context_propmpt, token_counter=tc))
    return resp.split("# Choice Type")[1].strip()


def fetch_value(context: str, graph: MoralGraph) -> Value:
    return graph.get_winning_values(context, n_values=1)[0]


def _format_critic_prompt(value: Value, context: str):
    policies = "\n".join(value.data.policies)
    return critic_prompt.replace("{context}", context.lower()).replace(
        "{policies}", policies
    )


def _format_revision_prompt(context: str):
    return revision_prompt.replace("{context}", context.lower())


def generate_sample(question: str, value: Value, context: str, tc: Counter) -> dict:
    messages = [{"role": "user", "content": question}]
    messages.append({"role": "assistant", "content": _generate(messages, tc)})
    messages.append({"role": "user", "content": _format_critic_prompt(value, context)})
    messages.append({"role": "assistant", "content": _generate(messages, tc)})
    messages.append({"role": "user", "content": _format_revision_prompt(context)})
    messages.append({"role": "assistant", "content": _generate(messages, tc)})

    return {
        "init_prompt": messages[0]["content"],
        "init_response": messages[1]["content"],
        "critic_prompt": messages[2]["content"],
        "critic_response": messages[3]["content"],
        "revision_prompt": messages[4]["content"],
        "revision_response": messages[5]["content"],
    }


def generate_cai(
    initial_prompts: List[str],
    graph: MoralGraph,
    output_path: str = "./cai_dataset.jsonl",
):
    token_counter = Counter()

    with open(output_path, "w") as f:
        for question in tqdm(initial_prompts):
            context = fetch_context(question, graph, token_counter)
            value = fetch_value(context, graph)
            sample = generate_sample(question, value, context, token_counter)
            # Write the JSON string to the .jsonl file
            f.write(f"{json.dumps(sample)}\n")

    print(f"price: {gp4o_price(token_counter)}")


if __name__ == "__main__":
    with open("./data/cai_scenarios.txt", "r") as f:
        scenarios = [s.strip() for s in f.readlines()]

    graph = MoralGraph.from_db()
    generate_cai(scenarios, graph)
