---
name: SelfConnect Inter-Terminal Communication
version: 2.0.0
description: Inject text into Claude Code terminals, spawn helper agents, and coordinate AI-to-AI mesh work. Windows uses PostMessage(WM_CHAR). Mac uses osascript/AppleScript + pynput. Triggers on "talk to another terminal", "inject into terminal", "spawn a helper", "send to another claude", "inter-terminal", "selfconnect", "agent mesh", "coordinate terminals", "multi-agent".
author: SelfConnect Team
tags:
  - selfconnect
  - inter-terminal
  - agent-mesh
  - windows-terminal
  - macos-terminal
  - cross-platform
  - automation
platforms:
  - windows
  - macos
---

# SelfConnect Inter-Terminal Communication

Coordinate Claude Code instances across separate terminal windows without API calls.
Each agent is a fully independent Claude Code process. The controller injects via OS-native
input APIs and reads back via accessibility APIs.

```
┌──────────────┐   OS-native injection     ┌──────────────────┐
│   AGENT-A    │◄────────────────────────  │   SC-CONTROLLER  │
│  Claude Code │                            │  (this terminal) │
└──────────────┘                            └──────────────────┘
                                                    │
┌──────────────┐   OS-native injection              │
│   AGENT-B    │◄───────────────────────────────────┘
│  Claude Code │
└──────────────┘
```

---

## Platform Detection

```python
import platform
IS_WINDOWS = platform.system() == "Windows"
IS_MAC     = platform.system() == "Darwin"
```

---

## Windows Path — PostMessage(WM_CHAR)

**SDK:** `selfconnect/self_connect.py` from `github.com/rblake2320/selfconnect`

### Setup

```python
import sys, time
SC_DIR = r"C:\Users\techai\PKA testing\selfconnect"   # adjust to your path
sys.path.insert(0, SC_DIR)
from self_connect import list_windows, send_string, get_text_uia, capture_window
```

### Find Windows

```python
wins = list_windows()

# Find by title keyword
agent_a = next((w for w in wins if 'AGENT-A' in w.title.upper()), None)

# Find all Claude Code terminals
claude_wins = [w for w in wins if w.class_name == 'CASCADIA_HOSTING_WINDOW_CLASS']

# Print all (safe encoding)
for w in wins:
    print(f"hwnd={w.hwnd:#010x}  {w.title.encode('ascii','replace').decode()[:60]}")
```

### Inject Text

```python
# Standard — no focus required, background-safe
send_string(agent_a, "Your message here\r", mode="turbo")

# Slower but more reliable on busy systems
send_string(agent_a, "Your message here\r", char_delay=0.02)
```

**Rules:**
- Always append `\r` (not `\n`) — ConPTY maps `\r` to Enter
- `mode="turbo"` sends all WM_CHAR messages in rapid burst
- `mode="wm_char"` uses `char_delay=0.02` — use if turbo drops chars

### Read Agent Response

```python
# UIA accessibility readback
text = get_text_uia(agent_a.hwnd) or ""
print(text[-1000:])  # last 1000 chars of TUI buffer

# Screenshot proof
img = capture_window(agent_a.hwnd)   # returns PIL Image
img.save("agent_a_state.png")
```

### Spawn New Agent Window

```python
import subprocess

subprocess.Popen(
    ['wt.exe', '-w', 'new', '--title', 'AGENT-A',
     'cmd', '/k', r'cd /d "C:\path\to\project" && claude'],
    creationflags=0x00000008  # DETACHED_PROCESS
)

# Poll until window appears
for _ in range(30):
    time.sleep(1.5)
    wins = [w for w in list_windows() if 'AGENT-A' in w.title.upper()]
    if wins:
        agent_a = wins[0]
        break

# Wait for Claude Code TUI to initialize
time.sleep(20)
```

**Why 20s:** Claude Code TUI takes 15-20s from cold `claude` command.

### WM_CHAR 0x0D Nuclear Option

When `send_string("\r")` doesn't submit:

```python
import ctypes
user32 = ctypes.windll.user32
user32.PostMessageW(agent_a.hwnd, 0x0102, 0x000D, 0x001C0001)
```

---

## macOS Path — AppleScript + pynput

**No SDK required** — uses built-in `osascript` + optional `pynput`.

### Prerequisites

```bash
# Install pynput for keystroke injection
pip install pynput

# Grant Accessibility access (one-time):
# System Preferences → Privacy & Security → Accessibility → add Terminal/iTerm2
```

### Find Terminal Windows

```python
import subprocess

def list_terminal_windows():
    """Return list of {id, title, app} for visible terminal windows."""
    script = '''
    tell application "System Events"
        set result to {}
        set appList to {"Terminal", "iTerm2", "iTerm"}
        repeat with appName in appList
            if exists process appName then
                tell process appName
                    repeat with w in windows
                        set result to result & {{name of w, appName}}
                    end repeat
                end tell
            end if
        end repeat
        return result
    end tell
    '''
    out = subprocess.check_output(['osascript', '-e', script], text=True)
    return out.strip()

print(list_terminal_windows())
```

