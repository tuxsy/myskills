"""Terminal UI abstraction with injectable interface for testing (R-003, R-004)."""

from __future__ import annotations

from typing import Protocol


class UIProvider(Protocol):
    """Abstract interface for UI interactions. Enables FakeUI injection in tests."""

    def info(self, message: str) -> None:
        """Display an informational message."""
        ...

    def success(self, message: str) -> None:
        """Display a success message."""
        ...

    def warning(self, message: str) -> None:
        """Display a warning message."""
        ...

    def error(self, message: str) -> None:
        """Display an error message."""
        ...

    def verbose(self, message: str) -> None:
        """Display a verbose/debug message."""
        ...

    def confirm(self, message: str, default: bool = False) -> bool:
        """Ask for yes/no confirmation. Returns True if confirmed."""
        ...

    def multi_select(
        self,
        title: str,
        options: list[str],
        preselected: list[int] | None = None,
    ) -> list[int]:
        """Present a multi-select menu. Returns indices of selected options."""
        ...

    def select_action(self, message: str, actions: list[str]) -> int:
        """Present a single-select action menu. Returns index of selected action."""
        ...


class TerminalUI:
    """Real terminal UI using click + simple-term-menu."""

    def __init__(self, verbose_mode: bool = False) -> None:
        self._verbose_mode = verbose_mode

    def info(self, message: str) -> None:
        """Display an informational message."""
        import click

        click.echo(message)

    def success(self, message: str) -> None:
        """Display a success message (green)."""
        import click

        click.secho(message, fg="green")

    def warning(self, message: str) -> None:
        """Display a warning message (yellow)."""
        import click

        click.secho(f"Warning: {message}", fg="yellow", err=True)

    def error(self, message: str) -> None:
        """Display an error message (red)."""
        import click

        click.secho(f"Error: {message}", fg="red", err=True)

    def verbose(self, message: str) -> None:
        """Display verbose message if verbose mode is enabled."""
        if self._verbose_mode:
            import click

            click.secho(f"[verbose] {message}", fg="cyan", err=True)

    def confirm(self, message: str, default: bool = False) -> bool:
        """Ask for yes/no confirmation using click."""
        import click

        return click.confirm(message, default=default)

    def multi_select(
        self,
        title: str,
        options: list[str],
        preselected: list[int] | None = None,
    ) -> list[int]:
        """Present a multi-select menu using simple-term-menu."""
        from simple_term_menu import TerminalMenu

        menu = TerminalMenu(
            options,
            title=title,
            multi_select=True,
            show_multi_select_hint=True,
            preselected_entries=preselected,
        )
        result = menu.show()

        if result is None:
            return []

        # TerminalMenu returns tuple for multi-select
        if isinstance(result, tuple):
            return list(result)
        return [result]

    def select_action(self, message: str, actions: list[str]) -> int:
        """Present single-select action menu."""
        from simple_term_menu import TerminalMenu

        menu = TerminalMenu(actions, title=message)
        result = menu.show()

        if result is None:
            return -1

        return int(result)


class FakeUI:
    """Test double for UIProvider. Records all interactions and returns predetermined responses."""

    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []  # (level, message)
        self._confirm_responses: list[bool] = []
        self._multi_select_responses: list[list[int]] = []
        self._select_action_responses: list[int] = []
        self._choice_responses: list[str] = []

    def set_confirm_responses(self, *responses: bool) -> None:
        """Set responses for confirm() calls (consumed in order)."""
        self._confirm_responses = list(responses)

    def set_multi_select_responses(self, *responses: list[int]) -> None:
        """Set responses for multi_select() calls (consumed in order)."""
        self._multi_select_responses = list(responses)

    def set_select_action_responses(self, *responses: int) -> None:
        """Set responses for select_action() calls (consumed in order)."""
        self._select_action_responses = list(responses)

    def set_choice_responses(self, *responses: str) -> None:
        """Set responses for choice prompts (consumed in order)."""
        self._choice_responses = list(responses)

    def info(self, message: str) -> None:
        self.messages.append(("info", message))

    def success(self, message: str) -> None:
        self.messages.append(("success", message))

    def warning(self, message: str) -> None:
        self.messages.append(("warning", message))

    def error(self, message: str) -> None:
        self.messages.append(("error", message))

    def verbose(self, message: str) -> None:
        self.messages.append(("verbose", message))

    def confirm(self, message: str, default: bool = False) -> bool:
        self.messages.append(("confirm", message))
        if self._confirm_responses:
            return self._confirm_responses.pop(0)
        return default

    def multi_select(
        self,
        title: str,
        options: list[str],
        preselected: list[int] | None = None,
    ) -> list[int]:
        self.messages.append(("multi_select", title))
        if self._multi_select_responses:
            return self._multi_select_responses.pop(0)
        return list(range(len(options)))

    def select_action(self, message: str, actions: list[str]) -> int:
        self.messages.append(("select_action", message))
        if self._select_action_responses:
            return self._select_action_responses.pop(0)
        return 0

    def get_choice_response(self) -> str | None:
        """Get next choice response if available."""
        if self._choice_responses:
            return self._choice_responses.pop(0)
        return None
