class Counter:
    def __init__(self, value: int) -> None:
        self.value = value

    def get_and_increment(self) -> int:
        current = self.value
        self.value = current + 1
        return current
