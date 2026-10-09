import copy

import pytest

from scripts.native_release import environment


@pytest.fixture
def protected_environment():
    return {
        "name": "native-capsule-signing",
        "can_admins_bypass": False,
        "deployment_branch_policy": {"protected_branches": True, "custom_branch_policies": False},
        "protection_rules": [
            {
                "type": "required_reviewers",
                "prevent_self_review": True,
                "reviewers": [{"type": "User", "reviewer": {"id": 1}}],
            }
        ],
    }


def test_explicit_protected_human_environment_is_required(protected_environment):
    environment.validate_environment(protected_environment, "native-capsule-signing")


@pytest.mark.parametrize(
    "path,value",
    [
        (("protection_rules",), []),
        (("protection_rules", 0, "prevent_self_review"), False),
        (("can_admins_bypass",), True),
        (("deployment_branch_policy",), None),
        (("name",), "unprotected"),
        (("can_admins_bypass",), 0),
    ],
)
def test_missing_or_weakened_environment_never_admits_signing(protected_environment, path, value):
    document = copy.deepcopy(protected_environment)
    parent = document
    for field in path[:-1]:
        parent = parent[field]
    parent[path[-1]] = value
    with pytest.raises(ValueError, match="environment"):
        environment.validate_environment(document, "native-capsule-signing")
