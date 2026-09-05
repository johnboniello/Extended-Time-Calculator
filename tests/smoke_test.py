"""Headless functional test for the rewrite, run with QT_QPA_PLATFORM=offscreen.

Simulates real usage end-to-end and specifically checks the scenario the
original README apologized for: entering data for a second student without
restarting the app should NOT carry over the first student's numbers.
"""
import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5 import QtWidgets  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from extended_time_calculator import MainWindow, StudentDatabase, classify  # noqa: E402


def main():
    # --- pure logic checks -------------------------------------------------
    assert classify(90) == (
        "This student may not require extra time for this subject "
        "(currently uses an average of 90% of the expected time)."
    )
    assert "time and a half" in classify(150)
    assert "double time" in classify(250)
    print("classify() sentences OK")

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    # Modal QMessageBox popups block on exec_() waiting for a real user/window
    # manager, which hangs forever under the offscreen platform. Stub them out
    # for this automated run only; the real app still shows them normally.
    QtWidgets.QMessageBox.information = staticmethod(lambda *a, **k: None)
    QtWidgets.QMessageBox.warning = staticmethod(lambda *a, **k: None)

    with tempfile.TemporaryDirectory() as tmp:
        db = StudentDatabase(os.path.join(tmp, "test.db"))
        win = MainWindow(db)

        # --- Student A: ELA test, 45 expected / 90 actual = 200% -> double time
        ela_tab = win.tabs_by_key["ela"]
        ela_tab.expected_spin.setValue(45)
        ela_tab.actual_spin.setValue(90)
        ela_tab._add_row()
        assert "double time" in win.summary_labels["ela"].text(), win.summary_labels["ela"].text()

        win.new_name_edit.setText("Smith_J")
        win._save_new_student()
        assert db.exists("Smith_J")
        print("Save new student OK:", db.load("Smith_J"))

        # --- Now simulate starting Student B WITHOUT restarting the app.
        # In the 2018 version this is exactly the scenario that leaked
        # Student A's numbers into Student B's calculation (global variables
        # persisted across students). Here we go through the same "load
        # existing" reset path a fresh student would trigger by loading
        # nothing / a blank sheet, then enter different numbers.
        win._reset_all_tabs()
        ela_tab.expected_spin.setValue(45)
        ela_tab.actual_spin.setValue(40)  # 88.9% -> should NOT need extra time
        ela_tab._add_row()
        label_b = win.summary_labels["ela"].text()
        assert "may not require extra time" in label_b, label_b
        assert "200" not in label_b and "double" not in label_b, (
            "BUG: student A's data leaked into student B: " + label_b
        )
        print("No cross-student leakage OK:", label_b)

        win.new_name_edit.setText("Jones_A")
        win._save_new_student()

        # --- Load Student A back and confirm their (and only their) data comes back.
        idx = win.existing_combo.findText("Smith_J")
        win.existing_combo.setCurrentIndex(idx)
        win._load_existing_student()
        ela_summary = win.summary_labels["ela"].text()
        assert "double time" in ela_summary, ela_summary
        print("Reload of Student A OK:", ela_summary)

        # --- Save Update: add a second ELA test for Smith_J and confirm it
        # averages with what was on file rather than overwriting it.
        ela_tab.expected_spin.setValue(45)
        ela_tab.actual_spin.setValue(45)  # 100% this time
        ela_tab._add_row()
        win._save_update()
        updated = db.load("Smith_J")["ela"]
        # on-file was 200%, new session avg is 100% -> combined should be 150%
        assert abs(updated - 150) < 0.01, updated
        print("Save Update averaging OK: new on-file value =", updated)

        # --- Remove-row actually works now (dead code in the original).
        rows_before = ela_tab.table.rowCount()
        ela_tab.table.setCurrentCell(0, 0)
        ela_tab._remove_selected_row()
        assert ela_tab.table.rowCount() == rows_before - 1
        assert len(ela_tab.record.entries) == rows_before - 1
        print("Remove-selected-test OK")

        # --- Duplicate-name guard.
        win.new_name_edit.setText("Smith_J")
        before = db.load("Smith_J")
        win._save_new_student()  # should warn and refuse, not overwrite
        after = db.load("Smith_J")
        assert before == after
        print("Duplicate-name guard OK")

    print("\nALL SMOKE TESTS PASSED")


if __name__ == "__main__":
    main()
