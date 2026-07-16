"""Fail-closed execution guard for mesh scripts (security issue #R-04).

The b_watcher / brief_b / b_roundtrip scripts historically ran
``subprocess.run(cmd, shell=True)`` on command strings scraped from ANOTHER
AI agent's free-text output. That is a prompt-injection -> arbitrary code
execution chain: whoever can influence the peer agent's replies gets a shell
on the operator's machine, and ``shell=True`` additionally lets metacharacters
(``;`` ``&&`` ``|`` backticks) escape any intended command shape.

This module replaces that with one narrow, shell-free primitive:

* ``run_allowlisted_script`` — only runs ``python <script> <args...>`` where
  ``<script>`` is in an explicit allowlist and every arg is a plain token
  (no shell metacharacters). Uses an explicit argv with ``shell=False``.

Peer-authored ``python -c`` snippets are never executable through this module.
An environment-variable escape hatch would merely re-enable the original RCE.
"""
from __future__ import annotations

import re
import shlex
import subprocess
import sys
from typing import Optional, Sequence

# Reject anything that could break out of a single intended command.
_SHELL_METACHARS = re.compile(r"[;&|`$><\n\r\\]")

class UnsafeCommand(ValueError):
    """Raised when peer-supplied text is not a safe, allowlisted command."""


def _reject_metachars(tokens: Sequence[str]) -> None:
    for tok in tokens:
        if _SHELL_METACHARS.search(tok):
            raise UnsafeCommand(f"shell metacharacter in argument: {tok!r}")


def run_allowlisted_script(
    command_line: str,
    allowed_scripts: Sequence[str],
    cwd: Optional[str] = None,
    timeout: Optional[float] = 120.0,
) -> subprocess.CompletedProcess:
    """Run ``python <script> <args...>`` iff <script> is allowlisted.

    Parses with shlex (POSIX tokenization), requires the form
    ``python <script> [args...]`` with <script> in ``allowed_scripts`` and no
    shell metacharacters anywhere, then executes an explicit argv with
    ``shell=False``. Raises UnsafeCommand on any deviation.
    """
    _reject_metachars([command_line])
    tokens = shlex.split(command_line, posix=True)
    if len(tokens) < 2 or tokens[0] not in ("python", "python3", sys.executable):
        raise UnsafeCommand("command must start with 'python <script>'")
    script = tokens[1]
    if script not in allowed_scripts:
        raise UnsafeCommand(f"script not allowlisted: {script!r}")
    args = tokens[2:]
    _reject_metachars(args)
    return subprocess.run(
        [sys.executable, script, *args],
        shell=False,
        capture_output=True,
        text=True,
        cwd=cwd,
        timeout=timeout,
    )
