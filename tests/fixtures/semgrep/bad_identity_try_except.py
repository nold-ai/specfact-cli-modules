def parse(raw: str) -> int:
    try:
        return int(raw)
    except ValueError:
        raise
