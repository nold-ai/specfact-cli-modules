import requests


def build_client() -> requests.Session:
    return requests.Session()
