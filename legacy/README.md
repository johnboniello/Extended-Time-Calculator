# Legacy (2018) version

This folder holds the **original** Extended Time Calculator exactly as it
was written in 2018, kept for historical reference and comparison. It is
**not** the version you should build or run today - see
[`../src/extended_time_calculator.py`](../src/extended_time_calculator.py)
for the current, actively maintained version.

- `extended_time_calculator_2018.py` - the final 2018 release (previously
  called `extended_time_calculator_v14.py`).
- `ui_form_2018.py` - the Qt Designer-generated UI class it depends on
  (previously called `app5.py` / published here as `pyQT code.py`).

### Why it was rewritten

This was a first Python project, written with no formal programming
background, and it worked - it shipped with a real Windows installer and
was used in an actual school setting. But it also accumulated some bugs
from copy-pasting the same block of logic six times (once per subject
tab), and it has a known issue documented in the original README: entering
data for more than one student without restarting the app could let the
previous student's numbers leak into the next student's calculation.

The 2026 rewrite in `src/` keeps the exact same purpose and workflow but:

- replaces six copy-pasted subject blocks with one reusable class,
  removing several copy-paste bugs that only affected some subjects
  (e.g. one subject's percentage math referenced another subject's
  variable, one "save update" method silently failed due to a typo);
- removes all `global` state in favor of per-student objects, which is
  what fixes the cross-student data leak mentioned above;
- adds a working "remove test row" feature (it existed in the original
  code but was never wired to a button);
- validates numeric input with spin boxes instead of free-text fields;
- reads the list of previously-entered students from the database itself
  instead of a separate, never-deduplicated `student_names.txt` file.

See [`../CHANGELOG.md`](../CHANGELOG.md) for the full list.
