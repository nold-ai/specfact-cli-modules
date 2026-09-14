"""Builder inventories retain dependency facts without credentials."""


def test_inventory_never_serializes_index_credentials() -> None:
    from specfact_code_review.run.runtime_build_driver import clean_inventory

    inventory = clean_inventory(
        {
            "installed": [
                {
                    "metadata": {
                        "name": "consumer",
                        "version": "1",
                        "description": "do not retain arbitrary metadata",
                        "requires_dist": ["dependency @ https://user:secret@example.test/pkg.whl?token=secret"],
                    },
                    "direct_url": {"url": "https://user:secret@example.test/pkg.whl?token=secret"},
                }
            ]
        }
    )
    import json

    encoded = json.dumps(inventory)
    assert "secret" not in encoded
    assert "description" not in encoded
    assert "example.test/pkg.whl" in encoded
