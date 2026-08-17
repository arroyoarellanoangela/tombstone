"""html_to_text is what turns a ~30x-noisier raw page into what Research and
the Verifier actually read/match against — worth its own coverage.
"""

import pytest

from src.utils.fetch import html_to_text, is_allowed


class TestIsAllowed:
    def test_exact_domain_match_is_allowed(self):
        assert is_allowed("https://volarisgroup.com/press-room/x")[0] is True

    def test_www_prefix_is_ignored(self):
        assert is_allowed("https://www.volarisgroup.com/press-room/x")[0] is True

    def test_subdomain_is_covered_by_its_parent_entry(self):
        # The brief points at news.banyansoftware.com; the allowlist names
        # the apex. Both must work, or real coverage silently disappears.
        assert is_allowed("https://news.banyansoftware.com/acme")[0] is True

    def test_lookalike_domain_does_not_match_by_suffix(self):
        # Matching must be dot-anchored, not a bare string suffix.
        assert is_allowed("https://notbanyansoftware.com/x")[0] is False

    def test_unknown_domain_fails_closed(self):
        allowed, reason = is_allowed("https://random-news-site.example/x")
        assert allowed is False
        assert "not in allowlist" in reason

    @pytest.mark.parametrize(
        "url",
        [
            "https://linkedin.com/posts/x",
            "https://www.linkedin.com/posts/x",
            "https://mergermarket.com/deal/x",
        ],
    )
    def test_explicitly_blocked_domains_stay_blocked(self, url):
        assert is_allowed(url)[0] is False


def test_strips_tags_and_collapses_whitespace():
    html = "<html><body><p>Volaris   Group\n  acquired  <b>Acme</b>.</p></body></html>"
    assert html_to_text(html) == "Volaris Group acquired Acme ."


def test_strips_script_and_style_blocks_entirely():
    html = (
        "<head><style>.x{color:red}</style></head>"
        "<body><script>trackEverything();</script>"
        "<p>Real article text.</p></body>"
    )
    assert html_to_text(html) == "Real article text."


def test_strips_nav_and_footer_boilerplate():
    html = (
        "<nav>Home | About | Contact</nav>"
        "<main>Volaris Group acquired Acme Software.</main>"
        "<footer>(c) 2026 Volaris Group. All rights reserved.</footer>"
    )
    assert html_to_text(html) == "Volaris Group acquired Acme Software."


def test_plain_text_with_no_tags_is_left_intact():
    text = "Volaris Group today announced it has acquired Acme Software."
    assert html_to_text(text) == text
