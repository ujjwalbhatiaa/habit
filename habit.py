#!/usr/bin/env python3
"""habit - a small CLI habit streak tracker.

Track daily habits, mark them done, and see current/best streaks.

    habit add "read 20 pages"
    habit check "read 20 pages"
    habit streak "read 20 pages"
    habit stats

Habits are stored as JSON in ~/.habits.json (override with --data or
the HABITS_FILE environment variable). Only the Python standard library
is used.
"""

import argparse
import json
import os
import sys
from datetime import date, timedelta

DEFAULT_DATA_FILE = os.path.expanduser("~/.habits.json")
DATE_FORMAT = "%Y-%m-%d"


def data_file_path(args):
    """Resolve the storage path: --data wins, then HABITS_FILE, then default."""
    if getattr(args, "data", None):
        return os.path.expanduser(args.data)
    env = os.environ.get("HABITS_FILE")
    if env:
        return os.path.expanduser(env)
    return DEFAULT_DATA_FILE


def load_habits(path):
    """Load the habits dict from path; missing/corrupt file -> empty dict."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    # Normalise: keep only {name: [date strings]} entries.
    habits = {}
    for name, dates in data.items():
        if isinstance(name, str) and isinstance(dates, list):
            habits[name] = sorted({d for d in dates if isinstance(d, str)})
    return habits


def save_habits(path, habits):
    """Write the habits dict to path (creating parent dirs as needed)."""
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(habits, f, indent=2, sort_keys=True)
        f.write("\n")


def parse_date(text):
    """Parse a YYYY-MM-DD string into a date; raise ValueError if invalid."""
    parts = text.split("-")
    if len(parts) != 3:
        raise ValueError(f"invalid date {text!r} (expected YYYY-MM-DD)")
    try:
        year, month, day = (int(p) for p in parts)
        return date(year, month, day)
    except ValueError:
        raise ValueError(f"invalid date {text!r} (expected YYYY-MM-DD)")


def streaks(dates, today=None):
    """Return (current_streak, best_streak) for a sorted list of date objects.

    The current streak counts back from today (or yesterday, if today is
    not yet checked in); the best streak is the longest run anywhere.
    """
    if today is None:
        today = date.today()
    if not dates:
        return 0, 0
    days = sorted(set(dates))
    best = run = 1
    for prev, cur in zip(days, days[1:]):
        if cur - prev == timedelta(days=1):
            run += 1
        else:
            run = 1
        best = max(best, run)
    # Current streak: walk back from today, allowing today to be unchecked.
    day_set = set(days)
    current = 0
    cursor = today
    if cursor not in day_set:
        cursor -= timedelta(days=1)
    while cursor in day_set:
        current += 1
        cursor -= timedelta(days=1)
    return current, best


def cmd_add(args):
    habits = load_habits(data_file_path(args))
    if args.name in habits:
        print(f"habit {args.name!r} already exists")
        return 1
    habits[args.name] = []
    save_habits(data_file_path(args), habits)
    print(f"added habit: {args.name}")
    return 0


def cmd_list(args):
    habits = load_habits(data_file_path(args))
    if not habits:
        print("no habits yet — add one with: habit add <name>")
        return 0
    today = date.today()
    for name in sorted(habits):
        dates = [parse_date(d) for d in habits[name]]
        current, best = streaks(dates, today)
        done = today.strftime(DATE_FORMAT) in habits[name]
        mark = "done today" if done else "not done today"
        print(f"{name} — current streak {current}, best {best} ({mark})")
    return 0


def cmd_check(args):
    habits = load_habits(data_file_path(args))
    if args.name not in habits:
        print(f"no habit named {args.name!r} — add it first with: habit add {args.name!r}")
        return 1
    day = parse_date(args.date) if args.date else date.today()
    if day > date.today():
        print("cannot check in a future date")
        return 1
    stamp = day.strftime(DATE_FORMAT)
    if stamp in habits[args.name]:
        print(f"{args.name!r} already checked for {stamp}")
        return 0
    habits[args.name].append(stamp)
    habits[args.name].sort()
    save_habits(data_file_path(args), habits)
    current, best = streaks([parse_date(d) for d in habits[args.name]])
    print(f"checked {args.name!r} for {stamp} — current streak {current}, best {best}")
    return 0


def cmd_uncheck(args):
    habits = load_habits(data_file_path(args))
    if args.name not in habits:
        print(f"no habit named {args.name!r}")
        return 1
    day = parse_date(args.date) if args.date else date.today()
    stamp = day.strftime(DATE_FORMAT)
    if stamp not in habits[args.name]:
        print(f"{args.name!r} was not checked for {stamp}")
        return 0
    habits[args.name].remove(stamp)
    save_habits(data_file_path(args), habits)
    print(f"removed check-in for {args.name!r} on {stamp}")
    return 0


def cmd_streak(args):
    habits = load_habits(data_file_path(args))
    if args.name not in habits:
        print(f"no habit named {args.name!r}")
        return 1
    dates = [parse_date(d) for d in habits[args.name]]
    current, best = streaks(dates)
    total = len(dates)
    print(f"{args.name}: {total} check-ins, current streak {current} day(s), best {best} day(s)")
    return 0


def cmd_stats(args):
    habits = load_habits(data_file_path(args))
    if not habits:
        print("no habits yet — add one with: habit add <name>")
        return 0
    today = date.today()
    total_checkins = sum(len(v) for v in habits.values())
    done_today = sum(1 for v in habits.values() if today.strftime(DATE_FORMAT) in v)
    longest = max(
        (streaks([parse_date(d) for d in v], today)[1], name)
        for name, v in habits.items()
    )
    print(f"{len(habits)} habit(s), {total_checkins} total check-in(s)")
    print(f"done today: {done_today}/{len(habits)}")
    print(f"longest best streak: {longest[0]} day(s) ({longest[1]})")
    for name in sorted(habits):
        dates = [parse_date(d) for d in habits[name]]
        current, best = streaks(dates, today)
        print(f"  {name}: {len(dates)} check-ins, streak {current}, best {best}")
    return 0


def cmd_remove(args):
    habits = load_habits(data_file_path(args))
    if args.name not in habits:
        print(f"no habit named {args.name!r}")
        return 1
    del habits[args.name]
    save_habits(data_file_path(args), habits)
    print(f"removed habit: {args.name}")
    return 0


def cmd_reset(args):
    path = data_file_path(args)
    if os.path.exists(path):
        os.remove(path)
    print("all habits cleared")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="habit", description="Track daily habits and streaks."
    )
    parser.add_argument("--data", help="path to the habits JSON file")
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="add a new habit")
    p_add.add_argument("name")
    p_add.set_defaults(func=cmd_add)

    p_list = sub.add_parser("list", help="list habits with streaks")
    p_list.set_defaults(func=cmd_list)

    p_check = sub.add_parser("check", help="mark a habit done for a day")
    p_check.add_argument("name")
    p_check.add_argument("--date", help="date to check in (YYYY-MM-DD, default today)")
    p_check.set_defaults(func=cmd_check)

    p_uncheck = sub.add_parser("uncheck", help="remove a check-in")
    p_uncheck.add_argument("name")
    p_uncheck.add_argument("--date", help="date to uncheck (YYYY-MM-DD, default today)")
    p_uncheck.set_defaults(func=cmd_uncheck)

    p_streak = sub.add_parser("streak", help="show a habit's streaks")
    p_streak.add_argument("name")
    p_streak.set_defaults(func=cmd_streak)

    p_stats = sub.add_parser("stats", help="show overall stats")
    p_stats.set_defaults(func=cmd_stats)

    p_remove = sub.add_parser("remove", help="delete a habit")
    p_remove.add_argument("name")
    p_remove.set_defaults(func=cmd_remove)

    p_reset = sub.add_parser("reset", help="delete all habits")
    p_reset.set_defaults(func=cmd_reset)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
