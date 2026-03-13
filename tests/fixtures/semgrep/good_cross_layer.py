def load_order(order_id: str, repository: object) -> object:
    return repository.find_by_id(order_id)
