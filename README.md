# Susu Group Tracker

A small, reliable Python command-line application for managing a rotating
savings group ("susu"), in which every member contributes a fixed amount each
week and, one member per week, receives the whole weekly pot in registration
order.

The goal is not to be a large application. It is to handle money exactly,
enforce the savings rules, prevent incorrect payouts, and stay easy for another
engineer to read and test.

> **Key invariant:** `weekly pot = weekly contribution × number of members`.
> Three members contributing GHS 50.00 each produce a pot of GHS 150.00.

## Table of contents

- [Quick start](#quick-start)
- [Overview](#overview)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Example session](#example-session)
- [Business rules](#business-rules)
- [Testing](#testing)
- [Project structure](#project-structure)
- [Design notes](#design-notes)

## Quick start

From a fresh clone, with no third-party runtime dependencies:

```bash
git clone <repository-url>
cd susu-group-tracker
python -m pip install -r requirements.txt   # installs pytest for the tests

python -m susu_tracker.cli                  # run the application
python -m pytest -v                         # run the test suite
```

See [Installation](#installation) for virtual-environment setup and
[Example session](#example-session) for a full walkthrough.

## Overview

Rotating savings groups are usually tracked on paper or in chat messages,
which makes it easy to lose track of who has paid, who still owes money, and
who has already received a payout. This program makes weekly contributions,
balances, and payouts accurate, transparent, and easy to verify.

## Features

- Create a group with a fixed weekly contribution in GHS (FR-01).
- Register members with a unique ID and a name, in registration order (FR-02).
- Record full or partial contributions against the current week (FR-03).
- Reject unknown members, invalid amounts, duplicates, and overpayments (FR-04).
- Close a week only when every member has paid in full (FR-05).
- Pay the whole pot to the next eligible member in order (FR-06).
- Advance the week and recipient exactly once per closure (FR-07).
- Report the current week, member balances, rotation status, and payout
  history (FR-08).
- Prevent duplicate payouts and further activity once the rotation is
  complete (FR-09).
- Use exact decimal arithmetic for all money (FR-10).

## Requirements

- Python 3.9 or newer (developed and tested on Python 3.13)
- pytest for the automated tests (installed below)

The application itself has **no third-party runtime dependencies**.

## Installation

Clone the repository and enter the project directory:

```bash
git clone <repository-url>
cd susu-group-tracker
```

A virtual environment is optional but recommended:

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

Install the (test) dependencies:

```bash
python -m pip install -r requirements.txt
```

No install step is needed to run the program; it is started directly from the
repository root (see below).

## Usage

Run the program from the repository root:

```bash
python -m susu_tracker.cli
```

The program first asks for the weekly contribution per member, then shows the
current status and this menu:

```
----------------------------------------
Weekly contribution: GHS 50.00
Current week: 1
Rotation status: Active
----------------------------------------
1. Add member
2. Record contribution
3. View current week status
4. Close current week
5. View payout history
6. View group report
0. Exit
Select an option:
```

| Option | Action |
| --- | --- |
| `1` | Register a new member (ID and name) |
| `2` | Record a full or partial contribution for a member |
| `3` | Show who has paid and who still owes for the current week |
| `4` | Close the current week and pay out the pot, if everyone has paid |
| `5` | Show the payout history |
| `6` | Show the full group report (balances, pot, status, payouts) |
| `0` | Exit |

## Example session

The scenario below is the one from the assignment: three members contributing
GHS 50.00 each. Text after `>` is what the organizer types; the status block
repeated before every prompt is omitted for brevity.

```
=== Susu Group Tracker ===
Enter the weekly contribution per member in GHS: > 50
Weekly contribution set to GHS 50.00.

1. Add member  ...  0. Exit
Select an option: > 1
Member ID: > M1
Member name: > Ama
Registered Ama (M1) as member #1.
... (Kofi as M2, Esi as M3) ...

Select an option: > 2
Member ID: > M1
Amount in GHS: > 50
Recorded GHS 50.00 for Ama. Outstanding balance: GHS 0.00.
... (Kofi pays GHS 50.00) ...

Select an option: > 2
Member ID: > M3
Amount in GHS: > 30
Recorded GHS 30.00 for Esi. Outstanding balance: GHS 20.00.

Select an option: > 4
Cannot close week 1: members still owe money.
  Esi (M3) owes GHS 20.00
No payout was recorded. Week 1 remains open.

Select an option: > 2
Member ID: > M3
Amount in GHS: > 20
Recorded GHS 20.00 for Esi. Outstanding balance: GHS 0.00.

Select an option: > 4
Week 1 closed.
Payout: GHS 150.00 to Ama (M1).
Next recipient for week 2: Kofi (M2).
```

## Business rules

1. The weekly contribution must be greater than zero.
2. Member IDs must be unique, compared case-insensitively after trimming
   surrounding whitespace. Names are display labels and may be repeated.
3. Members are paid in registration order, once per rotation.
4. Membership is frozen once the first contribution is recorded.
5. Each contribution must be greater than zero and may not exceed the
   member's remaining balance for the week.
6. A week closes only when at least one member exists and every member has
   paid in full.
7. Week closure is atomic: validation happens first, so a rejected closure
   creates no payout, does not advance the week, and keeps existing payments.
8. A successful closure creates exactly one payout and advances the cycle
   exactly once.
9. Once every member has received one payout the rotation is complete, and
   further contributions, closures, and members are rejected.

## Testing

Run the full test suite from the repository root:

```bash
python -m pytest -v
```

| Test ID | Scenario | Test |
| --- | --- | --- |
| T-01 | Create a group with GHS 50.00 | `test_group.py::test_create_group_stores_weekly_contribution` |
| T-02 | Reject zero / negative weekly contribution | `test_group.py::test_create_group_rejects_non_positive_amounts` |
| T-03 | Reject duplicate member | `test_group.py::test_duplicate_member_id_is_rejected` |
| T-04 | Reject payment for an unknown member | `test_contributions.py::test_unknown_member_balance_is_rejected` |
| T-05 | Partial payment leaves GHS 20.00 owed | `test_contributions.py::test_partial_payment_reduces_the_outstanding_balance` |
| T-06 | Reject overpayment | `test_contributions.py::test_overpayment_after_full_payment_changes_nothing` |
| T-07 | Reject closure while members owe money | `test_week_closure.py::test_failed_closure_leaves_the_group_unchanged` |
| T-08 | Close week, pay the correct recipient | `test_week_closure.py::test_successful_closure_pays_the_pot_to_the_first_member` |
| T-09 | No duplicate payout | `test_week_closure.py::test_reopening_a_closed_week_is_rejected` |
| T-10 | Complete the rotation | `test_week_closure.py::test_full_rotation_pays_every_member_in_registration_order` |
| T-11 | Freeze membership after first payment | `test_group.py::test_membership_freezes_after_first_contribution` |
| T-12 | Report shows balances and payouts | `test_reports.py::test_report_shows_payout_history_after_closure` |
| T-13 | Contributions tracked per week | `test_contributions_and_payouts.py::test_contributions_are_tracked_per_week` |
| T-14 | Failed close reports every unpaid member | `test_contributions_and_payouts.py::test_close_reports_every_unpaid_member` |
| T-15 | Failed closures are absent from payout history | `test_contributions_and_payouts.py::test_report_omits_failed_closures` |
| T-16 | Spec example: partial payments then closure | `test_contributions_and_payouts.py::test_spec_example_contributions_then_closure` |
| T-17 | Failed registration keeps list and joining order | `test_susu.py::test_failed_registrations_do_not_change_the_member_list_or_order` |
| T-18 | Money stays exact Decimal | `test_susu.py::test_money_stays_exact_decimal` |
| T-19 | Second payout follows joining order | `test_susu.py::test_second_payout_follows_joining_order` |
| T-20 | Zero / negative payments rejected | `test_susu.py::test_zero_and_negative_payments_are_rejected` |

## Project structure

```
susu-group-tracker/
├── susu_tracker/
│   ├── __init__.py
│   ├── cli.py              # presentation layer: menu, prompts, formatting
│   ├── money.py            # exact Decimal money parsing/formatting
│   ├── exceptions.py       # expected business-rule errors
│   ├── models.py           # domain layer: SusuGroup, Member, Week, Payout
│   ├── repository.py       # in-memory storage
│   └── susu_service.py     # application layer: coordinates operations
├── tests/
│   ├── conftest.py
│   ├── test_money.py
│   ├── test_group.py
│   ├── test_susu.py
│   ├── test_contributions.py
│   ├── test_contributions_and_payouts.py
│   ├── test_week_closure.py
│   ├── test_reports.py
│   └── test_cli.py
├── NOTES.md
├── README.md
├── pyproject.toml
└── requirements.txt
```

The layers are kept separate on purpose:

- `cli.py` (presentation) contains no financial rules; it only collects input
  and formats output.
- `susu_service.py` (application) coordinates operations and is the single
  entry point used by the CLI and the tests.
- `models.py` (domain) owns the savings rules, delegating storage to
  `repository.py`.

That keeps the rules testable without the CLI.

## Design notes

Assumptions, design decisions, current limitations, and future improvements
are recorded in [NOTES.md](NOTES.md), including why Python and `Decimal` are
used, membership freezing, partial payments, payout order, and the in-memory
persistence choice.
