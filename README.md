# habit

A small CLI habit streak tracker. Add a daily habit, check it off each day,
and watch your current and best streaks grow.

```bash
habit add "read 20 pages"
habit check "read 20 pages"
habit streak "read 20 pages"
habit stats
```

## Commands

| Command | What it does |
| --- | --- |
| `habit add <name>` | Add a new habit |
| `habit list` | List all habits with current/best streaks and today's status |
| `habit check <name> [--date YYYY-MM-DD]` | Mark a habit done (default: today) |
| `habit uncheck <name> [--date YYYY-MM-DD]` | Remove a check-in |
| `habit streak <name>` | Show one habit's check-ins and streaks |
| `habit stats` | Overall stats across all habits |
| `habit remove <name>` | Delete a habit |
| `habit reset` | Delete all habits |

The current streak counts back from today (today may still be unchecked);
the best streak is the longest unbroken run ever. Future dates can't be
checked in, and checking the same day twice is a no-op.

## Storage

Habits live in `~/.habits.json` (override with `--data <path>` or the
`HABITS_FILE` environment variable).

## Run

Requires Python 3.8+ and nothing else — standard library only.

```bash
python3 habit.py add "meditate"
python3 habit.py check "meditate"
python3 habit.py stats
```

## Tests

```bash
python3 -m pytest tests/ -v
```
