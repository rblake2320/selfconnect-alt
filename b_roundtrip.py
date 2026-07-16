"""Clean B roundtrip: inject task, then relay an allowlisted reply once."""
import os
import sys
import time

from mesh_exec_guard import UnsafeCommand, run_allowlisted_script
from self_connect import get_text_uia, list_windows, send_string

sys.stdout.reconfigure(encoding="utf-8")

B_HWND = 0x01FA0D74
SC_PATH = os.path.dirname(os.path.abspath(__file__))

wins = list_windows()
b = next((window for window in wins if window.hwnd == B_HWND), None)
if not b:
    print("B not found")
    sys.exit(1)

before = get_text_uia(B_HWND) or ""
task = (
    "Agent-A task: output ONLY this exact line, nothing else:\n"
    "python b_send.py B-REPLY: roundtrip confirmed"
)
print("Injecting task to B...")
send_string(b, task + "\r", char_delay=0.015)

print("Waiting 20s for B...")
time.sleep(20)

after = get_text_uia(B_HWND) or ""
new_text = after[len(before) :]
print(f"\n--- B new output ---\n{new_text[-1500:]}\n--- end ---")

command = next(
    (
        line.strip()
        for line in reversed(after.splitlines())
        if line.strip().startswith("python b_send.py")
        or line.strip().startswith("python b_reply.py")
    ),
    None,
)
if not command:
    print("No allowlisted reply command found in B's output.")
    sys.exit(1)

print(f"\nExecuting B's allowlisted reply:\n  {command[:120]}...")
try:
    result = run_allowlisted_script(
        command,
        ("b_send.py", "b_reply.py"),
        cwd=SC_PATH,
    )
except UnsafeCommand as exc:
    print(f"Refused: {exc}")
    sys.exit(1)

if result.returncode == 0:
    print("Done - watch for B-REPLY in Agent-A's input.")
else:
    print(f"Error: {result.stderr[:300]}")
    sys.exit(result.returncode)
