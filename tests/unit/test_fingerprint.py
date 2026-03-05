"""Tests for mastiff.core.fingerprint — stable Finding ID generation."""


class TestFingerprint:
    """Fingerprint generation tests."""

    def test_same_code_same_fingerprint(self):
        from mastiff.core.fingerprint import generate_fingerprint
        fp1 = generate_fingerprint("blocking-sync-in-async", "    time.sleep(1)")
        fp2 = generate_fingerprint("blocking-sync-in-async", "    time.sleep(1)")
        assert fp1 == fp2

    def test_different_rule_different_fingerprint(self):
        from mastiff.core.fingerprint import generate_fingerprint
        fp1 = generate_fingerprint("blocking-sync-in-async", "time.sleep(1)")
        fp2 = generate_fingerprint("race-shared-state", "time.sleep(1)")
        assert fp1 != fp2

    def test_different_code_different_fingerprint(self):
        from mastiff.core.fingerprint import generate_fingerprint
        fp1 = generate_fingerprint("blocking-sync-in-async", "time.sleep(1)")
        fp2 = generate_fingerprint("blocking-sync-in-async", "await asyncio.sleep(1)")
        assert fp1 != fp2

    def test_whitespace_normalization(self):
        from mastiff.core.fingerprint import generate_fingerprint
        fp1 = generate_fingerprint("rule", "  x = 1  ")
        fp2 = generate_fingerprint("rule", "x = 1")
        assert fp1 == fp2

    def test_fingerprint_is_hex_string(self):
        from mastiff.core.fingerprint import generate_fingerprint
        fp = generate_fingerprint("rule", "code")
        assert isinstance(fp, str)
        # Should be a valid hex string
        int(fp, 16)

    def test_fingerprint_stable_length(self):
        from mastiff.core.fingerprint import generate_fingerprint
        fp1 = generate_fingerprint("a", "b")
        fp2 = generate_fingerprint("long-rule-id-here", "lots of code content here")
        assert len(fp1) == len(fp2)


class TestFindingFingerprint:
    """Test fingerprint generation from Finding objects."""

    def test_fingerprint_from_finding(self):
        from mastiff.core.fingerprint import fingerprint_finding
        from mastiff.core.models import DetectionCategory, FindingSchema
        from mastiff.core.severity import Severity
        finding = FindingSchema(
            rule_id="blocking-sync-in-async",
            category=DetectionCategory.BLOCKING,
            severity=Severity.CRITICAL,
            file_path="src/main.py",
            line_start=42,
            title="Sync in async",
            explanation="time.sleep blocks event loop",
            confidence=0.9,
        )
        fp = fingerprint_finding(finding, code_snippet="    time.sleep(1)")
        assert isinstance(fp, str)
        assert len(fp) > 0

    def test_fingerprint_independent_of_line_number(self):
        from mastiff.core.fingerprint import fingerprint_finding
        from mastiff.core.models import DetectionCategory, FindingSchema
        from mastiff.core.severity import Severity
        f1 = FindingSchema(
            rule_id="blocking-sync-in-async",
            category=DetectionCategory.BLOCKING,
            severity=Severity.CRITICAL,
            file_path="src/main.py",
            line_start=42,
            title="Sync in async",
            explanation="blocks",
            confidence=0.9,
        )
        f2 = FindingSchema(
            rule_id="blocking-sync-in-async",
            category=DetectionCategory.BLOCKING,
            severity=Severity.CRITICAL,
            file_path="src/main.py",
            line_start=99,  # different line
            title="Sync in async",
            explanation="blocks",
            confidence=0.9,
        )
        snippet = "time.sleep(1)"
        assert fingerprint_finding(f1, snippet) == fingerprint_finding(f2, snippet)
