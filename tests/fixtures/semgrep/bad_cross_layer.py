def sync_order(order_id: str, repository: object, http_client: object) -> object:
    order = repository.find_by_id(order_id)
    http_client.post("/events", json={"id": order_id})
    return order
