"""Tests for habit.py — run with: python3 -m pytest tests/ -v"""

import json
import os
import subprocess
import sys
from datetime import date, timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import habit as h

HERE = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def data_file(tmp_path):
    return str(tmp_path / "habits.json")


def run_cli(data_file, *args):
    cmd = [sys.executable, os.path.join(HERE, "..", "habit.py"),
           "--data", data_file, *args]
    return subprocess.run(cmd, capture_output=True, text=True)


def read_json(data_file):
    with open(data_file, encoding="utf-8") as f:
        return json.load(f)


# --- streaks() ---

def test_streaks_empty():
    assert h.streaks([]) == (0, 0)


def test_streaks_single_today():
    today = date(2026, 11, 19)
    assert h.streaks([today], today) == (1, 1)


def test_streaks_consecutive_run():
    today = date(2026, 11, 19)
    days = [today - timedelta(days=i) for i in range(5)]
    assert h.streaks(days, today) == (5, 5)


def test_streaks_current_allows_missing_today():
    today = date(2026, 11, 19)
    days = [today - timedelta(days=i) for i in range(1, 4)]
    assert h.streaks(days, today) == (3, 3)


def test_streaks_broken_current_streak():
    today = date(2026, 11, 19)
    days = [today - timedelta(days=5), today - timedelta(days=4),
            today - timedelta(days=1)]
    current, best = h.streaks(days, today)
    assert best == 2
    assert current == 1


def test_streaks_best_longer_than_current():
    today = date(2026, 11, 19)
    days = [today - timedelta(days=10 + i) for i in range(4)]
    days += [today - timedelta(days=1)]
    current, best = h.streaks(days, today)
    assert best == 4
    assert current == 1


def test_streaks_gap_resets_best_run():
    today = date(2026, 11, 19)
    days = [today - timedelta(days=9), today - timedelta(days=8),
            today - timedelta(days=3), today - timedelta(days=2),
            today - timedelta(days=1)]
    assert h.streaks(days, today) == (3, 3)


def test_streaks_duplicates_ignored():
    today = date(2026, 11, 19)
    assert h.streaks([today, today], today) == (1, 1)


# --- dates ---

def test_parse_date_valid():
    assert h.parse_date("2026-11-19") == date(2026, 11, 19)


def test_parse_date_bad_format():
    with pytest.raises(ValueError):
        h.parse_date("19/11/2026")


def test_parse_date_impossible():
    with pytest.raises(ValueError):
        h.parse_date("2026-02-30")


# --- storage ---

def test_load_missing_file_returns_empty(tmp_path):
    assert h.load_habits(str(tmp_path / "nope.json")) == {}


def test_load_corrupt_file_returns_empty(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    assert h.load_habits(str(path)) == {}


def test_save_and_load_roundtrip(data_file):
    h.save_habits(data_file, {"read": ["2026-11-18", "2026-11-19"]})
    assert read_json(data_file)["read"] == ["2026-11-18", "2026-11-19"]


# --- CLI: add / list ---

def test_cli_add_and_list(data_file):
    r = run_cli(data_file, "add", "read 20 pages")
    assert r.returncode == 0
    assert "added habit" in r.stdout
    r = run_cli(data_file, "list")
    assert "read 20 pages" in r.stdout
    assert "current streak 0" in r.stdout


def test_cli_add_duplicate_fails(data_file):
    run_cli(data_file, "add", "gym")
    r = run_cli(data_file, "add", "gym")
    assert r.returncode == 1
    assert "already exists" in r.stdout


def test_cli_list_empty(data_file):
    r = run_cli(data_file, "list")
    assert r.returncode == 0
    assert "no habits yet" in r.stdout


# --- CLI: check / uncheck / streak ---

def test_cli_check_today_builds_streak(data_file):
    run_cli(data_file, "add", "gym")
    r = run_cli(data_file, "check", "gym")
    assert r.returncode == 0
    assert "current streak 1" in r.stdout
    r = run_cli(data_file, "streak", "gym")
    assert "1 check-in" in r.stdout
    assert "current streak 1" in r.stdout


def test_cli_check_twice_same_day_is_noop(data_file):
    run_cli(data_file, "add", "gym")
    run_cli(data_file, "check", "gym")
    r = run_cli(data_file, "check", "gym")
    assert r.returncode == 0
    assert "already checked" in r.stdout
    assert len(read_json(data_file)["gym"]) == 1


def test_cli_check_past_dates_builds_streak(data_file):
    run_cli(data_file, "add", "meditate")
    today = date.today()
    for i in (2, 1, 0):
        day = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        r = run_cli(data_file, "check", "meditate", "--date", day)
        assert r.returncode == 0
    r = run_cli(data_file, "streak", "meditate")
    assert "current streak 3" in r.stdout
    assert "best 3" in r.stdout


def test_cli_check_future_date_rejected(data_file):
    run_cli(data_file, "add", "gym")
    future = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    r = run_cli(data_file, "check", "gym", "--date", future)
    assert r.returncode == 1
    assert "future" in r.stdout


def test_cli_check_unknown_habit_fails(data_file):
    r = run_cli(data_file, "check", "nope")
    assert r.returncode == 1
    assert "no habit named" in r.stdout


def test_cli_uncheck_removes_day(data_file):
    run_cli(data_file, "add", "gym")
    run_cli(data_file, "check", "gym")
    r = run_cli(data_file, "uncheck", "gym")
    assert r.returncode == 0
    assert read_json(data_file)["gym"] == []


def test_cli_uncheck_missing_day_is_noop(data_file):
    run_cli(data_file, "add", "gym")
    r = run_cli(data_file, "uncheck", "gym")
    assert r.returncode == 0
    assert "was not checked" in r.stdout


# --- CLI: stats / remove / reset ---

def test_cli_stats(data_file):
    run_cli(data_file, "add", "gym")
    run_cli(data_file, "add", "read")
    run_cli(data_file, "check", "gym")
    r = run_cli(data_file, "stats")
    assert r.returncode == 0
    assert "2 habit(s)" in r.stdout
    assert "done today: 1/2" in r.stdout


def test_cli_stats_empty(data_file):
    r = run_cli(data_file, "stats")
    assert "no habits yet" in r.stdout


def test_cli_remove(data_file):
    run_cli(data_file, "add", "gym")
    r = run_cli(data_file, "remove", "gym")
    assert r.returncode == 0
    assert "gym" not in read_json(data_file)


def test_cli_remove_unknown_fails(data_file):
    r = run_cli(data_file, "remove", "nope")
    assert r.returncode == 1


def test_cli_reset_clears_everything(data_file):
    run_cli(data_file, "add", "gym")
    run_cli(data_file, "check", "gym")
    r = run_cli(data_file, "reset")
    assert r.returncode == 0
    assert not os.path.exists(data_file)
    r = run_cli(data_file, "list")
    assert "no habits yet" in r.stdout


def test_env_var_data_file(tmp_path, monkeypatch):
    path = str(tmp_path / "env.json")
    monkeypatch.setenv("HABITS_FILE", path)
    args = h.build_parser().parse_args(["add", "envhabit"])
    assert h.data_file_path(args) == path
