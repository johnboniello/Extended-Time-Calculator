# Extended Time Calculator

A small desktop tool for special-education teams to help estimate an
extended-time testing accommodation from real test data, built with
PyQt5 and SQLite.

## Disclaimer

This application is **not** intended to be the one measure used in
determining an extended time accommodation for a student with a
disability. It is simply one piece of data that can support a decision
made by a Committee on Special Education (or equivalent team). Any
decision must be made in accordance with relevant laws and regulations
and must take into account the impact of the disability on the student's
ability to complete a test in the expected amount of time. This
application can only give you a number and a sentence that explains that
number - do not base a decision on this number alone.

Copyright (C) 2018-2026 John Boniello. This program comes with ABSOLUTELY
NO WARRANTY; see `LICENSE.txt`. This is free software, and you are
welcome to redistribute it under the terms of the GNU General Public
License v3.

## Repository layout

```
src/                  The current application (v2, 2026 rewrite). Run this.
tests/                Automated smoke test for src/.
packaging/windows/    Scripts to build a Windows .exe and installer.
legacy/               The original 2018 version, kept for reference.
CHANGELOG.md          What changed between the 2018 version and this one.
```

## Using the app

1. Enter a **new** student's name, or pick an **existing** one from the
   dropdown.
2. On each subject tab (ELA, Math, Social Studies, Science, World
   Languages, ENL), log a test: date, test name, expected time, and the
   time the student actually used, then click **Add Test**. Data should
   be collected over multiple tests before drawing any conclusion.
3. Click **Calculate** to turn the running average into a plain-English
   recommendation. The Student tab shows a live summary across all six
   subjects.
4. Click **Save New Student** for a brand-new student, or **Save Update**
   for an existing one - this averages newly-entered data in with
   whatever was already on file, rather than overwriting it.

Names must be unique (the database key is the student's name), so agree
on a naming convention up front - e.g. `Lastname_FirstInitial`.

Data is stored in a SQLite database under
`%APPDATA%\Extended_Time_Calc\TimeAccommodations.db`. You can open this
file directly with any SQLite browser (e.g. DB Browser for SQLite) if you
need to inspect or correct a record, but doing so is not recommended
unless you're comfortable with SQL - changes made there affect what the
app sees directly.

## Running from source

```
pip install -r requirements.txt
python src/extended_time_calculator.py
```

Requires Python 3.9+ and PyQt5.

## Building a Windows installer

From `packaging/windows/`, double-click `build_windows.bat` (or run it
from a terminal). It will install PyInstaller/PyQt5/Pillow if needed,
build `dist\Extended Time Calculator.exe`, and - if Inno Setup
(https://jrsoftware.org/isdl.php) is installed - also produce a full
installer, `extended_time_calculator_setup.exe`. See `build_log.txt` in
that folder for details of what happened.

## Testing

```
pip install -r requirements.txt
python tests/smoke_test.py
```

Runs an end-to-end headless check (works without a display via
`QT_QPA_PLATFORM=offscreen`) covering save/load/update, the averaging
rule, and the cross-student data isolation described in `CHANGELOG.md`.

## Contact

johnboniello@gmail.com
