"""strip_json_fences is the single point every agent's JSON response passes
through. A live run lost an entire acquirer's discovery results to prose
wrapped around otherwise-valid JSON, so its edge cases are worth pinning.
"""

import json

from src.utils import llm
from src.utils.llm import _account_failure, _is_transient_spawn_failure, strip_json_fences


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


class TestAccountFailureDetection:
    """The CLI returns account failures as ordinary assistant text, so every
    agent parsed 'Credit balance is too low' as unparseable output and
    reported zero results. An exhausted key must not look like an honest
    finding of no acquisitions."""

    def test_credit_exhaustion_is_detected(self):
        assert _account_failure("Credit balance is too low") == "credit balance is too low"

    def test_auth_error_is_detected(self):
        assert _account_failure("authentication_error: invalid x-api-key") is not None

    def test_normal_json_response_is_not_flagged(self):
        assert _account_failure('[{"url": "https://x.com"}]') is None

    def test_long_extraction_quoting_the_phrase_is_not_flagged(self):
        # A genuine article could discuss a company's credit balance; only
        # short, bare refusals should stop the run.
        text = (
            '{"target": {"status": "verified", "value": "Acme", "quote": "the group '
            'noted its credit balance is too low to fund further acquisitions this '
            'year, according to the filing published alongside the announcement"}}'
        )
        assert _account_failure(text) is None


class TestSubprocessEnvironment:
    """A live run produced 'Informática'/'IVèS' back as mojibake — the
    classic UTF-8-decoded-as-Windows-codepage signature. Forcing UTF-8 mode
    on the subprocess is the fix; this pins it so a future refactor can't
    quietly drop it."""

    def test_forces_utf8_mode(self):
        env = llm._subprocess_env()
        assert env["PYTHONUTF8"] == "1"
        assert env["PYTHONIOENCODING"] == "utf-8"

    def test_still_isolates_from_a_developer_login(self):
        env = llm._subprocess_env()
        assert env["HOME"] == env["USERPROFILE"] == llm._ISOLATED_HOME
        assert env["CLAUDECODE"] == ""
