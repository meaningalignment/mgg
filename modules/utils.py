import re


def serialize(obj) -> dict | list:
    if isinstance(obj, list):
        return [serialize(item) for item in obj]
    elif hasattr(obj, "__dict__"):
        return {key: serialize(value) for key, value in obj.__dict__.items()}
    else:
        return obj


def calculate_gp4_turbo_price(input_tokens, output_tokens):
    return (input_tokens * 10 + output_tokens * 30) / 1_000_000


def parse_to_dict(text):
    sections = text.split("#")
    result = {}
    for section in sections[1:]:  # Skip the first split as it's before the first header
        if "\n" in section:
            header, content = section.split("\n", 1)
            result[header.strip()] = content.strip()
    return result


def count_sentences(text: str) -> int:
    return len([s for s in re.split(r"[.!?]+\s*", text.strip()) if s])


def retry(times=3):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for _ in range(times):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    print(f"Error: {e}")
            return None

        return wrapper

    return decorator
