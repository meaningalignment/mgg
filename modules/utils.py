import numpy as np
from numpy import dot
from numpy.linalg import norm


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


def parse_to_dict(text):
    sections = text.split("#")
    result = {}
    for section in sections[1:]:  # Skip the first split as it's before the first header
        if "\n" in section:
            header, content = section.split("\n", 1)
            result[header.strip()] = content.strip()
    return result


def cosine_distance(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    return 1.0 - dot(vec_a, vec_b) / (norm(vec_a) * norm(vec_b))
