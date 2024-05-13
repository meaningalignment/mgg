from collections import Counter
import json
from typing import List
import openai

client = openai.OpenAI()


def gpt4(
    user_prompt: str | None = None,
    system_prompt: str | None = None,
    function: dict | None = None,
    temperature: float = 0.0,
    token_counter: Counter | None = None,
) -> str | dict:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    if user_prompt:
        messages.append({"role": "user", "content": user_prompt})
    if not system_prompt and not user_prompt:
        raise ValueError(
            "At least one of user_prompt or system_prompt must be provided"
        )

    params = {
        "model": "gpt-4o",
        "messages": [*messages],
        "temperature": temperature,
    }

    if function:
        params["tools"] = [{"type": "function", "function": function}]
        params["tool_choice"] = {
            "type": "function",
            "function": {"name": function["name"]},
        }

    result = client.chat.completions.create(**params)

    if token_counter is not None:
        token_counter["prompt_tokens"] += result.usage.prompt_tokens
        token_counter["completion_tokens"] += result.usage.completion_tokens

    return (
        json.loads(result.choices[0].message.tool_calls[0].function.arguments)
        if function
        else result.choices[0].message.content.strip()
    )
