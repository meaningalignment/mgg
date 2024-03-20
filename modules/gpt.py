from collections import Counter
import json
from typing import List
import numpy as np
import openai
from prisma.models import DeduplicatedCard, ValuesCard

client = openai.OpenAI()


def gpt4(
    user_prompt: str,
    system_prompt: str | None = None,
    function: dict | None = None,
    temperature: float = 0.0,
    token_counter: Counter | None = None,
) -> str | dict:
    messages = []

    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    params = {
        "model": "gpt-4-0125-preview",
        "messages": [
            *messages,
            {"role": "user", "content": user_prompt},
        ],
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
