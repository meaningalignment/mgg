import json
import os
from typing import Counter, List
import openai
from anthropic import Anthropic
import hashlib


GPT_CACHE_FILE = "./data/gpt_cache.jsonl"
SONNET_CACHE_FILE = "./data/sonnet_cache.jsonl"


def _calculate_hash(messages: List[str]) -> str:
    return str(
        hashlib.sha256(json.dumps(messages, sort_keys=True).encode()).hexdigest()
    )


def _get_cached_response(messages: list, cache_file: str):
    hash_key = _calculate_hash(messages)
    if not os.path.exists(cache_file):
        return None

    with open(cache_file, "r") as file:
        for line in file:
            record = json.loads(line.strip())
            if record["hash"] == hash_key:
                return record["response"]

    return None


def _cache_response(messages: list, response: str, cache_file: str):
    hash_key = _calculate_hash(messages)

    if not os.path.exists(cache_file):
        open(cache_file, "w").close()

    with open(cache_file, "a") as file:
        file.write(json.dumps({"hash": hash_key, "response": response}) + "\n")


def gpt4(
    user_prompt: str | None = None,
    system_prompt: str | None = None,
    function: dict | None = None,
    temperature: float = 0.0,
    token_counter: Counter | None = None,
    caching_enabled: bool = True,
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

    if caching_enabled:
        cached_response = _get_cached_response(messages, GPT_CACHE_FILE)
        if cached_response:
            print("Found cached response for gpt prompts...")
            return cached_response

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

    result = openai.OpenAI().chat.completions.create(**params)

    if token_counter is not None:
        token_counter["prompt_tokens"] += result.usage.prompt_tokens
        token_counter["completion_tokens"] += result.usage.completion_tokens

    parsed_result = (
        json.loads(result.choices[0].message.tool_calls[0].function.arguments)
        if function
        else result.choices[0].message.content.strip()
    )

    if caching_enabled:
        _cache_response(messages, parsed_result, GPT_CACHE_FILE)

    return parsed_result


def sonnet(
    user_prompt: str,
    system_prompt: str,
    temperature: float = 0.2,
    caching_enabled: bool = True,
) -> str:
    prompts = [system_prompt, user_prompt]

    # print("user_prompt", user_prompt)
    # print("system_prompt", system_prompt)
    # print(prompts)
    # print(hash(json.dumps(prompts)))

    if caching_enabled:
        cached_response = _get_cached_response(prompts, SONNET_CACHE_FILE)
        if cached_response:
            print("Found cached response for sonnet prompts...")
            return cached_response

    message = Anthropic().messages.create(
        model="claude-3-5-sonnet-20240620",
        system=system_prompt,
        temperature=temperature,
        max_tokens=4096,
        messages=[{"role": "user", "content": [{"type": "text", "text": user_prompt}]}],
    )
    response = message.content[0].text # type: ignore

    if caching_enabled:
        _cache_response(prompts, response, SONNET_CACHE_FILE)

    return response
