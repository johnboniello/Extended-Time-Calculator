#!/usr/bin/env python3
"""Extended Time Accommodation Calculator (rewrite)

Original concept and all subject-matter logic (c) 2018 John Boniello.
This is a from-scratch rewrite of the same program, built to remove
duplication and fix the bugs found in the 2018 version, while keeping
the exact same purpose described in the project's own README:

    "This application is ... one piece of data that can support any
    decision made by the Committee on Special Education ... Any
    application, especially this application, can only provide you
    with a number and a sentence that explains that number."

What a teacher does with it, per the original README, hasn't changed:
  1. Enter a NEW student name, or pick an EXISTING one from the list.
  2. On each subject tab, log a test's expected time and the time the
     student actually used, then "Add Test".
  3. "Calculate" turns the running average into a plain-English
     recommendation sentence.
  4. "Save" (new student) or "Save Update" (existing student, averages
     the new data in with what was already on file) persists it.

Licensed, like the original, under the GNU GPL v3 (see LICENSE.txt).
"""
from __future__ import annotations

import os
import sys
import sqlite3
from dataclasses import dataclass, field
from typing import Optional

from PyQt5 import QtCore, QtWidgets


# ---------------------------------------------------------------------------
# Domain logic: kept completely separate from the GUI so it can be tested
# (and read) on its own, and so there is exactly ONE copy of it instead of
# six near-identical copies, one per subject, as in the original.
# ---------------------------------------------------------------------------

#: Subjects the app tracks. Adding a new one is a one-line change here --
#: in the original app it meant copy-pasting ~120 lines and hoping every
#: variable name inside them got renamed correctly (it didn't, always).
SUBJECTS: list[tuple[str, str]] = [
    ("ela", "English Language Arts"),
    ("math", "Math"),
    ("ss", "Social Studies"),
    ("sci", "Science"),
    ("wl", "World Languages"),
    ("enl", "ENL"),
]


def classify(percent: float) -> str:
    """Turn an average time-used percentage into the README's recommendation
    sentence. This is the ONE place this logic lives (the original had it
    copy-pasted 24 times -- once per subject, per save/update/load variant --
    which is how it ended up with mismatched variable names in a couple of
    the copies)."""
    pct = round(percent, 2)
    if pct <= 100:
        return (
            "This student may not require extra time for this subject "
            f"(currently uses an average of {pct}% of the expected time)."
        )
    if pct < 150:
        return (
            f"This student may or may not need extended time; they use {pct}% "
            "of the expected time on exams."
        )
    if pct == 150:
        return (
            "This student may need time and a half on exams for this subject "
            f"(currently uses an average of {pct}% of the expected time)."
        )
    if pct < 200:
        return (
            f"This student takes {pct}% of the expected time on exams in this "
            "subject. This suggests they may need time and a half or double time."
        )
    return (
        "This student may need double time on exams for this subject "
        f"(currently uses an average of {pct}% of the expected time)."
    )


@dataclass
class TestEntry:
    test_date: str
    test_name: str
    expected_minutes: float
    actual_minutes: float

    @property
    def ratio_percent(self) -> float:
        return (self.actual_minutes / self.expected_minutes) * 100


@dataclass
class SubjectRecord:
    """All the state for one subject, for the student currently loaded.

    In the original app this was six sets of module-level `global`
    variables (`elatime`, `mathtime`, `elaratio_list`, ...) that lived for
    the lifetime of the whole application. That is the direct cause of the
    bug the original README documents and apologizes for: "if you enter
    for multiple students without restarting ... the sentence will be
    incorrect." Here it's a plain attribute on a per-student object that
    gets thrown away and recreated every time you start a new student or
    load a different one, so there is no way for one student's numbers to
    leak into another's.
    """

    key: str
    label: str
    entries: list[TestEntry] = field(default_factory=list)
    on_file_percent: Optional[float] = None  # value already saved in the DB

    def average_percent(self) -> Optional[float]:
        if not self.entries:
            return None
        return sum(e.ratio_percent for e in self.entries) / len(self.entries)

    def combined_with_on_file(self) -> Optional[float]:
        """What gets written back on 'Save Update': the average of what was
        already on file and whatever new tests were entered this session --
        exactly the averaging rule the README describes, just computed in
        one place instead of duplicated per subject."""
        session_avg = self.average_percent()
        if session_avg is None:
            return self.on_file_percent
        if self.on_file_percent is None:
            return session_avg
        return (session_avg + self.on_file_percent) / 2


def new_subject_records() -> dict[str, SubjectRecord]:
    return {key: SubjectRecord(key, label) for key, label in SUBJECTS}


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

