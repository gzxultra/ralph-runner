"""Basic tests for ralph-runner utilities."""

from ralph_runner.display import fmt_duration, fmt_tokens
from ralph_runner.prompt import sanitize_prefix, build_prompt, COMPLETION_SIGNAL
from ralph_runner.verify import verify_trend_str, verify_sequence_str
from pathlib import Path
import tempfile


def test_fmt_duration_seconds():
    assert fmt_duration(30) == "30s"


def test_fmt_duration_minutes():
    assert fmt_duration(90) == "1m30s"


def test_fmt_tokens_small():
    assert fmt_tokens(500) == "500"


def test_fmt_tokens_thousands():
    assert fmt_tokens(5000) == "5K"


def test_fmt_tokens_millions():
    assert fmt_tokens(1_500_000) == "1.5M"


def test_sanitize_prefix():
    assert sanitize_prefix("Fix the login bug") == "fix-the-login-bug"
    assert sanitize_prefix("") == "ralph"
    assert sanitize_prefix("!!!") == "ralph"


def test_build_prompt_first_iteration():
    with tempfile.TemporaryDirectory() as td:
        progress = Path(td) / "progress.md"
        progress.write_text("")
        prompt = build_prompt(
            user_prompt="Fix the bug",
            iteration=1,
            min_iterations=5,
            progress_file=progress,
            plan_file=None,
            verify_cmd="",
        )
        assert "Fix the bug" in prompt
        assert "Iteration 1" in prompt
        assert COMPLETION_SIGNAL in prompt


def test_build_prompt_later_iteration():
    with tempfile.TemporaryDirectory() as td:
        progress = Path(td) / "progress.md"
        progress.write_text("## Iteration 1\nDid some work\n")
        prompt = build_prompt(
            user_prompt="Fix the bug",
            iteration=2,
            min_iterations=5,
            progress_file=progress,
            plan_file=None,
            verify_cmd="make test",
        )
        assert "Iteration Discipline" in prompt
        assert "make test" in prompt
        assert "Did some work" in prompt


def test_verify_trend_str():
    assert verify_trend_str([]) == ""
    assert verify_trend_str([True, True]) == "(2/2)"
    assert "↑" in verify_trend_str([False, False, False, True, True, True])


def test_verify_sequence_str():
    assert verify_sequence_str([]) == ""
    result = verify_sequence_str([True, False, True])
    assert "✓" in result
    assert "✗" in result
    assert "2/3" in result
