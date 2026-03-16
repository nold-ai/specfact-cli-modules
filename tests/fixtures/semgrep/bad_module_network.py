import requests


CLIENT = requests.Session()


def fetch_status(url: str) -> int:
    response = CLIENT.get(url, timeout=5)
    return response.status_code