class StudentDatabase:
    """Thin wrapper around the same one-row-per-student SQLite table the
    original app used, with two fixes:

    1. The original kept a SEPARATE flat file (`student_names.txt`) as a
       human-readable index of who'd been entered, appending to it on every
       save with no de-duplication -- so it grew a repeated entry every time
       you re-saved the same student, and it lived at a bare relative path
       that depended on the app's current working directory. The database
       is already the index; there's no reason to also maintain a second,
       driftable copy of the same information in a text file.
    2. The database file itself lives under %APPDATA% (Windows) or the
       platform-appropriate equivalent, exactly like the original -- that
       part of the original was correct and is kept as-is.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        with self._connect() as conn:
            columns = ", ".join(f"{key}_pct REAL" for key, _ in SUBJECTS)
            conn.execute(
                f"CREATE TABLE IF NOT EXISTS students ("
                f"name TEXT PRIMARY KEY NOT NULL, {columns})"
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def student_names(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT name FROM students ORDER BY name").fetchall()
        return [r[0] for r in rows]

    def exists(self, name: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM students WHERE name = ?", (name,)
            ).fetchone()
        return row is not None

    def load(self, name: str) -> Optional[dict[str, Optional[float]]]:
        with self._connect() as conn:
            cols = ", ".join(f"{key}_pct" for key, _ in SUBJECTS)
            row = conn.execute(
                f"SELECT {cols} FROM students WHERE name = ?", (name,)
            ).fetchone()
        if row is None:
            return None
        return {key: row[i] for i, (key, _) in enumerate(SUBJECTS)}

    def insert_new(self, name: str, values: dict[str, Optional[float]]) -> None:
        cols = ["name"] + [f"{key}_pct" for key, _ in SUBJECTS]
        placeholders = ", ".join("?" for _ in cols)
        params = [name] + [values.get(key) for key, _ in SUBJECTS]
        with self._connect() as conn:
            conn.execute(
                f"INSERT INTO students ({', '.join(cols)}) VALUES ({placeholders})",
                params,
            )

    def update_existing(self, name: str, values: dict[str, Optional[float]]) -> None:
        set_clause = ", ".join(f"{key}_pct = ?" for key, _ in SUBJECTS)
        params = [values.get(key) for key, _ in SUBJECTS] + [name]
        with self._connect() as conn:
            conn.execute(
                f"UPDATE students SET {set_clause} WHERE name = ?", params
            )


def default_db_path() -> str:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        base = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
    app_dir = os.path.join(base, "Extended_Time_Calc")
    os.makedirs(app_dir, exist_ok=True)
    return os.path.join(app_dir, "TimeAccommodations.db")


# ---------------------------------------------------------------------------
# GUI: one reusable panel class instead of six copy-pasted subject blocks.
# ---------------------------------------------------------------------------

class SubjectTab(QtWidgets.QWidget):
    """One subject's tab: a plain input row, a running table of tests, an
    Add/Remove/Calculate toolbar, and a result sentence.

    Every subject in the app is one instance of this class. The original
    app had six copies of this UI hand-built in Qt Designer and six copies
    of the wiring code in Python; a bug fix or a wording change had to be
    made six times and, in three places, wasn't (see the review notes:
    `mathtime`/`elatime` mixed up, an undefined `new_ss2`, a misspelled
    method name that made one subject's "Save Update" silently do nothing).
    """

    changed = QtCore.pyqtSignal()

    def __init__(self, record: SubjectRecord, parent=None):
        super().__init__(parent)
        self.record = record

        self.date_edit = QtWidgets.QDateEdit(QtCore.QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.test_name_edit = QtWidgets.QLineEdit()
        self.test_name_edit.setPlaceholderText("e.g. Unit 3 quiz")

        # QDoubleSpinBox instead of a free-text QLineEdit: it is physically
        # impossible to type "abc" into these, which removes an entire class
        # of ValueError the original silently swallowed and hid from the user.
        self.expected_spin = QtWidgets.QDoubleSpinBox()
        self.expected_spin.setRange(0.1, 1000)
        self.expected_spin.setSuffix(" min")
        self.expected_spin.setValue(45)

        self.actual_spin = QtWidgets.QDoubleSpinBox()
        self.actual_spin.setRange(0.0, 2000)
        self.actual_spin.setSuffix(" min")
        self.actual_spin.setValue(45)

        add_btn = QtWidgets.QPushButton("Add Test")
        add_btn.clicked.connect(self._add_row)
        remove_btn = QtWidgets.QPushButton("Remove Selected Test")
        remove_btn.clicked.connect(self._remove_selected_row)
        calc_btn = QtWidgets.QPushButton("Calculate")
        calc_btn.clicked.connect(self._recalculate)

        form = QtWidgets.QFormLayout()
        form.addRow("Date:", self.date_edit)
        form.addRow("Test name:", self.test_name_edit)
        form.addRow("Expected time:", self.expected_spin)
        form.addRow("Actual time used:", self.actual_spin)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addWidget(add_btn)
        btn_row.addWidget(remove_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(calc_btn)

        self.table = QtWidgets.QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["Date", "Test", "Expected", "Actual"]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        self.result_label = QtWidgets.QLabel("No tests added yet.")
        self.result_label.setWordWrap(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(btn_row)
        layout.addWidget(self.table)
        layout.addWidget(QtWidgets.QLabel("Result:"))
        layout.addWidget(self.result_label)

    def reset(self) -> None:
        """Clear this tab's session data. Called whenever the user starts a
        new student or loads a different one, so nothing from a previous
        student can bleed into the next one's average."""
        self.record.entries.clear()
        self.record.on_file_percent = None
        self.table.setRowCount(0)
        self.result_label.setText("No tests added yet.")

    def load_on_file_percent(self, percent: Optional[float]) -> None:
        self.record.on_file_percent = percent
        if percent is not None:
            self.result_label.setText(
                "On file: " + classify(percent)
            )

    def _add_row(self) -> None:
        expected = self.expected_spin.value()
        actual = self.actual_spin.value()
        if expected <= 0:
            QtWidgets.QMessageBox.warning(
                self, "Invalid entry", "Expected time must be greater than zero."
            )
            return
        entry = TestEntry(
            self.date_edit.date().toString("yyyy-MM-dd"),
            self.test_name_edit.text().strip() or "(untitled test)",
            expected,
            actual,
        )
        self.record.entries.append(entry)

        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(entry.test_date))
        self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(entry.test_name))
        self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(str(entry.expected_minutes)))
        self.table.setItem(row, 3, QtWidgets.QTableWidgetItem(str(entry.actual_minutes)))

        self.test_name_edit.clear()
        self._recalculate()

    def _remove_selected_row(self) -> None:
        """Actually works, unlike the original: the original wrote this
        method (and its six copies) but never connected any of them to a
        button, so there was no way to delete a mis-entered row without
        restarting the whole app."""
        row = self.table.currentRow()
        if row < 0:
            return
        self.table.removeRow(row)
        del self.record.entries[row]
        self._recalculate()

    def _recalculate(self) -> None:
        avg = self.record.average_percent()
        if avg is None:
            self.result_label.setText("No tests added yet.")
        else:
            self.result_label.setText(classify(avg))
        self.changed.emit()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, db: StudentDatabase):
        super().__init__()
        self.db = db
        self.setWindowTitle("Extended Time Accommodation Calculator")
        self.resize(900, 650)

        self.records = new_subject_records()
        self.tabs_by_key: dict[str, SubjectTab] = {}
        self._loaded_student: Optional[str] = None

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.addTab(self._build_student_tab(), "Student")
        for key, label in SUBJECTS:
            tab = SubjectTab(self.records[key])
            tab.changed.connect(self._refresh_summary)
            self.tabs_by_key[key] = tab
            self.tabs.addTab(tab, label)
        self.tabs.addTab(self._build_about_tab(), "About / Disclaimer")

        self.setCentralWidget(self.tabs)
        self._refresh_student_list()
        self._refresh_summary()

    # -- Student tab ------------------------------------------------------

    def _build_student_tab(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()

        self.new_name_edit = QtWidgets.QLineEdit()
        self.new_name_edit.setPlaceholderText("e.g. Smith_J")
        new_row = QtWidgets.QHBoxLayout()
        new_row.addWidget(QtWidgets.QLabel("New student name:"))
        new_row.addWidget(self.new_name_edit)
        self.save_btn = QtWidgets.QPushButton("Save New Student")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self._save_new_student)
        new_row.addWidget(self.save_btn)

        self.existing_combo = QtWidgets.QComboBox()
        self.existing_combo.setEditable(False)
        existing_row = QtWidgets.QHBoxLayout()
        existing_row.addWidget(QtWidgets.QLabel("Existing student:"))
        existing_row.addWidget(self.existing_combo, 1)
        self.load_btn = QtWidgets.QPushButton("Load")
        self.load_btn.clicked.connect(self._load_existing_student)
        self.update_btn = QtWidgets.QPushButton("Save Update")
        self.update_btn.setEnabled(False)
        self.update_btn.clicked.connect(self._save_update)
        existing_row.addWidget(self.load_btn)
        existing_row.addWidget(self.update_btn)

        self.new_name_edit.textChanged.connect(
            lambda text: self.save_btn.setEnabled(bool(text.strip()))
        )

        self.loaded_label = QtWidgets.QLabel("No student loaded.")
        self.loaded_label.setStyleSheet("font-style: italic; color: gray;")

        summary_group = QtWidgets.QGroupBox("Summary (updates live as you enter data)")
        self.summary_labels: dict[str, QtWidgets.QLabel] = {}
        summary_layout = QtWidgets.QFormLayout()
        for key, label in SUBJECTS:
            lbl = QtWidgets.QLabel("No tests added yet.")
            lbl.setWordWrap(True)
            self.summary_labels[key] = lbl
            summary_layout.addRow(f"{label}:", lbl)
        summary_group.setLayout(summary_layout)

        layout = QtWidgets.QVBoxLayout(widget)
        layout.addLayout(new_row)
        layout.addLayout(existing_row)
        layout.addWidget(self.loaded_label)
        layout.addWidget(summary_group)
        layout.addStretch(1)
        return widget

    def _build_about_tab(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        text = QtWidgets.QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(
            "This application is not intended to be the one measure used in "
            "determining an extended time accommodation for a student with a "
            "disability. This is simply one piece of data that can support "
            "any decision made by the Committee on Special Education. "
            "Decisions made by the CSE must be made in accordance with "
            "relevant laws and regulations and must take into account the "
            "impact of the disability on the student's ability to complete "
            "a test in the expected amount of time. This application can "
            "only provide you with a number and a sentence that explains "
            "that number -- do not base a decision on this number alone.\n\n"
            "Copyright (C) 2018 John Boniello. This program comes with "
            "ABSOLUTELY NO WARRANTY. This is free software, distributed "
            "under the GNU General Public License v3."
        )
        layout = QtWidgets.QVBoxLayout(widget)
        layout.addWidget(text)
        return widget

    # -- state management ---------------------------------------------------

    def _refresh_student_list(self) -> None:
        current = self.existing_combo.currentText()
        self.existing_combo.blockSignals(True)
        self.existing_combo.clear()
        self.existing_combo.addItems(self.db.student_names())
        idx = self.existing_combo.findText(current)
        if idx >= 0:
            self.existing_combo.setCurrentIndex(idx)
        self.existing_combo.blockSignals(False)

    def _reset_all_tabs(self) -> None:
        for tab in self.tabs_by_key.values():
            tab.reset()
        self._refresh_summary()

    def _refresh_summary(self) -> None:
        for key, _ in SUBJECTS:
            record = self.records[key]
            combined = record.combined_with_on_file()
            if combined is None:
                self.summary_labels[key].setText("No tests added yet.")
            else:
                self.summary_labels[key].setText(classify(combined))

    def _collect_percentages(self) -> dict[str, Optional[float]]:
        return {
            key: self.records[key].combined_with_on_file() for key, _ in SUBJECTS
        }

    # -- button handlers ------------------------------------------------

    def _save_new_student(self) -> None:
        name = self.new_name_edit.text().strip()
        if not name:
            return
        if self.db.exists(name):
            QtWidgets.QMessageBox.warning(
                self,
                "Student already exists",
                f"'{name}' is already in the database. Use the 'Existing "
                "student' box and 'Save Update' instead, or choose a "
                "different, unique name.",
            )
            return
        # A new student gets only the tests entered this session -- never the
        # on-file values of whichever student happened to be loaded.
        values = {key: self.records[key].average_percent() for key, _ in SUBJECTS}
        self.db.insert_new(name, values)
        QtWidgets.QMessageBox.information(self, "Saved", f"Saved new student '{name}'.")
        self.new_name_edit.clear()
        # Start clean for the next student so nothing carries over. To add
        # more tests for this student later, load them and use Save Update.
        self._reset_all_tabs()
        self._loaded_student = None
        self.loaded_label.setText(
            f"Saved {name}. Enter tests for the next student, or load an existing one."
        )
        self.update_btn.setEnabled(False)
        self._refresh_student_list()

    def _load_existing_student(self) -> None:
        name = self.existing_combo.currentText()
        if not name:
            return
        data = self.db.load(name)
        if data is None:
            QtWidgets.QMessageBox.warning(self, "Not found", f"No record for '{name}'.")
            return
        # Fixes the bug the original README warned about ("if you enter for
        # multiple students without restarting ... the sentence will be
        # incorrect"): every tab's running totals are cleared before the
        # new student's on-file values are loaded in, so nothing from
        # whoever was loaded before can leak into this student's average.
        self._reset_all_tabs()
        for key, _ in SUBJECTS:
            self.tabs_by_key[key].load_on_file_percent(data.get(key))
        self._loaded_student = name
        self.loaded_label.setText(f"Currently working on: {name} (loaded from file)")
        self.update_btn.setEnabled(True)
        self._refresh_summary()

    def _save_update(self) -> None:
        if not self._loaded_student:
            return
        self.db.update_existing(self._loaded_student, self._collect_percentages())
        QtWidgets.QMessageBox.information(
            self, "Saved", f"Updated '{self._loaded_student}'."
        )
        self._refresh_summary()


def main() -> None:
    app = QtWidgets.QApplication(sys.argv)
    db = StudentDatabase(default_db_path())
    window = MainWindow(db)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
