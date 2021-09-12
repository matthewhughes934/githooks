#!/usr/bin/env python3
"""
Hook to add a JIRA ticket from the current branch to the end of the commit body. You'll
want to:

* Edit `TICKET_LABELS` to support the labels used e.g. by JIRA
* Edit `TICKET_PREFIX` to what you want the ticket to be prefixed by in the commit
body

Searches your branch for a pattern of the form `<LABEL>-1234`, where `<LABEL>` is one of
the `TICKET_LABELS` below. It then adds the ticket to the commit if the commit source is
in the `SUPPORTED_SOURCES` below (see https://git-scm.com/docs/githooks or `githooks(5)`
for details on these sources).

For example:

        $ git checkout --branch FOO-1234/my-new-feature
        # make some changes...
        $ git commit --all --message "Add the new feature!"
        $ git log -1
        commit 2c49333eabcd2f92d39a341ebaf47bbdb2e5b275 (HEAD -> FOO-1234/my-new-feature)
        Author: John Smith <john.smith@email.com>
        Date:   Mon Dec 7 20:25:45 2020 -0500
            Add the new feature!

            Ticket: FOO-1234
"""

import re
import subprocess
import sys
from typing import Iterable, Literal, Optional, Sequence

TICKET_LABELS = ("FOO", "BAR")
TICKET_PREFIX = "Ticket: "
SUPPORTED_SOURCES = (None, "message", "template", "commit")

_AVAILABLE_SOURCES = (None, "message", "template", "merge", "squash", "commit")

# Returning nonzero would abort the commit
# I don't think there's a good reason to ever abort the commit
# just because of a missing ticket, so always return 0
def main(argv: Sequence[str]) -> Literal[0]:
    # see `githooks(5)` for details on expected args
    commit_msg_file = argv[1]

    commit_source: Optional[str]
    if len(argv) == 4:
        commit_source = argv[2]
    else:
        commit_source = None

    if commit_source in SUPPORTED_SOURCES:
        branch = _get_branch()
        if branch is not None:
            ticket = _get_ticket_from_branch(branch, TICKET_LABELS)
            if ticket is not None:
                with open(commit_msg_file) as f:
                    commit_content = f.read()
                out_content = _add_ticket_to_commit(
                    ticket, commit_source, commit_content
                )
                if out_content is not None:
                    with open(commit_msg_file, "w") as f:
                        f.write(out_content)

    return 0


def _add_ticket_to_commit(
    ticket: str, commit_source: Optional[str], commit_content: str
) -> Optional[str]:
    ticket_string = TICKET_PREFIX + ticket

    # no-op if the ticket details already exist
    if ticket_string in commit_content:
        return None

    if commit_source is None or commit_source in ("message", "commit"):
        return _add_ticket_details(commit_content, ticket_string, commit_source)
    else:
        return None


def _add_ticket_details(
    commit_content: str, ticket_string: str, commit_source: Optional[str]
) -> str:

    comment_start = re.search("^#", commit_content, flags=re.MULTILINE)
    if comment_start is not None:
        # commit open with editor: contents are the commit followed by
        # auto-generated comments
        # add the ticket between the end of the contents and the start of the comments
        comment_location = comment_start.span(0)[0]
        commit_text = commit_content[:comment_location]
        commit_comments = commit_content[comment_location:]

        ticket_string = f"\n{ticket_string}\n"
        if commit_source is None:
            ticket_string += "\n"

        return commit_text + ticket_string + commit_comments
    else:
        # commit not open with editor, just contains contents
        # append the ticket details
        return commit_content + f"\n{ticket_string}\n"


def _get_ticket_from_branch(branch: str, labels: Iterable[str]) -> Optional[str]:
    for label in labels:
        match = re.search(f"{re.escape(label)}-[0-9]+", branch)
        if match is not None:
            return match.group(0)
    return None


def _get_branch() -> Optional[str]:
    cmd = ("git", "rev-parse", "--abbrev-ref", "HEAD")
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as e:
        print(f"Failed to run `f{' '.join(cmd)}`: {e}", file=sys.stderr)
        return None

    stdout, stderr = proc.communicate()
    stdout_text = stdout.decode() if stdout is not None else ""
    stderr_text = stderr.decode() if stderr is not None else ""

    if proc.returncode != 0:
        print(
            f"`{' '.join(cmd)}` failed: {stdout_text}, {stderr_text}", file=sys.stderr
        )
        return None
    else:
        return stdout_text


if __name__ == "__main__":
    sys.exit(main(sys.argv))
