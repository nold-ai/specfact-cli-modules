def read_value(obj: object) -> object | None:
    config = obj.config if obj is not None else None
    if config is None:
        return None
    return config.value
