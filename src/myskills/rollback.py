"""Atomic operation undo stack for rollback on failure (FR-010, SC-006)."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


class RollbackError(Exception):
    """Raised when rollback itself fails."""


@dataclass
class Step:
    """A single atomic operation with its corresponding undo action."""

    description: str
    action: Callable[[], Any]
    undo: Callable[[], Any]


class UndoStack:
    """Manages a sequence of steps with automatic rollback on failure.

    Usage:
        stack = UndoStack()
        stack.add("Copy files", do_copy, undo_copy)
        stack.add("Create symlink", do_symlink, undo_symlink)
        stack.execute()  # Runs all steps; rolls back on failure
    """

    def __init__(self, verbose: bool = False) -> None:
        self._steps: list[Step] = []
        self._completed: list[Step] = []
        self._verbose = verbose

    def add(
        self,
        description: str,
        action: Callable[[], Any],
        undo: Callable[[], Any],
    ) -> None:
        """Register a step with its action and corresponding undo.

        Args:
            description: Human-readable description of the step.
            action: Callable to execute the step.
            undo: Callable to reverse the step.
        """
        self._steps.append(Step(description=description, action=action, undo=undo))

    def execute(self) -> list[Any]:
        """Execute all registered steps in order.

        If any step fails, all previously completed steps are rolled back
        in reverse order.

        Returns:
            List of results from each successful action.

        Raises:
            The original exception from the failed step (after rollback).
            RollbackError: If rollback itself fails (wraps original + rollback errors).
        """
        self._completed = []
        results: list[Any] = []

        for step in self._steps:
            try:
                if self._verbose:
                    logger.info("Executing: %s", step.description)
                result = step.action()
                results.append(result)
                self._completed.append(step)
            except Exception as original_error:
                if self._verbose:
                    logger.warning("Step failed: %s. Rolling back...", step.description)
                self._rollback(original_error)
                raise

        return results

    def _rollback(self, original_error: Exception) -> None:
        """Roll back all completed steps in reverse order.

        Args:
            original_error: The original exception that triggered rollback.

        Raises:
            RollbackError: If any undo action fails (includes original error context).
        """
        rollback_errors: list[tuple[str, Exception]] = []

        for step in reversed(self._completed):
            try:
                if self._verbose:
                    logger.info("Rolling back: %s", step.description)
                step.undo()
            except Exception as e:
                rollback_errors.append((step.description, e))

        self._completed.clear()

        if rollback_errors:
            error_details = "; ".join(f"'{desc}': {err}" for desc, err in rollback_errors)
            raise RollbackError(
                f"Operation failed ({original_error}) and rollback had errors: {error_details}"
            ) from original_error

    @property
    def step_count(self) -> int:
        """Number of registered steps."""
        return len(self._steps)

    @property
    def completed_count(self) -> int:
        """Number of completed steps."""
        return len(self._completed)

    def clear(self) -> None:
        """Clear all registered steps and completed tracking."""
        self._steps.clear()
        self._completed.clear()
