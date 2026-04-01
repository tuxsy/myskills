"""Git operations via dulwich (clone, pull, sync, credential resolution) per R-002."""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

from myskills.models import SkillsRepository

logger = logging.getLogger(__name__)


class GitError(Exception):
    """Raised when Git operations fail."""


def _get_ssh_vendor() -> object | None:
    """Get paramiko SSH vendor for dulwich if available."""
    try:
        from dulwich.contrib.paramiko_vendor import ParamikoSSHVendor

        return ParamikoSSHVendor()
    except ImportError:
        return None


def clone_repository(url: str, target: Path, verbose: bool = False) -> None:
    """Clone a Git repository using dulwich, with system git fallback.

    Args:
        url: Repository URL (SSH or HTTPS).
        target: Local directory to clone into.
        verbose: Enable verbose logging.

    Raises:
        GitError: If cloning fails.
    """
    if target.exists():
        raise GitError(f"Clone target '{target}' already exists.")

    target.parent.mkdir(parents=True, exist_ok=True)

    # Try dulwich first
    try:
        if verbose:
            logger.info("Cloning repository %s via dulwich", url)

        import dulwich.porcelain

        kwargs: dict = {"source": url, "target": str(target)}

        # Set up SSH if URL looks like SSH
        if url.startswith("git@") or url.startswith("ssh://"):
            vendor = _get_ssh_vendor()
            if vendor is not None:
                import dulwich.client

                dulwich.client.get_ssh_vendor = lambda: vendor  # type: ignore[assignment]

        repo = dulwich.porcelain.clone(**kwargs)
        if verbose and repo:
            logger.info("Dulwich clone completed: %s", repo)
        return
    except Exception as e:
        if verbose:
            logger.warning(
                "Dulwich clone failed: %s (%s). Trying system git...", type(e).__name__, e
            )
        # Clean up partial clone
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)

    # Fallback to system git
    _fallback_git_clone(url, target, verbose)


def pull_repository(repo_path: Path, verbose: bool = False) -> None:
    """Pull latest changes from remote using dulwich, with system git fallback.

    Args:
        repo_path: Local repository path.
        verbose: Enable verbose logging.

    Raises:
        GitError: If pulling fails.
    """
    if not repo_path.exists():
        raise GitError(f"Repository path '{repo_path}' does not exist.")

    # Try dulwich first
    try:
        if verbose:
            logger.info("Pulling latest changes via dulwich in %s", repo_path)

        import dulwich.porcelain

        try:
            result = dulwich.porcelain.pull(str(repo_path), fast_forward=True, ff_only=False)
            # dulwich.porcelain.pull can return None or a tuple of (old_sha, new_sha)
            # Both indicate success
            if verbose and result:
                logger.info("Dulwich pull completed: %s", result)
            return
        except dulwich.porcelain.DivergedBranches:
            # If branches have diverged, use system git to handle merge
            if verbose:
                logger.info("Branches diverged, using system git for merge")
            # Fall through to system git

    except Exception as e:
        if verbose:
            logger.warning(
                "Dulwich pull failed: %s (%s). Trying system git...", type(e).__name__, e
            )

    # Fallback to system git
    _fallback_git_pull(repo_path, verbose)


def sync_repository(repo: SkillsRepository, verbose: bool = False) -> None:
    """Clone or pull to ensure local cache is up-to-date.

    Args:
        repo: SkillsRepository with url and local_cache.
        verbose: Enable verbose logging.

    Raises:
        GitError: If sync fails.
    """
    if repo.is_cloned:
        pull_repository(repo.local_cache, verbose=verbose)
    else:
        clone_repository(repo.url, repo.local_cache, verbose=verbose)


def push_repository(repo_path: Path, verbose: bool = False) -> None:
    """Push local commits to remote.

    Args:
        repo_path: Local repository path.
        verbose: Enable verbose logging.

    Raises:
        GitError: If pushing fails.
    """
    if not repo_path.exists():
        raise GitError(f"Repository path '{repo_path}' does not exist.")

    # Try dulwich first
    try:
        if verbose:
            logger.info("Pushing changes via dulwich from %s", repo_path)

        import dulwich.porcelain

        dulwich.porcelain.push(str(repo_path))
        return
    except Exception as e:
        if verbose:
            logger.warning(
                "Dulwich push failed: %s (%s). Trying system git...", type(e).__name__, e
            )

    # Fallback to system git
    _fallback_git_push(repo_path, verbose)


