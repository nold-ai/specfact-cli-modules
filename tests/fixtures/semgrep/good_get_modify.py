class Counter:
    def __init__(self, value: int) -> None:
        self.value = value

    def get_value(self) -> int:
        return self.value

    def increment(self) -> None:
        self.value = self.value + 1
