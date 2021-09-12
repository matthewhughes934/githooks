import os
import shutil
import subprocess
from pathlib import Path
from textwrap import dedent
from typing import Optional, Tuple
from unittest import mock

import pytest


def run_cmd(*args: str) -> Tuple[Optional[bytes], Optional[bytes], int]:
    try:
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError as e:
        assert False, f"Failed to run `{' '.join(args)}`: {e}"
    else:
        stdout, stderr = proc.communicate()

        returncode = proc.returncode
        if proc.returncode != 0:
            stdout_text = stdout if stdout is not None else ""
            stderr_text = stderr if stderr is not None else ""
            assert False, f"`{' '.join(args)}` failed: {stdout_text}, {stderr_text}"
        else:
            return stdout, stderr, returncode


@pytest.fixture
def git_dir(tmpdir) -> str:
    run_cmd("git", "init", tmpdir),
    yield tmpdir


@pytest.fixture
def ticket():
    return "FOO-123"


# run without opening an editor, ":"
# and opening opening an editor that does nothing, "true"
@pytest.fixture(params=("true", ":"))
def editor(request):
    return request.param


@pytest.fixture(
    params=("{}-great-new-feature", "feature/{}-new-feature", "{}/new-feature")
)
def branch_name(request, ticket):
    return request.param.format(ticket)


@pytest.fixture(autouse=True)
def init_git_repo(git_dir, request, branch_name):
    script_path = (
        Path(request.config.rootpath)
        / "prepare-commit-msg"
        / "add-jira-to-commit-body.py"
    )

    with git_dir.as_cwd():
        run_cmd("git", "checkout", "--orphan", branch_name)

        # Add a commit so a branch is defined
        run_cmd(
            "git",
            "commit",
            "--allow-empty",
            "--no-edit",
            "--message",
            "First commit",
        )
        shutil.copy(script_path, Path(git_dir) / ".git" / "hooks" / "prepare-commit-msg")
        # Ensure we use the hook we just copied
        run_cmd("git", "config", "--local", "--add", "core.hooksPath", ".git/hooks")


def test_bare_commit(git_dir, ticket, editor):
    expected_commit_subject = f"Ticket: {ticket}"

    with git_dir.as_cwd():
        with mock.patch.dict(os.environ, {"GIT_EDITOR": editor}):
            run_cmd(
                "git",
                "commit",
                "--allow-empty",
                "--cleanup",
                "verbatim",
            )

        log_stdout, log_stderr, _ = run_cmd(
            "git", "log", "--max-count", "1", "--format=format:%s"
        )
    assert log_stdout.decode() == expected_commit_subject


def test_ammending_commit(git_dir, ticket, editor):
    expected_commit_subject = f"Ticket: {ticket}\n"

    with git_dir.as_cwd():
        with mock.patch.dict(os.environ, {"GIT_EDITOR": editor}):
            run_cmd(
                "git",
                "commit",
                "--allow-empty",
                "--no-edit",
                "--amend",
                "--cleanup",
                "verbatim",
            )

        log_stdout, log_stderr, _ = run_cmd(
            "git", "log", "--max-count", "1", "--format=format:%b"
        )

    assert log_stdout.decode() == expected_commit_subject


@pytest.mark.parametrize("reuse_flag", ("--reuse-message", "--reedit-message"))
def test_reusing_commit(reuse_flag, git_dir, ticket, editor):
    expected_commit_subject = f"Ticket: {ticket}"

    with git_dir.as_cwd():
        rev_stdout, _, _ = run_cmd("git", "rev-parse", "HEAD")
        first_sha = rev_stdout.decode().strip()

        with mock.patch.dict(os.environ, {"GIT_EDITOR": editor}):
            run_cmd(
                "git",
                "commit",
                "--allow-empty",
                "--cleanup",
                "verbatim",
                reuse_flag,
                first_sha,
            )

        log_stdout, log_stderr, _ = run_cmd(
            "git", "log", "--max-count", "1", "--format=format:%b"
        )

    # comment lines still exist when reediting
    assert [
        line for line in log_stdout.decode().splitlines() if not line.startswith("#")
    ] == [expected_commit_subject]


def test_with_message(git_dir, ticket):
    commit_message = "Add the new feature"
    expected_commit_body = f"Ticket: {ticket}\n"

    with git_dir.as_cwd():
        run_cmd(
            "git",
            "commit",
            "--allow-empty",
            "--cleanup",
            "verbatim",
            "--message",
            commit_message,
        )

        log_stdout, log_stderr, _ = run_cmd(
            "git", "log", "--max-count", "1", "--format=format:%b"
        )

    assert log_stdout.decode() == expected_commit_body


def test_with_merge_commit(git_dir, ticket):
    merge_subject = "Merge the other commit"
    expected_merge_body = f"Ticket: {ticket}\n"
    other_branch = "another_branch"

    with git_dir.as_cwd():
        run_cmd(
            "git",
            "checkout",
            "-b",
            other_branch,
        )

        run_cmd(
            "git",
            "commit",
            "--allow-empty",
            "--no-edit",
            "--message",
            "Commit on the other branch",
        )
        run_cmd(
            "git",
            "checkout",
            "@{-1}",
        )
        run_cmd(
            "git",
            "commit",
            "--allow-empty",
            "--no-edit",
            "--message",
            "Commit on the main branch",
        )

        run_cmd(
            "git",
            "merge",
            "--message",
            merge_subject,
            other_branch,
        )

        log_stdout, log_stderr, _ = run_cmd(
            "git", "log", "--max-count", "1", "--format=format:%b"
        )

    assert log_stdout.decode() == expected_merge_body
