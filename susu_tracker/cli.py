"""Command-line interface for Susu Group Tracker.

This layer only collects input and formats output; every financial rule is
enforced by SusuService and the domain model.
"""

from __future__ import annotations

from .exceptions import IncompleteWeekError, SusuError
from .money import format_money
from .susu_service import SusuService

MENU = """1. Add member
2. Record contribution
3. View current week status
4. Close current week
5. View payout history
6. View group report
0. Exit"""


def main() -> int:
    """Run the interactive menu until the organizer exits."""
    print("=== Susu Group Tracker ===")
    service = SusuService()
    try:
        _ensure_group(service)
        while True:
            _print_status(service)
            choice = _prompt("Select an option: ")
            if choice == "0":
                print("Goodbye.")
                return 0
            try:
                _dispatch(choice, service)
            except SusuError as exc:
                print(f"Error: {exc}")
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye.")
        return 0


# -- menu plumbing -----------------------------------------------------


def _ensure_group(service: SusuService) -> None:
    while not service.has_group():
        raw = _prompt("Enter the weekly contribution per member in GHS: ")
        try:
            group = service.create_group(raw)
        except SusuError as exc:
            print(f"Error: {exc}")
            continue
        print(f"Weekly contribution set to {format_money(group.weekly_contribution)}.")


def _prompt(message: str) -> str:
    return input(message).strip()


def _print_status(service: SusuService) -> None:
    group = service.get_group()
    print()
    print("-" * 40)
    print(f"Weekly contribution: {format_money(group.weekly_contribution)}")
    print(f"Current week: {group.current_week}")
    print(f"Rotation status: {group.rotation_status}")
    print("-" * 40)
    print(MENU)


def _dispatch(choice: str, service: SusuService) -> None:
    if choice == "1":
        _add_member(service)
    elif choice == "2":
        _record_contribution(service)
    elif choice == "3":
        _view_week_status(service)
    elif choice == "4":
        _close_week(service)
    elif choice == "5":
        _view_payout_history(service)
    elif choice == "6":
        _view_report(service)
    else:
        print(f"Unknown option '{choice}'. Please choose from the menu.")


# -- menu actions ------------------------------------------------------


def _add_member(service: SusuService) -> None:
    member_id = _prompt("Member ID: ")
    name = _prompt("Member name: ")
    member = service.add_member(member_id, name)
    print(f"Registered {member.name} ({member.member_id}) as member #{member.join_order}.")


def _record_contribution(service: SusuService) -> None:
    group = service.get_group()
    member_id = _prompt("Member ID: ")
    raw_amount = _prompt("Amount in GHS: ")
    contribution = service.record_contribution(member_id, raw_amount)
    member = group.get_member(contribution.member_id)
    balance = service.get_member_balance(contribution.member_id, group.current_week)
    print(
        f"Recorded {format_money(contribution.amount)} for {member.name}. "
        f"Outstanding balance: {format_money(balance)}."
    )


def _view_week_status(service: SusuService) -> None:
    group = service.get_group()
    balances = service.get_week_status(group.current_week)
    print(f"Week {group.current_week} payment status:")
    if not balances:
        print("  No members registered yet.")
        return
    for balance in balances:
        print(
            f"  {balance.name} ({balance.member_id}): "
            f"paid {format_money(balance.paid)}, owed {format_money(balance.balance)}"
        )
    owing = [balance for balance in balances if balance.balance > 0]
    if not owing:
        print(f"Week {group.current_week} is ready to close.")
    elif len(owing) == 1:
        print(f"Week {group.current_week} cannot be closed yet: 1 member still owes money.")
    else:
        print(
            f"Week {group.current_week} cannot be closed yet: "
            f"{len(owing)} members still owe money."
        )


def _close_week(service: SusuService) -> None:
    group = service.get_group()
    try:
        payout = service.close_week()
    except IncompleteWeekError as exc:
        print(f"Cannot close week {group.current_week}: members still owe money.")
        for balance in exc.outstanding:
            print(f"  {balance.name} ({balance.member_id}) owes {format_money(balance.balance)}")
        print(f"No payout was recorded. Week {group.current_week} remains open.")
        return

    recipient = group.get_member(payout.recipient_id)
    print(f"Week {payout.week_number} closed.")
    print(f"Payout: {format_money(payout.amount)} to {recipient.name} ({recipient.member_id}).")
    if group.is_complete:
        print(
            f"Rotation complete: all {len(group.members)} members have received a payout."
        )
    else:
        next_recipient = group.next_recipient
        print(
            f"Next recipient for week {group.current_week}: "
            f"{next_recipient.name} ({next_recipient.member_id})."
        )


def _view_payout_history(service: SusuService) -> None:
    group = service.get_group()
    payouts = service.get_payout_history()
    if not payouts:
        print("No payouts recorded yet.")
        return
    print("Payout history:")
    for payout in payouts:
        recipient = group.get_member(payout.recipient_id)
        print(
            f"  Week {payout.week_number}: {recipient.name} ({recipient.member_id}) "
            f"received {format_money(payout.amount)}"
        )


def _view_report(service: SusuService) -> None:
    group = service.get_group()
    report = service.get_report()
    print("======== Group report ========")
    print(f"Weekly contribution: {format_money(report.weekly_contribution)}")
    print(f"Current week: {report.current_week}")
    print(f"Rotation status: {report.rotation_status}")
    print(f"Weekly pot: {format_money(report.pot)}")
    print(f"Next recipient: {report.next_recipient_name or 'none'}")

    print()
    print(f"Payment status for week {report.current_week}:")
    if not report.members:
        print("  No members registered yet.")
    for balance in report.members:
        print(
            f"  {balance.name} ({balance.member_id}): "
            f"paid {format_money(balance.paid)}, owed {format_money(balance.balance)}"
        )

    print()
    if report.payout_history:
        print("Payout history:")
        for payout in report.payout_history:
            recipient = group.get_member(payout.recipient_id)
            print(
                f"  Week {payout.week_number}: {recipient.name} ({recipient.member_id}) "
                f"received {format_money(payout.amount)}"
            )
    else:
        print("Payout history: none yet.")


if __name__ == "__main__":
    raise SystemExit(main())
