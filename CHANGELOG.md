# Changelog

## v2.0 (2026) - rewrite

A ground-up rewrite of the same application (same purpose, same on-screen
workflow, same underlying idea - see `README.md`), fixing bugs found in
the 2018 version:

- **Fixed:** entering data for a second student without restarting the app
  could carry the previous student's numbers into the new calculation.
  This was the one bug the original README explicitly apologized for
  ("I'm working on a fix for this"). Caused by module-level `global`
  variables shared across the whole app session; the rewrite scopes all
  per-student state to a per-student object that's reset on load/new.
- **Fixed:** one subject's percentage classification compared against the
  wrong subject's variable (`mathtime` compared against `elatime`), a
  copy-paste artifact from having six near-identical code blocks.
- **Fixed:** one subject's "Save Update" recalculation silently did
  nothing because it called a misspelled, nonexistent method name.
- **Fixed:** an undefined variable reference in one subject's calculation
  path (`new_ss2`, left over from copy-pasting the Social Studies block).
- **Added:** "Remove selected test" now actually works. The original code
  had this method fully written, for all six subjects, but never
  connected it to a button.
- **Added:** numeric fields (expected/actual time) are now spin boxes
  instead of free-text fields, so invalid input can't silently produce a
  blank result the way it could before.
- **Added:** saving a name that's already in the database now warns you
  and tells you to use "Load" + "Save Update" instead of failing silently.
- **Changed:** the list of previously-entered students is now read
  directly from the database instead of a separate `student_names.txt`
  file that only ever grew and was never deduplicated.
- **Changed:** one reusable tab class/config list drives all six subjects
  instead of six hand-copied ~120-line blocks - the main reason the bugs
  above existed in the first place.

The full 2018 source is preserved under `legacy/` for reference.

## v1.4 (2018) - original release

Original PyQt5 desktop application: six subject tabs, SQLite storage under
`%APPDATA%`, PyInstaller + Inno Setup packaging. See `legacy/README.md`.
