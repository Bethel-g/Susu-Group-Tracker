"""Reporting tests (FR-08, US-04, US-08, US-09)."""

import re
from decimal import Decimal

import pytest

from susu_tracker.exceptions import UnknownWeekError
from susu_tracker.money import format_money
from susu_tracker.susu_service import SusuService

MONEY_PATTERN = r"^GHS [\d,]+\.\d{2}$"


def test_report_before_any_payment(three_members: SusuService):
    report = three_members.get_report()
    assert report.current_week == 1
    assert report.rotation_status == "Active"
    assert report.is_complete is False
    assert report.pot == Decimal("150.00")
    assert report.next_recipient_name == "Ama"
    assert report.payout_history == []
    assert [(b.paid, b.balance) for b in report.members] == [
        (Decimal("0.00"), Decimal("50.00"))
    ] * 3


def test_report_lists_every_member_with_paid_and_owed(three_members: SusuService):
    three_members.record_contribution("M1", "50.00")
    three_members.record_contribution("M3", "30.00")

    report = three_members.get_report()
    assert [(b.name, b.paid, b.balance) for b in report.members] == [
        ("Ama", Decimal("50.00"), Decimal("0.00")),
        ("Kofi", Decimal("0.00"), Decimal("50.00")),
        ("Esi", Decimal("30.00"), Decimal("20.00")),
    ]


def test_report_shows_payout_history_after_closure(three_members: SusuService, pay_all):
    pay_all("50.00")
    three_members.close_week()

    report = three_members.get_report()
    assert report.current_week == 2
    assert report.rotation_status == "Active"
    assert len(report.payout_history) == 1
    payout = report.payout_history[0]
    assert (payout.week_number, payout.recipient_id, payout.amount) == (
        1,
        "M1",
        Decimal("150.00"),
    )


def test_report_marks_a_completed_rotation(three_members: SusuService, pay_all):
    for _ in range(3):
        pay_all("50.00")
        three_members.close_week()

    report = three_members.get_report()
    assert report.is_complete is True
    assert report.rotation_status == "Complete"
    assert report.next_recipient_name is None
    assert [payout.recipient_id for payout in report.payout_history] == ["M1", "M2", "M3"]


def test_week_status_is_available_for_a_closed_week(three_members: SusuService, pay_all):
    pay_all("50.00")
    three_members.close_week()

    balances = three_members.get_week_status(1)
    assert all(balance.paid == Decimal("50.00") for balance in balances)
    assert all(balance.balance == Decimal("0.00") for balance in balances)


def test_unknown_week_status_is_rejected(three_members: SusuService):
    with pytest.raises(UnknownWeekError):
        three_members.get_week_status(99)


def test_all_report_money_uses_two_decimal_format(three_members: SusuService):
    three_members.record_contribution("M3", "30.00")
    report = three_members.get_report()

    values = [report.weekly_contribution, report.pot]
    values += [b.paid for b in report.members] + [b.balance for b in report.members]
    assert all(re.match(MONEY_PATTERN, format_money(value)) for value in values)
