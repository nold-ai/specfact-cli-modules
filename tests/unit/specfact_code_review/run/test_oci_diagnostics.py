"""OCI integrity failures identify the observed and expected descriptor."""

import hashlib

import pytest

from specfact_code_review.run import toolchain


@pytest.mark.parametrize("payload,expected_size", [(b"changed", 7), (b"changed", 8)])
def test_customer_oci_mismatch_identifies_digest_and_size(payload, expected_size):
    expected = "sha256:" + "0" * 64
    actual = "sha256:" + hashlib.sha256(payload).hexdigest()
    with pytest.raises(ValueError) as failure:
        toolchain._validate_oci_payload(payload, digest=expected, expected_size=expected_size)
    reason = str(failure.value)
    assert "expected_digest=" + expected in reason
    assert "actual_digest=" + actual in reason
    assert "expected_size=" + str(expected_size) in reason
    assert "actual_size=" + str(len(payload)) in reason