def commit_changes(
    repo_path: Path,
    message: str,
    author: str = "myskills <myskills@local>",
    verbose: bool = False,
) -> None:
    """Stage all changes and commit.

    Args:
        repo_path: Local repository path.
        message: Commit message.
        author: Author string.
        verbose: Enable verbose logging.

    Raises:
        GitError: If committing fails.
    """
    try:
        if verbose:
            logger.info("Committing changes in %s", repo_path)

        import dulwich.porcelain

        dulwich.porcelain.add(str(repo_path))
        dulwich.porcelain.commit(
            str(repo_path),
            message=message.encode("utf-8"),
            author=author.encode("utf-8"),
            committer=author.encode("utf-8"),
        )
    except Exception as e:
        raise GitError(f"Failed to commit changes: {e}") from e


# --- System git fallbacks ---


def _find_git() -> str | None:
    """Find system git binary."""
    return shutil.which("git")


def _fallback_git_clone(url: str, target: Path, verbose: bool = False) -> None:
    """Clone using system git as fallback."""
    git = _find_git()
    if git is None:
        raise GitError(
            "Repository unreachable. Neither dulwich nor system git could complete the operation."
        )

    try:
        cmd = [git, "clone", url, str(target)]
        if verbose:
            logger.info("Falling back to system git: %s", " ".join(cmd))
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            raise GitError(f"git clone failed: {result.stderr.strip()}")
    except subprocess.TimeoutExpired as e:
        raise GitError("git clone timed out") from e
    except OSError as e:
        raise GitError(f"Failed to run system git: {e}") from e


def _fallback_git_pull(repo_path: Path, verbose: bool = False) -> None:
    """Pull using system git as fallback."""
    git = _find_git()
    if git is None:
        raise GitError(
            "Repository unreachable. Neither dulwich nor system git could complete the operation."
        )

    try:
        # First, try to fetch to ensure we have the latest refs
        fetch_cmd = [git, "fetch"]
        if verbose:
            logger.info("Falling back to system git: %s", " ".join(fetch_cmd))
        fetch_result = subprocess.run(
            fetch_cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=repo_path,
        )
        if fetch_result.returncode != 0:
            raise GitError(f"git fetch failed: {fetch_result.stderr.strip()}")

        # Get current branch
        branch_cmd = [git, "rev-parse", "--abbrev-ref", "HEAD"]
        branch_result = subprocess.run(
            branch_cmd,
            capture_output=True,
            text=True,
            timeout=10,
            cwd=repo_path,
        )
        if branch_result.returncode != 0:
            raise GitError(f"Failed to get current branch: {branch_result.stderr.strip()}")

        current_branch = branch_result.stdout.strip()

        # Merge the fetched changes
        merge_cmd = [git, "merge", f"origin/{current_branch}"]
        if verbose:
            logger.info("Merging changes: %s", " ".join(merge_cmd))
        merge_result = subprocess.run(
            merge_cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=repo_path,
        )
        if merge_result.returncode != 0:
            raise GitError(f"git merge failed: {merge_result.stderr.strip()}")

    except subprocess.TimeoutExpired as e:
        raise GitError("git operation timed out") from e
    except OSError as e:
        raise GitError(f"Failed to run system git: {e}") from e


def _fallback_git_push(repo_path: Path, verbose: bool = False) -> None:
    """Push using system git as fallback."""
    git = _find_git()
    if git is None:
        raise GitError(
            "Repository unreachable. Neither dulwich nor system git could complete the operation."
        )

    try:
        cmd = [git, "push"]
        if verbose:
            logger.info("Falling back to system git: %s", " ".join(cmd))
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=repo_path,
        )
        if result.returncode != 0:
            raise GitError(f"git push failed: {result.stderr.strip()}")
    except subprocess.TimeoutExpired as e:
        raise GitError("git push timed out") from e
    except OSError as e:
        raise GitError(f"Failed to run system git: {e}") from e
