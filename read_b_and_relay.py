"""Read Agent B's terminal and relay only an allowlisted reply script."""
import os
import sys

from mesh_exec_guard import UnsafeCommand, run_allowlisted_script
from self_connect import get_text_uia

sys.stdout.reconfigure(encoding="utf-8")

B_HWND = 0x01FA0D74
SC_DIR = os.path.dirname(os.path.abspath(__file__))

print("Reading Agent B terminal...")
text = get_text_uia(B_HWND)
if not text:
    print("No text captured from B")
    sys.exit(1)

print("\n--- B's terminal (last 2000 chars) ---")
print(text[-2000:])
print("--- end ---\n")

command = next(
    (
        line.strip()
        for line in reversed(text.splitlines())
        if line.strip().startswith("python b_send.py")
        or line.strip().startswith("python b_reply.py")
    ),
    None,
)
if not command:
    print("No allowlisted reply found yet.")
    sys.exit(1)

print(f"\nFound B's allowlisted reply:\n  {command}\n")
try:
    result = run_allowlisted_script(
        command,
        ("b_send.py", "b_reply.py"),
        cwd=SC_DIR,
    )
except UnsafeCommand as exc:
    print(f"Refused unsafe reply: {exc}")
    sys.exit(1)

print("stdout:", result.stdout)
print("stderr:", result.stderr)
print("returncode:", result.returncode)
sys.exit(result.returncode)