### Inject Text (AppleScript — creates new tab or uses existing)

```python
import subprocess, time

def send_to_terminal(text: str, window_index: int = 1, app: str = "Terminal"):
    """Inject text into a Terminal window via AppleScript keystroke."""
    # Escape double quotes
    safe = text.replace('"', '\\"').replace('\r', '').replace('\n', '')
    script = f'''
    tell application "{app}"
        activate
    end tell
    tell application "System Events"
        tell process "{app}"
            keystroke "{safe}"
            key code 36  -- Return key
        end tell
    end tell
    '''
    subprocess.run(['osascript', '-e', script], check=True)

send_to_terminal("You are AGENT-A. Reply with AGENT_A_ONLINE.")
```

### Inject Text (pynput — more reliable for long strings)

```python
from pynput.keyboard import Key, Controller
import subprocess, time

def focus_terminal_window(title_contains: str, app: str = "Terminal"):
    """Bring a Terminal window to front by partial title match."""
    script = f'''
    tell application "{app}"
        activate
        set targetWindow to first window whose name contains "{title_contains}"
        set index of targetWindow to 1
    end tell
    '''
    subprocess.run(['osascript', '-e', script])
    time.sleep(0.5)

def inject_text_mac(text: str, title_contains: str = "AGENT-A"):
    keyboard = Controller()
    focus_terminal_window(title_contains)
    time.sleep(0.3)
    # Type each character
    for ch in text:
        keyboard.type(ch)
        time.sleep(0.01)
    keyboard.press(Key.enter)
    keyboard.release(Key.enter)

inject_text_mac("You are AGENT-A. Reply with AGENT_A_ONLINE.", "AGENT-A")
```

### Read Agent Response (AppleScript)

```python
import subprocess

def read_terminal_contents(window_index: int = 1, app: str = "Terminal") -> str:
    script = f'''
    tell application "{app}"
        return contents of window {window_index}
    end tell
    '''
    return subprocess.check_output(['osascript', '-e', script], text=True)

response = read_terminal_contents(1)
print(response[-1000:])
```

### Screenshot Proof (macOS)

```python
import subprocess
from PIL import Image
import io

def capture_window_mac(window_title: str) -> Image.Image:
    """Capture screenshot of a window by title using screencapture."""
    subprocess.run(['screencapture', '-l', '0', '-x', '/tmp/sc_capture.png'])
    # For window-specific capture, use screencapture -l <windowID>
    # Get window IDs via: python -c "from Quartz import CGWindowListCopyWindowInfo, kCGWindowListOptionAll; import Quartz; [print(w) for w in Quartz.CGWindowListCopyWindowInfo(kCGWindowListOptionAll, 0)]"
    return Image.open('/tmp/sc_capture.png')
```

### Spawn New Agent Window (macOS)

```python
import subprocess, time

def spawn_agent_mac(title: str, work_dir: str, app: str = "Terminal"):
    script = f'''
    tell application "{app}"
        do script "cd \\"{work_dir}\\" && echo -ne \\\"\\\\033]0;{title}\\\\007\\\" && claude"
    end tell
    '''
    subprocess.run(['osascript', '-e', script])
    time.sleep(20)  # Wait for Claude Code TUI to initialize
    print(f"Spawned {title!r} — ready for injection")

spawn_agent_mac("AGENT-A", "/path/to/project")
```

---

## Cross-Platform Controller Template

