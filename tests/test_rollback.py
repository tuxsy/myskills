"""Unit tests for rollback mechanism (T018)."""

from __future__ import annotations

import pytest

from myskills.rollback import RollbackError, UndoStack


class TestUndoStackSuccess:
    """Tests for successful execution paths."""

    def test_execute_empty_stack(self):
        """Empty stack should execute without error and return empty results."""
        stack = UndoStack()

        results = stack.execute()

        assert results == []

    def test_execute_single_step(self):
        """Single step should execute and return its result."""
        stack = UndoStack()
        stack.add("step1", lambda: "result1", lambda: None)

        results = stack.execute()

        assert results == ["result1"]
        assert stack.completed_count == 1

    def test_execute_multiple_steps_in_order(self):
        """Multiple steps should execute in registration order."""
        execution_order: list[str] = []
        stack = UndoStack()

        stack.add("step1", lambda: execution_order.append("a1"), lambda: None)
        stack.add("step2", lambda: execution_order.append("a2"), lambda: None)
        stack.add("step3", lambda: execution_order.append("a3"), lambda: None)

        stack.execute()

        assert execution_order == ["a1", "a2", "a3"]

    def test_step_count(self):
        """step_count should reflect registered steps."""
        stack = UndoStack()
        assert stack.step_count == 0

        stack.add("s1", lambda: None, lambda: None)
        assert stack.step_count == 1

        stack.add("s2", lambda: None, lambda: None)
        assert stack.step_count == 2


class TestUndoStackRollback:
    """Tests for failure and rollback behavior."""

    def test_rollback_on_failure(self):
        """When a step fails, all completed steps should be undone in reverse."""
        undo_order: list[str] = []
        stack = UndoStack()

        stack.add("step1", lambda: None, lambda: undo_order.append("u1"))
        stack.add("step2", lambda: None, lambda: undo_order.append("u2"))

        def fail_step():
            raise ValueError("step3 failed")

        stack.add("step3", fail_step, lambda: undo_order.append("u3"))

        with pytest.raises(ValueError, match="step3 failed"):
            stack.execute()

        # step3 never completed, so its undo is NOT called
        # step1 and step2 undo should be called in reverse order
        assert undo_order == ["u2", "u1"]

    def test_rollback_clears_completed(self):
        """After rollback, completed_count should be 0."""
        stack = UndoStack()

        stack.add("step1", lambda: None, lambda: None)
        stack.add("step2", lambda: (_ for _ in ()).throw(RuntimeError("fail")), lambda: None)

        with pytest.raises(RuntimeError):
            stack.execute()

        assert stack.completed_count == 0

    def test_first_step_failure_no_rollback_needed(self):
        """If the first step fails, no rollback is needed."""
        undo_order: list[str] = []
        stack = UndoStack()

        def fail_step():
            raise ValueError("first failed")

        stack.add("step1", fail_step, lambda: undo_order.append("u1"))
        stack.add("step2", lambda: None, lambda: undo_order.append("u2"))

        with pytest.raises(ValueError, match="first failed"):
            stack.execute()

        # No undos should have been called since nothing completed
        assert undo_order == []

    def test_partial_failure_only_rollbacks_completed(self):
        """Only completed steps should be rolled back, not pending ones."""
        undo_order: list[str] = []
        stack = UndoStack()

        stack.add("step1", lambda: "ok", lambda: undo_order.append("u1"))

        def fail_step():
            raise RuntimeError("boom")

        stack.add("step2", fail_step, lambda: undo_order.append("u2"))
        stack.add("step3", lambda: "ok", lambda: undo_order.append("u3"))

        with pytest.raises(RuntimeError, match="boom"):
            stack.execute()

        # Only step1 completed, so only u1 should be rolled back
        assert undo_order == ["u1"]


class TestUndoStackRollbackErrors:
    """Tests for when rollback itself fails."""

    def test_rollback_error_wraps_original(self):
        """If rollback fails, RollbackError should include both errors."""
        stack = UndoStack()

        def bad_undo():
            raise OSError("undo failed")

        stack.add("step1", lambda: None, bad_undo)
        stack.add(
            "step2",
            lambda: (_ for _ in ()).throw(ValueError("action failed")),
            lambda: None,
        )

        with pytest.raises(RollbackError, match="rollback had errors"):
            stack.execute()

    def test_rollback_continues_on_undo_failure(self):
        """Even if one undo fails, remaining undos should still execute."""
        undo_order: list[str] = []
        stack = UndoStack()

        stack.add("step1", lambda: None, lambda: undo_order.append("u1"))

        def bad_undo():
            undo_order.append("u2_attempted")
            raise OSError("undo2 failed")

        stack.add("step2", lambda: None, bad_undo)
        stack.add(
            "step3",
            lambda: (_ for _ in ()).throw(ValueError("fail")),
            lambda: None,
        )

        with pytest.raises(RollbackError):
            stack.execute()

        # Both undo2 (attempted but failed) and undo1 should have run
        assert undo_order == ["u2_attempted", "u1"]


class TestUndoStackNested:
    """Tests for nested/real-world usage patterns."""

    def test_filesystem_like_operations(self, tmp_path):
        """Simulate create-dir + create-file with rollback."""
        test_dir = tmp_path / "skill"
        test_file = test_dir / "SKILL.md"

        stack = UndoStack()

        # Step 1: create directory
        def create_dir():
            test_dir.mkdir()

        def remove_dir():
            if test_dir.exists():
                test_dir.rmdir()

        # Step 2: create file (will fail intentionally)
        def create_file():
            test_file.write_text("content")

        def remove_file():
            if test_file.exists():
                test_file.unlink()

        # Step 3: failing step
        def fail():
            raise RuntimeError("simulated failure")

        stack.add("create dir", create_dir, remove_dir)
        stack.add("create file", create_file, remove_file)
        stack.add("final step", fail, lambda: None)

        with pytest.raises(RuntimeError, match="simulated failure"):
            stack.execute()

        # Both dir and file should have been cleaned up
        assert not test_file.exists()
        assert not test_dir.exists()

    def test_clear_resets_stack(self):
        """clear() should remove all steps and completed tracking."""
        stack = UndoStack()
        stack.add("s1", lambda: None, lambda: None)
        stack.execute()

        assert stack.step_count == 1
        assert stack.completed_count == 1

        stack.clear()

        assert stack.step_count == 0
        assert stack.completed_count == 0
