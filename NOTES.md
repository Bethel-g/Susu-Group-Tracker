# Notes, assumptions, and design decisions

This document records the decisions taken where the assignment leaves room for
interpretation, plus the reasoning behind them.

## Why Python, and the data structures used

Python was chosen because the standard library is enough for this problem
(`decimal`, `dataclasses`, `enum`, `re`), so the application runs with no
third-party runtime dependencies and is easy to test with pytest. The work is
business logic rather than performance or I/O, so a readable language keeps the
rules short and obvious without hiding anything behind a framework.

The main data structures are:

- **`dataclass` records** for immutable values: `Member`, `Contribution`,
  `Payout`, and `MemberBalance`. They give equality and readable construction
  for free, which keeps the tests short.
- **`list`s kept in joining or chronological order**: `members`, `contributions`,
  and `payouts`. Order *is* the payout schedule, so a list (rather than a set or
  a dict) is the natural container and keeps the history easy to display.
- **A `dict[int, Week]`** mapping a week number to its `Week`, so a week's
  status and payout are looked up directly.
- **`decimal.Decimal`** for every amount; `float` is never used for money.
- **A single `SusuGroup` reference** held by `InMemoryRepository`, isolated in
  its own module so a database could replace it later.

## Assumptions and design decisions

### 1. Membership

Members cannot be added after the first contribution has been recorded. This
keeps the contribution obligation and the weekly pot consistent, because the
pot depends on the number of members. Before any payment, members may be added
freely.

### 2. Uniqueness rule

Member IDs must be unique. Comparison is case-insensitive after trimming
surrounding whitespace, so `m1`, `M1`, and ` M1 ` are the same ID. Names are
display labels only and may be repeated, so two members can both be called
`Ama` as long as their IDs differ.

### 3. Partial payments

Multiple payments are allowed during an open week. Each payment is stored as a
separate `Contribution` record rather than overwriting the previous amount, so
the payment history stays transparent (`GHS 30.00` then `GHS 20.00`). The total
may never exceed the required weekly contribution; the outstanding balance is
never negative.

### 4. Failed closure

A week remains open when any member owes money. Closure validates first and
mutates state only after every check passes, so a failed closure creates no
payout, does not advance the week, does not change the next recipient, and
preserves all existing contributions.

### 5. Payout order

Members receive payouts in registration order, exactly once per rotation. The
first payout goes to the first registered member.

### 6. Completed rotation

The group becomes complete when every registered member has received one
payout. A new rotation is not started automatically; the organizer would create
a new group. After completion the program rejects new contributions, new
members, and further closures.

On the final payout the week is closed but no new week is opened, so the report
shows the final week number together with the status `Complete`.

### 7. Money

Monetary values use Python's `decimal.Decimal` and are displayed in GHS with
exactly two decimal places (`GHS 1,500.50`). Amounts must be representable in
pesewas: input with more than two decimal places is rejected rather than
rounded. Floats are converted through their shortest round-trip
representation, so a value such as `0.1 + 0.2` is rejected instead of silently
becoming `0.30`.

### 8. Persistence

Data is held in memory and is lost when the program exits. The in-memory
repository is isolated in `repository.py`, so persistent storage (for example
SQLite) could be added later without touching the domain rules.

### 9. Error handling

Expected business-rule violations raise subclasses of `SusuError`
(`susu_tracker/exceptions.py`). The CLI catches `SusuError` once and prints the
message, so only one place needs to know how errors are presented. A failed
closure raises `IncompleteWeekError`, which carries the outstanding balances so
the CLI can report exactly who still owes what.

### 10. Project layout

The package lives at the repository root (`susu_tracker/`) instead of under
`src/`. This keeps the documented commands (`python -m susu_tracker.cli` and
`python -m pytest`) working straight after a clone, with no install step.

### 11. Service layer

The assignment suggests separate `GroupService`, `ContributionService`,
`WeekClosureService`, and `ReportService` classes. For a program of this size a
single `SusuService` is easier to follow and keeps the same separation between
CLI, application, and domain layers. Splitting it later would be mechanical.

### 11a. Reporting helpers

The report is a read-only snapshot (`GroupReport`) built from the domain's
balance calculations; it performs no calculations of its own.

### 12. One group at a time

The application manages a single savings group. Creating a second group is
rejected with `GroupAlreadyExistsError` rather than silently overwriting the
existing one, and there is no group identifier because only one can exist at a
time. The repository holds at most one `SusuGroup` reference.

## Current limitations

- **One group only.** There is no way to name, create, or switch between
  several savings groups in one session.
- **No persistence.** Data lives in memory, so exiting the program loses the
  group, its contributions, and its payouts.
- **Membership is frozen after the first contribution.** A latecomer cannot be
  added, and members cannot be removed if someone leaves.
- **One full rotation only.** Payouts always follow joining order and each
  member is paid exactly once; the rotation does not restart automatically.
- **No reversal or audit trail.** A wrongly recorded payment cannot be undone
  through the interface.
- **No authentication.** The CLI trusts whoever runs it, and all output is
  plain text with no export.

## Future improvements

- Save data in SQLite or another database.
- Add persistent transaction records and a CLI export of reports.
- Support multiple savings groups.
- Add transaction reversal rules and an audit log.
- Support starting a second rotation for the same members.