```python
"""sc_controller.py — cross-platform SelfConnect mesh controller."""
import platform, subprocess, time, sys

PLATFORM = platform.system()

if PLATFORM == "Windows":
    SC_DIR = r"C:\Users\techai\PKA testing\selfconnect"
    sys.path.insert(0, SC_DIR)
    from self_connect import list_windows, send_string, get_text_uia

    def find_agent(name: str):
        for _ in range(20):
            wins = [w for w in list_windows() if name in w.title.upper()]
            if wins: return wins[0]
            time.sleep(1.5)
        return None

    def inject(agent, text: str):
        send_string(agent, text + "\r", mode="turbo")

    def read_agent(agent) -> str:
        return get_text_uia(agent.hwnd) or ""

elif PLATFORM == "Darwin":
    from pynput.keyboard import Key, Controller
    _kb = Controller()

    def find_agent(name: str):
        # Returns the window title string (used as identifier)
        script = f'tell application "Terminal" to return name of first window whose name contains "{name}"'
        try:
            return subprocess.check_output(['osascript', '-e', script], text=True).strip()
        except:
            return None

    def inject(agent: str, text: str):
        # agent is the window title
        script = f'tell application "Terminal" to activate\ntell application "System Events" to tell process "Terminal" to set frontmost to true'
        subprocess.run(['osascript', '-e', script])
        time.sleep(0.3)
        _kb.type(text)
        _kb.press(Key.enter)
        _kb.release(Key.enter)

    def read_agent(agent: str) -> str:
        script = 'tell application "Terminal" to return contents of front window'
        return subprocess.check_output(['osascript', '-e', script], text=True)

# ── Main mesh demo ──────────────────────────────────────────────────
agent_a = find_agent("AGENT-A")
agent_b = find_agent("AGENT-B")

if not agent_a or not agent_b:
    print("ERROR: open AGENT-A and AGENT-B terminals running claude first")
    sys.exit(1)

inject(agent_a, "You are AGENT-A. Reply with AGENT_A_ONLINE and your working directory.")
time.sleep(8)

inject(agent_b, "You are AGENT-B. Reply with AGENT_B_ONLINE and confirm you are ready.")
time.sleep(8)

a_resp = read_agent(agent_a)
b_resp = read_agent(agent_b)

a_ok = "AGENT_A_ONLINE" in a_resp or "AGENT-A" in a_resp.upper()
b_ok = "AGENT_B_ONLINE" in b_resp or "AGENT-B" in b_resp.upper()

print(f"Agent A: {'LIVE' if a_ok else 'NO RESPONSE'}")
print(f"Agent B: {'LIVE' if b_ok else 'NO RESPONSE'}")
print(f"Mesh: {'ACTIVE' if a_ok and b_ok else 'PARTIAL'}")
```

---

## Known Failure Modes (Both Platforms)

| Symptom | Platform | Root Cause | Fix |
|---------|----------|-----------|-----|
| Text injected but Claude never receives it | Win | Claude TUI not yet initialized | Wait 20s after opening, retry |
| `send_string` injects but Enter doesn't submit | Win | WM_CHAR 0x0D not routing through XAML | Use PostMessageW(hwnd, 0x0102, 0x000D, 0x001C0001) |
| `get_text_uia` returns empty | Win | UIA tree not initialized | Run `python -c "import comtypes.client; comtypes.client.GetModule('UIAutomationCore.dll')"` |
| osascript permission denied | Mac | Accessibility not granted | System Preferences → Privacy → Accessibility → add Terminal |
| Keystrokes go to wrong window | Mac | Focus changed between focus+type | Increase sleep between activate and keystroke |
| `pynput` not found | Mac | Not installed | `pip install pynput` |
| Claude Code TUI shows text but doesn't process | Both | Approval prompt blocking | Inject `y\r` or run approval_partner.py (Windows) |
| Agent responds but response unreadable | Both | Buffer trimmed | Read last N chars only: `text[-2000:]` |

---

## Team Inbox Protocol (Both Platforms)

Agents communicate async via shared filesystem:

```
<workspace>/Team Inbox/
  msg_from_<sender>_to_<recipient>.md    ← drop a task
  helper-a-result.md                     ← helper reports back

<workspace>/Owner's Inbox/
  <deliverable>.md                       ← completed work for human
```

### Polling pattern

```python
from pathlib import Path
import time

inbox = Path("/path/to/Team Inbox")
target = inbox / "helper-a-result.md"

for i in range(20):
    time.sleep(15)
    if target.exists():
        print(target.read_text())
        break
    print(f"  {i*15+15}s — waiting for agent reply...")
```

---

## Install from GitHub

```bash
# Clone the full SDK + runbooks + demos
git clone https://github.com/rblake2320/selfconnect-alt.git
cd selfconnect-alt
pip install -e .[full]          # Windows
pip install -e .                # Mac (core only — Win32 deps skipped)

# Mac additional deps
pip install pynput pyobjc-framework-Quartz   # for screenshot capture

# Run the mesh demo (opens AGENT-A, AGENT-B, SC-CONTROLLER)
python sc_mesh_demo.py          # Windows
# Mac: open three Terminal tabs/windows manually, then run the cross-platform controller
python sc_controller.py
```

---

## Runbooks in This Repo

| File | What |
|------|------|
| `runbooks/sc-ai-to-ai-mesh-demo.md` | Live mesh demo: AGENT-A + AGENT-B + SC-CONTROLLER |
| `runbooks/spawn_claude_terminal.md` | Spawn a new Claude Code WT window (Windows) |
| `runbooks/sc-alt-unit-test-suite.md` | Run 170 unit tests |
| `runbooks/sc-alt-win32-integration-test.md` | Run 39 real Win32 integration tests |
| `runbooks/sc-alt-benchmark.md` | Head-to-head benchmark vs original SDK |
| `runbooks/enter_claude_tui.md` | Submit pending input in Claude Code TUI |
| `runbooks/peer_approval_check.md` | Policy-gated approval relay |
| `runbooks/cross_machine_mesh.md` | Windows ↔ Spark-1 ↔ Spark-2 cross-machine mesh |
