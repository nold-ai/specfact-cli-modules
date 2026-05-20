def canonicalize(value: str) -> str:
    return value.strip()


callbacks = [lambda value: canonicalize(value)]
