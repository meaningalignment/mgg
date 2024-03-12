def serialize(obj) -> dict | list:
    if isinstance(obj, list):
        return [serialize(item) for item in obj]
    elif hasattr(obj, "__dict__"):
        return {key: serialize(value) for key, value in obj.__dict__.items()}
    else:
        return obj


def calculate_price(input_tokens, output_tokens):
    # using pricing for gpt-4-0125-preview
    return (input_tokens * 10 + output_tokens * 30) / 1_000_000
