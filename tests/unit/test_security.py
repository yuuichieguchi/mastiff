"""Tests for sentinel.security — patterns, redactor, sanitizer."""


class TestSecretPatterns:
    """SECRET_PATTERNS regex list tests."""

    def test_detects_openai_key(self):
        from sentinel.security.patterns import SECRET_PATTERNS

        text = 'api_key = "sk-abc123def456ghi789"'
        assert any(p.search(text) for p in SECRET_PATTERNS)

    def test_detects_github_token(self):
        from sentinel.security.patterns import SECRET_PATTERNS

        text = 'token = "ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ012345"'
        assert any(p.search(text) for p in SECRET_PATTERNS)

    def test_detects_aws_key(self):
        from sentinel.security.patterns import SECRET_PATTERNS

        text = 'aws_key = "AKIAIOSFODNN7EXAMPLE"'
        assert any(p.search(text) for p in SECRET_PATTERNS)

    def test_detects_bearer_token(self):
        from sentinel.security.patterns import SECRET_PATTERNS

        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIs"
        assert any(p.search(text) for p in SECRET_PATTERNS)

    def test_detects_generic_api_key_assignment(self):
        from sentinel.security.patterns import SECRET_PATTERNS

        text = 'api_key = "someSecretValue12345678"'
        assert any(p.search(text) for p in SECRET_PATTERNS)

    def test_detects_password_assignment(self):
        from sentinel.security.patterns import SECRET_PATTERNS

        text = 'password = "super_secret_password_123"'
        assert any(p.search(text) for p in SECRET_PATTERNS)

    def test_ignores_normal_code(self):
        from sentinel.security.patterns import SECRET_PATTERNS

        text = "x = 42\nfor i in range(10):\n    print(i)"
        assert not any(p.search(text) for p in SECRET_PATTERNS)

    def test_ignores_short_strings(self):
        from sentinel.security.patterns import SECRET_PATTERNS

        text = 'name = "hello"'
        assert not any(p.search(text) for p in SECRET_PATTERNS)

    def test_ignores_key_comments(self):
        from sentinel.security.patterns import SECRET_PATTERNS

        text = "# You need an API key to use this service"
        assert not any(p.search(text) for p in SECRET_PATTERNS)


class TestRedactor:
    """Redactor class tests."""

    def test_redacts_api_key(self):
        from sentinel.security.redactor import Redactor

        r = Redactor()
        text = 'key = "sk-abc123def456ghi789jkl"'
        result, count = r.redact(text)
        assert "[REDACTED]" in result
        assert "sk-abc123" not in result
        assert count >= 1

    def test_preserves_normal_code(self):
        from sentinel.security.redactor import Redactor

        r = Redactor()
        text = "def hello():\n    return 42"
        result, count = r.redact(text)
        assert result == text
        assert count == 0

    def test_high_entropy_detection(self):
        from sentinel.security.redactor import Redactor

        r = Redactor()
        # High entropy string (random-looking)
        assert r.is_high_entropy("aB3xK9mP2qR7wY4zL8nT5vJ1cF6hD0g") is True
        # Low entropy string
        assert r.is_high_entropy("aaaaaaaaaaaaaaaaaaaaaa") is False

    def test_short_strings_skip_entropy(self):
        from sentinel.security.redactor import Redactor

        r = Redactor(min_entropy_length=20)
        assert r.is_high_entropy("aB3xK9") is False  # too short

    def test_path_exclusion(self):
        from sentinel.security.redactor import Redactor

        r = Redactor()
        never_send = [".env", "*.pem", "*.key", "*credentials*", "**/secrets/**"]
        assert r.should_exclude_path(".env", never_send) is True
        assert r.should_exclude_path("certs/server.pem", never_send) is True
        assert r.should_exclude_path("config/credentials.json", never_send) is True
        assert r.should_exclude_path("src/main.py", never_send) is False

    def test_multiple_redactions(self):
        from sentinel.security.redactor import Redactor

        r = Redactor()
        text = 'key1 = "sk-first123456789abcdef"\nkey2 = "ghp_second12345678901234567890"'
        result, count = r.redact(text)
        assert count >= 2
        assert "sk-first" not in result
        assert "ghp_second" not in result

    def test_custom_patterns(self):
        import re

        from sentinel.security.redactor import Redactor

        custom = [re.compile(r"MY_TOKEN_\w+")]
        r = Redactor(patterns=custom)
        text = "secret = MY_TOKEN_abc123"
        result, count = r.redact(text)
        assert "[REDACTED]" in result
        assert count >= 1

    def test_redact_returns_tuple(self):
        from sentinel.security.redactor import Redactor

        r = Redactor()
        result = r.redact("clean text")
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], str)
        assert isinstance(result[1], int)


class TestSanitizer:
    """sanitize_output and sanitize_for_log tests."""

    def test_removes_ansi_escapes(self):
        from sentinel.security.sanitizer import sanitize_output

        text = "\x1b[31mred text\x1b[0m"
        assert sanitize_output(text) == "red text"

    def test_removes_control_characters(self):
        from sentinel.security.sanitizer import sanitize_output

        text = "hello\x00world\x07"
        assert sanitize_output(text) == "helloworld"

    def test_preserves_newlines_and_tabs(self):
        from sentinel.security.sanitizer import sanitize_output

        text = "line1\nline2\ttab"
        assert sanitize_output(text) == "line1\nline2\ttab"

    def test_sanitize_for_log_escapes(self):
        from sentinel.security.sanitizer import sanitize_for_log

        text = "hello\x1b[31mworld\x00"
        result = sanitize_for_log(text)
        assert "\x1b" not in result
        assert "\x00" not in result
        # Should contain escaped representation
        assert "\\x" in result or "\\u" in result

    def test_clean_text_unchanged(self):
        from sentinel.security.sanitizer import sanitize_output

        text = "Normal text with no special chars."
        assert sanitize_output(text) == text

    def test_complex_ansi_sequences(self):
        from sentinel.security.sanitizer import sanitize_output

        text = "\x1b[1;32;40mBold green\x1b[0m normal"
        assert sanitize_output(text) == "Bold green normal"

    def test_sanitize_for_log_preserves_readable_text(self):
        from sentinel.security.sanitizer import sanitize_for_log

        text = "Normal log message"
        assert sanitize_for_log(text) == "Normal log message"
