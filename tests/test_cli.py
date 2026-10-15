"""End-to-end CLI tests.

The CLI is exercised by feeding a scripted list of inputs to input(), which
keeps the interactive menu honest without manual typing.
"""

import pytest

from susu_tracker import cli


def _scripted_input(monkeypatch, answers):
    """Feed *answers* to input() and raise EOFError when exhausted."""
    answers = iter(answers)

    def fake_input(prompt: str = "") -> str:
        try:
            return next(answers)
        except StopIteration:
            raise EOFError from None

    monkeypatch.setattr("builtins.input", fake_input)


def test_cli_rejects_an_incomplete_week_then_completes_the_payout(monkeypatch, capsys):
    _scripted_input(
        monkeypatch,
        [
            "50",              # weekly contribution
            "1", "M1", "Ama",
            "1", "M2", "Kofi",
            "1", "M3", "Esi",
            "2", "M1", "50",
            "2", "M2", "50",
            "2", "M3", "30",
            "4",               # close: rejected, Esi still owes 20
            "2", "M3", "20",
            "4",               # close: payout to Ama
            "5",               # payout history
            "6",               # group report
            "0",               # exit
        ],
    )

    assert cli.main() == 0
    output = capsys.readouterr().out

    assert "Cannot close week 1: members still owe money." in output
    assert "Esi (M3) owes GHS 20.00" in output
    assert "No payout was recorded. Week 1 remains open." in output
    assert "Payout: GHS 150.00 to Ama (M1)." in output
    assert "Next recipient for week 2: Kofi (M2)." in output
    assert "Week 1: Ama (M1) received GHS 150.00" in output
    assert "Goodbye." in output


def test_cli_rejects_invalid_money_then_accepts_a_valid_group(monkeypatch, capsys):
    _scripted_input(monkeypatch, ["0", "50", "0"])

    assert cli.main() == 0
    output = capsys.readouterr().out

    assert "Weekly contribution must be greater than zero." in output
    assert "Weekly contribution set to GHS 50.00." in output


def test_cli_reports_bad_amounts_and_unknown_options(monkeypatch, capsys):
    _scripted_input(
        monkeypatch,
        [
            "50",
            "1", "M1", "Ama",
            "9",               # unknown menu option
            "3",               # week status
            "2", "M1", "abc",  # invalid amount
            "0",
        ],
    )

    assert cli.main() == 0
    output = capsys.readouterr().out

    assert "Unknown option '9'." in output
    assert "Week 1 payment status:" in output
    assert "Ama (M1): paid GHS 0.00, owed GHS 50.00" in output
    assert "is not a valid money amount" in output
    assert "Goodbye." in output


def test_cli_handles_end_of_input_gracefully(monkeypatch, capsys):
    _scripted_input(monkeypatch, ["50"])
    assert cli.main() == 0
    assert "Goodbye." in capsys.readouterr().out
