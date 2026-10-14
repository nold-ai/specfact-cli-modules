import io as stdio

import pytest

from specfact_code_review.run import target_crosshair


_stream_sink = vars(target_crosshair)["_TargetOutput"]


def test_discard_custom_error_handler_matches_one_native_encoding_pass():
    import codecs
    from uuid import uuid4

    calls = []

    def replace_once(error):
        calls.append((error.encoding, error.start, error.end))
        if len(calls) != 1:
            raise RuntimeError("error handler called twice")
        return "?", error.end

    handler = "specfact_" + uuid4().hex
    codecs.register_error(handler, replace_once)
    with stdio.TextIOWrapper(stdio.BytesIO(), encoding="ascii", errors=handler) as native:
        expected = native.write("\ud800")
        native.flush()
        expected_calls = calls.copy()
    assert expected_calls == [("ascii", 0, 1)]
    calls.clear()
    with _stream_sink() as sink:
        sink.reconfigure(encoding="ascii", errors=handler)
        assert sink.write("\ud800") == expected
    assert calls == expected_calls


def test_discard_utf7_strict_accepts_native_lone_surrogate():
    with stdio.TextIOWrapper(stdio.BytesIO(), encoding="utf-7", errors="strict") as native:
        expected = native.write("\ud800")
        native.flush()
    with _stream_sink() as sink:
        sink.reconfigure(encoding="utf-7", errors="strict")
        assert sink.write("\ud800") == expected


def test_discard_native_encoding_failure_calls_handler_once():
    import codecs
    from uuid import uuid4

    calls = []

    def reject(error):
        calls.append((error.encoding, error.start, error.end))
        raise error

    handler = "specfact_" + uuid4().hex
    codecs.register_error(handler, reject)
    with (
        stdio.TextIOWrapper(stdio.BytesIO(), encoding="ascii", errors=handler) as native,
        pytest.raises(UnicodeEncodeError) as expected,
    ):
        native.write("é")
    expected_calls = calls.copy()
    assert expected_calls == [("ascii", 0, 1)]
    calls.clear()
    with _stream_sink() as sink:
        sink.reconfigure(encoding="ascii", errors=handler)
        with pytest.raises(UnicodeEncodeError) as actual:
            sink.write("é")
        assert sink.write("x") == 1
    assert str(actual.value) == str(expected.value)
    assert calls == expected_calls


def test_discard_quota_does_not_call_string_overrides():
    class NativeText(str):
        def encode(self, *args, **kwargs):
            raise AssertionError("quota called custom encode")

        def __iter__(self):
            raise AssertionError("quota called custom iteration")

    text = NativeText("é\ud800")
    with stdio.TextIOWrapper(stdio.BytesIO(), encoding="ascii", errors="replace") as native:
        expected = native.write(text)
    with _stream_sink() as sink:
        sink.reconfigure(encoding="ascii", errors="replace")
        assert sink.write(text) == expected


def test_discard_quota_does_not_call_registered_surrogatepass():
    import codecs

    original = codecs.lookup_error("surrogatepass")

    def reject(error):
        raise AssertionError("quota called registered surrogatepass")

    try:
        codecs.register_error("surrogatepass", reject)
        with _stream_sink() as sink:
            sink.reconfigure(encoding="ascii", errors="replace")
            assert sink.write("\ud800") == 1
    finally:
        codecs.register_error("surrogatepass", original)


@pytest.mark.parametrize("errors", ["ignore", "replace", "backslashreplace"])
def test_discard_surrogate_uses_three_logical_bytes_at_exact_bound(errors):
    with _stream_sink() as sink:
        sink.reconfigure(encoding="latin-1", errors="strict")
        prefix = "é" * (2 * 1024 * 1024 - 2)
        assert sink.write(prefix) == len(prefix)
        sink.reconfigure(encoding="ascii", errors=errors)
        assert sink.write("\ud800") == 1
        assert sink.write("x") == 1
        with pytest.raises(ValueError, match="crosshair_target_output_limit_exceeded"):
            sink.write("x")


def test_discard_scalar_widths_retain_exact_logical_bound():
    with _stream_sink() as sink:
        sink.reconfigure(encoding="latin-1", errors="strict")
        prefix = "é" * (2 * 1024 * 1024 - 10)
        assert sink.write(prefix) == len(prefix)
        sink.reconfigure(encoding="ascii", errors="replace")
        assert sink.write("x\x7f\x80\u07ff\u0800\uffff\U00010000\U0010ffff") == 8
        with pytest.raises(ValueError, match="crosshair_target_output_limit_exceeded"):
            sink.write("x")


def test_discard_surrogate_escape_keeps_mixed_physical_bound():
    with _stream_sink() as sink:
        sink.reconfigure(encoding="ascii", errors="backslashreplace")
        assert sink.buffer.write(b"x" * (4 * 1024 * 1024 - 7)) == 4 * 1024 * 1024 - 7
        assert sink.write("\ud800") == 1
        assert sink.buffer.raw.write(b"x") == 1
        with pytest.raises(ValueError, match="crosshair_target_output_limit_exceeded"):
            sink.write("x")
