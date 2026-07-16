"""Watch Agent B's terminal and relay only allowlisted reply scripts."""
import os
import sys
import time

from mesh_exec_guard import UnsafeCommand, run_allowlisted_script
from self_connect import get_text_uia

sys.stdout.reconfigure(encoding="utf-8")

B_HWND = 0x01FA0D74
POLL_INTERVAL = 2
SC_DIR = os.path.dirname(os.path.abspath(__file__))
seen_commands = set()

print(f"[watcher] Monitoring Agent B at 0x{B_HWND:x}...")
print("[watcher] Only allowlisted b_send.py / b_reply.py commands can run.")
print("[watcher] Press Ctrl+C to stop.\n")

while True:
    try:
        text = get_text_uia(B_HWND) or ""
        for raw_line in text.splitlines():
            command = raw_line.strip()
            if not (
                command.startswith("python b_send.py")
                or command.startswith("python b_reply.py")
            ):
                continue
            if command in seen_commands:
                continue
            seen_commands.add(command)

            print(f"\n[watcher] NEW allowlisted reply from B:\n  {command[:120]}...")
            try:
                result = run_allowlisted_script(
                    command,
                    ("b_send.py", "b_reply.py"),
                    cwd=SC_DIR,
                )
            except UnsafeCommand as exc:
                print(f"[watcher] REFUSED: {exc}")
                continue
            if result.returncode == 0:
                print(f"[watcher] OK - {result.stdout.strip()}")
            else:
                print(f"[watcher] ERROR: {result.stderr.strip()[:200]}")

        time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        print("\n[watcher] Stopped.")
        break
    except Exception as exc:
        print(f"[watcher] poll error: {exc}")
        time.sleep(POLL_INTERVAL)
