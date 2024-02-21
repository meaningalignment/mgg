import openai

client = openai.OpenAI()


def gpt4(
    user_prompt: str,
    system_prompt: str | None = None,
    function: dict | None = None,
    temperature: float = 0.0,
) -> str:
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

    return (
        result.choices[0].message.function_call.arguments
        if function
        else result.choices[0].message.content.strip()
    )
