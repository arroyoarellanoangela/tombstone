"""strip_json_fences is the single point every agent's JSON response passes
through. A live run lost an entire acquirer's discovery results to prose
wrapped around otherwise-valid JSON, so its edge cases are worth pinning.
"""

import json

from src.utils.llm import _is_transient_spawn_failure, strip_json_fences


def test_bare_json_is_unchanged():
    assert json.loads(strip_json_fences('[{"url": "https://x.com"}]')) == [{"url": "https://x.com"}]


def test_code_fences_are_stripped():
    raw = '```json\n[{"url": "https://x.com"}]\n```'
    assert json.loads(strip_json_fences(raw)) == [{"url": "https://x.com"}]


def test_prose_before_and_after_json_is_discarded():
    raw = 'Here are the deals I found:\n[{"url": "https://x.com"}]\nLet me know if you need more.'
    assert json.loads(strip_json_fences(raw)) == [{"url": "https://x.com"}]


def test_object_response_is_extracted_too():
    raw = 'Sure!\n{"status": "verified", "value": "Houlihan Lokey"}\nHope that helps.'
    assert json.loads(strip_json_fences(raw))["value"] == "Houlihan Lokey"


def test_brackets_inside_string_values_do_not_end_the_match():
    raw = '[{"snippet": "Acme [formerly Beta] was acquired"}]'
    assert json.loads(strip_json_fences(raw))[0]["snippet"] == "Acme [formerly Beta] was acquired"


def test_escaped_quote_inside_a_string_does_not_break_parsing():
    raw = r'[{"snippet": "the \"leading\" provider"}]'
    assert json.loads(strip_json_fences(raw))[0]["snippet"] == 'the "leading" provider'


def test_truncated_json_is_returned_untouched_for_the_caller_to_report():
    # No balanced closer — this must not silently become something parseable.
    raw = '[{"url": "https://x.com", "snippet": "cut off mid-'
    assert strip_json_fences(raw) == raw


def test_response_with_no_json_at_all_is_returned_untouched():
    assert strip_json_fences("I could not find anything.") == "I could not find anything."


class TestTransientSpawnDetection:
    """A live run lost a deal to 'Control request timeout: initialize'. That
    failure precedes any billing, so it is retried; a mid-response failure
    may already have been charged and is not."""

    def test_initialize_timeout_is_transient(self):
        assert _is_transient_spawn_failure(Exception("Control request timeout: initialize"))

    def test_closed_transport_is_transient(self):
        assert _is_transient_spawn_failure(Exception("Transport closed unexpectedly"))

    def test_credit_error_is_not_transient(self):
        # Retrying this would just burn time and produce the same failure.
        assert not _is_transient_spawn_failure(Exception("Your credit balance is too low"))

    def test_ordinary_error_is_not_transient(self):
        assert not _is_transient_spawn_failure(ValueError("bad JSON schema"))
