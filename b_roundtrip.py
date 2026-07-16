"""Clean B roundtrip: inject task → wait → read → extract → execute once."""
import sys, os, time, re
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from self_connect import list_windows, send_string, get_text_uia
from mesh_exec_guard import run_agent_python_snippet

B_HWND = 0x01fa0d74
A_HWND = 0x0ea80dfe
SC_PATH = 'C:/Users/techai/PKA testing/selfconnect'

wins = list_windows()
b = next((w for w in wins if w.hwnd == B_HWND), None)
if not b:
    print("B not found"); sys.exit(1)

# Snapshot B's current text so we only look at NEW output
before = get_text_uia(B_HWND) or ""

# Inject a clean, simple task — no encoding tricks
task = (
    "Agent-A task: output ONLY this exact line, nothing else:\n"
    "python -c \"import sys; sys.path.insert(0, 'C:/Users/techai/PKA testing/selfconnect'); "
    "from self_connect import list_windows, send_string; "
    "a=next((w for w in list_windows() if w.hwnd==0x0ea80dfe),None); "
    "send_string(a,'B-REPLY: roundtrip confirmed\\r',char_delay=0.02)\""
)
print("Injecting task to B...")
send_string(b, task + "\r", char_delay=0.015)

# Wait for B to finish responding
print("Waiting 20s for B...")
time.sleep(20)

# Read B's new output only
after = get_text_uia(B_HWND) or ""
new_text = after[len(before):]
print(f"\n--- B new output ---\n{new_text[-1500:]}\n--- end ---")

# Extract the python -c line (handle terminal line wrapping)
all_lines = after.splitlines()
cmd_parts = []
collecting = False
for line in all_lines:
    s = line.strip()
    if s.startswith('python -c "'):
        collecting = True
        cmd_parts = [s]
    elif collecting:
        cmd_parts.append(s)
        # Stop when we have balanced quotes
        joined = ' '.join(cmd_parts)
        if joined.count('"') % 2 == 0:
            break

if not cmd_parts:
    print("No python -c line found in B's output.")
    sys.exit(1)

cmd = ' '.join(cmd_parts)
print(f"\nExecuting B's command:\n  {cmd[:120]}...")

# SECURITY (#R-04): B's output is untrusted. Never shell-exec it. Extract the
# 'python -c' snippet and run it opt-in only (SC_ALLOW_REMOTE_EXEC=1), no shell.
m = re.match(r'''^python\s+-c\s+(['"])(?P<code>.*)\1\s*$''', cmd, re.DOTALL)
if not m:
    print("Refused: not a recognized 'python -c' snippet.")
    sys.exit(1)
result = run_agent_python_snippet(m.group('code'), cwd=SC_PATH)
if result is None:
    sys.exit(1)  # refused (opt-in not set)
if result.returncode == 0:
    print("Done — watch for B-REPLY in Agent-A's input.")
else:
    print(f"Error: {result.stderr[:300]}")
