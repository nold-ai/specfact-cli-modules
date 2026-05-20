def canonicalize(value: str) -> str:
    return value.strip()


callbacks = [canonicalize]
