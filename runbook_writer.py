"""
runbook_writer.py — Auto-generate structured runbook files in selfconnect/runbooks/

Usage (CLI):
    python runbook_writer.py \\
        --title "My Procedure" \\
        --what "What it achieves in one line" \\
        --step "Step 1 description" \\
        --step "Step 2 description" \\
        --fail "Thing that doesn't work: reason" \\
        --prereq "Pillow>=10.0.0" \\
        --session 15

Usage (Python API):
    from runbook_writer import write_runbook
    path = write_runbook(
        title="My Procedure",
        what="What it achieves",
        steps=["Step 1", "Step 2"],
        known_failures=["Failure: reason"],
        prerequisites=["Pillow>=10.0.0"],
        session=15,
    )
    print(f"Runbook written to: {path}")

Trigger condition: call this after any task that required 3+ retry attempts
or a corrective injection before succeeding.
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

RUNBOOKS_DIR = Path(__file__).parent / "runbooks"


def _slugify(title: str) -> str:
    """Convert a title to a safe filename slug."""
    slug = title.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug


def write_runbook(
    title: str,
    what: str,
    steps: list[str],
    known_failures: list[str] | None = None,
    prerequisites: list[str] | None = None,
    session: int | None = None,
    runbooks_dir: Path | None = None,
) -> Path:
    """Write a structured runbook to runbooks/{slug}.md.

    If the file already exists, the Verified section is updated with today's date.
    All other sections are replaced with the new content.

    Args:
        title: Human-readable title (e.g. "Capture Chrome Window")
        what: One-line description of what this achieves
        steps: Ordered list of step descriptions (plain text or markdown)
        known_failures: List of "Failure: reason" strings
        prerequisites: List of prerequisite strings (packages, window state, etc.)
        session: Session number where this was proved (optional)
        runbooks_dir: Override output directory (default: selfconnect/runbooks/)

    Returns:
        Path to the written runbook file.
    """
    out_dir = runbooks_dir or RUNBOOKS_DIR
    out_dir.mkdir(exist_ok=True)

    slug = _slugify(title)
    out_path = out_dir / f"{slug}.md"
    today = date.today().isoformat()

    lines: list[str] = [f"# Runbook: {title}", ""]

    # What
    lines += ["## What", what, ""]

    # Prerequisites
    lines += ["## Prerequisites"]
    if prerequisites:
        for prereq in prerequisites:
            lines.append(f"- {prereq}")
    else:
        lines.append("- `self_connect` available on sys.path")
    lines.append("")

    # Steps
    lines += ["## Steps"]
    for i, step in enumerate(steps, 1):
        lines.append(f"{i}. {step}")
    lines.append("")

    # Known Failures
    lines += ["## Known Failures"]
    if known_failures:
        for failure in known_failures:
            lines.append(f"- {failure}")
    else:
        lines.append("- None documented yet")
    lines.append("")

    # Verified
    lines += ["## Verified"]
    session_note = f", session {session}" if session else ""
    lines.append(f"- {today}{session_note}")
    lines.append("")

    content = "\n".join(lines)
    out_path.write_text(content, encoding="utf-8")
    return out_path


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Write a structured runbook to selfconnect/runbooks/",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--title", required=True, help="Runbook title")
    p.add_argument("--what", required=True, help="One-line description")
    p.add_argument(
        "--step", dest="steps", action="append", default=[],
        metavar="STEP", help="Step description (repeat for multiple steps)",
    )
    p.add_argument(
        "--fail", dest="failures", action="append", default=[],
        metavar="FAILURE", help="Known failure description",
    )
    p.add_argument(
        "--prereq", dest="prerequisites", action="append", default=[],
        metavar="PREREQ", help="Prerequisite (repeat for multiple)",
    )
    p.add_argument("--session", type=int, default=None, help="Session number")
    p.add_argument(
        "--dir", dest="runbooks_dir", default=None,
        help="Override output directory (default: selfconnect/runbooks/)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not args.steps:
        parser.error("At least one --step is required")

    out_dir = Path(args.runbooks_dir) if args.runbooks_dir else None
    path = write_runbook(
        title=args.title,
        what=args.what,
        steps=args.steps,
        known_failures=args.failures or None,
        prerequisites=args.prerequisites or None,
        session=args.session,
        runbooks_dir=out_dir,
    )
    print(f"Runbook written: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
