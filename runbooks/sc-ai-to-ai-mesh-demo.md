# Runbook: SelfConnect AI-to-AI Multi-Agent Mesh Demo

**Last Updated**: 2026-05-13
**Owner**: SelfConnect Team
**Severity**: P1 (core capability demonstration — proves patent claims)
**Estimated Duration**: 5-10 minutes
**Review Cycle**: After any change to `self_connect.py`, `sc_mesh_demo.py`, or Claude Code version

---

## What This Demonstrates

SelfConnect's core purpose: two separate Claude Code processes (AGENT-A, AGENT-B) running in
separate Windows Terminal windows, controlled by a third SC-CONTROLLER window via pure Win32.

```
┌────────────────┐   PostMessage(WM_CHAR)    ┌──────────────────┐
│   AGENT-A      │◄────────────────────────  │  SC-CONTROLLER   │
│  Claude Code   │                            │  sc_mesh_demo.py │
└────────────────┘                            └──────────────────┘
                                                       │
┌────────────────┐   PostMessage(WM_CHAR)              │
│   AGENT-B      │◄────────────────────────────────────┘
│  Claude Code   │
└────────────────┘
```

**No API calls between agents. No shared memory server. No focus stealing.**
SC-CONTROLLER reads agent responses via UIA (get_text_uia) and screenshots (PrintWindow).

---

## Prerequisites

- [ ] Python 3.12+ with selfconnect-alt deps: `pip install -e .[full]` in selfconnect-alt/
- [ ] Windows Terminal (`wt.exe`) available in PATH
- [ ] `claude` CLI available in PATH (Claude Code installed)
- [ ] Running as normal user (NOT elevated) — elevation breaks console attachment
- [ ] At least one existing WT window open (not strictly required, but avoids startup delays)

---

## Steps

### Step 1: Open AGENT-A window (estimated: 15 sec)

Open a **separate** Windows Terminal window (own title bar, not a tab) running Claude Code,
titled AGENT-A:

```cmd
wt.exe -w new --title "AGENT-A" cmd /k "cd /d \"C:\Users\techai\PKA testing\selfconnect-alt\" && claude"
```

Wait for Claude Code to finish initializing (the TUI prompt appears).

**Expected:** A new WT window appears with title `AGENT-A`, Claude Code TUI loaded.

**If title shows `cmd.exe` instead of `AGENT-A`:**
Windows Terminal sometimes takes 2-5 seconds to apply the `--title` flag.
Poll from Python:
```python
import sys, time
sys.path.insert(0, r'C:\Users\techai\PKA testing\selfconnect-alt')
from self_connect import list_windows
for _ in range(20):
    wins = [w for w in list_windows() if 'AGENT-A' in w.title.upper()]
    if wins:
        print(f"Found: hwnd={wins[0].hwnd}  title={wins[0].title!r}"); break
    time.sleep(1.5)
```

---

### Step 2: Open AGENT-B window (estimated: 15 sec)

```cmd
wt.exe -w new --title "AGENT-B" cmd /k "cd /d \"C:\Users\techai\PKA testing\selfconnect-alt\" && claude"
```

Wait for Claude Code TUI.

**Expected:** Second separate WT window with title `AGENT-B`, Claude Code TUI loaded.

**If Claude Code does not start automatically:**
The `claude` command may not be in the PATH inside the new window's cmd session.
Fix:
```cmd
wt.exe -w new --title "AGENT-B" cmd /k "cd /d \"C:\Users\techai\PKA testing\selfconnect-alt\" && C:\Users\techai\AppData\Roaming\npm\claude.cmd"
```

---

### Step 3: Open SC-CONTROLLER window (estimated: 5 sec)

```cmd
wt.exe -w new --title "SC-CONTROLLER" cmd /k "cd /d \"C:\Users\techai\PKA testing\selfconnect-alt\" && python sc_mesh_demo.py"
```

**Expected:** A third separate WT window opens and immediately begins running the demo.

---

### Step 4: Watch SC-CONTROLLER output (estimated: 30-60 sec)

The script runs 5 numbered phases:

```
============================================================
  SELFCONNECT MESH DEMO
  Agent A <--Win32--> SC-CONTROLLER <--Win32--> Agent B
============================================================

[1/5] Locating AGENT-A...
      Found: hwnd=XXXXXXXXXX  title='AGENT-A'
[2/5] Locating AGENT-B...
      Found: hwnd=XXXXXXXXXX  title='AGENT-B'

[3/5] Briefing AGENT-A via PostMessage(WM_CHAR)...
      Injected briefing. Screenshot: demo_agent_a_briefed.png
      UIA confirms text in buffer: True

[4/5] Briefing AGENT-B via PostMessage(WM_CHAR)...
      Injected briefing. Screenshot: demo_agent_b_briefed.png
      UIA confirms text in buffer: True

[5/5] Reading both agents, relaying messages cross-agent...
  Agent A responded: True  (XXXX chars in buffer)
  Agent B responded: True  (XXXX chars in buffer)

============================================================
  MESH DEMO COMPLETE
  A briefed:  True
  B briefed:  True
  A->B relay: DONE (relay message injected into A)
  Screenshots: demo_agent_a_briefed.png, demo_agent_b_briefed.png, demo_relay_to_a.png
============================================================
```

**Simultaneously**, watch AGENT-A and AGENT-B windows — you will see Claude Code receive the
injected text and start generating a response.

---

### Step 5: Verify proof screenshots (estimated: 10 sec)

```cmd
dir "C:\Users\techai\PKA testing\selfconnect-alt\demo_*.png"
```

**Expected output:** 3 non-zero-byte PNG files:
```
demo_agent_a_briefed.png
demo_agent_b_briefed.png
demo_relay_to_a.png
```

Open any of them to see the Claude Code TUI with injected text visible.

**If PNG files are missing or zero bytes:**
`capture_window()` may have failed. This is non-critical — the injection still occurred.
Capture manually:
```python
import sys
sys.path.insert(0, r'C:\Users\techai\PKA testing\selfconnect-alt')
from self_connect import list_windows, capture_window
win = next(w for w in list_windows() if 'AGENT-A' in w.title.upper())
img = capture_window(win.hwnd)
img.save('manual_capture.png')
```

---

### Step 6: Confirm agent responses via UIA (estimated: 15 sec)

After the demo completes, read AGENT-A's TUI buffer directly:

```python
import sys
sys.path.insert(0, r'C:\Users\techai\PKA testing\selfconnect-alt')
from self_connect import list_windows, get_text_uia

for name in ['AGENT-A', 'AGENT-B']:
    win = next((w for w in list_windows() if name in w.title.upper()), None)
    if win:
        text = get_text_uia(win.hwnd) or ''
        print(f"\n{name} ({len(text)} chars):")
        print(text[-500:])   # last 500 chars of TUI buffer
```

**Expected:** Both agents show the injected briefing text AND Claude's response in their TUI.
AGENT-A should contain the relay message (e.g. `Agent B is ONLINE. Mesh is LIVE.`).

---

### Step 7: Run extended multi-turn mesh (optional, estimated: 2-5 min)

To demonstrate full back-and-forth relay between agents, inject a multi-turn task:

```python
import sys, time
sys.path.insert(0, r'C:\Users\techai\PKA testing\selfconnect-alt')
from self_connect import list_windows, send_string, get_text_uia

agent_a = next(w for w in list_windows() if 'AGENT-A' in w.title.upper())
agent_b = next(w for w in list_windows() if 'AGENT-B' in w.title.upper())

# Round 1: ask Agent A to generate a question for Agent B
send_string(agent_a, "Generate ONE yes/no question about Python and output ONLY the question.\r", mode="turbo")
time.sleep(8)

# Read A's question
a_text = get_text_uia(agent_a.hwnd) or ''
# Extract last line (A's response)
question = [l.strip() for l in a_text.splitlines() if l.strip()][-1]
print(f"Agent A generated: {question!r}")

# Round 2: relay question to Agent B
send_string(agent_b, f"Answer YES or NO: {question}\r", mode="turbo")
time.sleep(6)

# Read B's answer
b_text = get_text_uia(agent_b.hwnd) or ''
answer = [l.strip() for l in b_text.splitlines() if l.strip()][-1]
print(f"Agent B answered: {answer!r}")

# Round 3: relay B's answer back to A
send_string(agent_a, f"Agent B says: {answer}. Reply with MESH_ROUND_COMPLETE.\r", mode="turbo")
time.sleep(6)

a_final = get_text_uia(agent_a.hwnd) or ''
print(f"Mesh complete: {'MESH_ROUND_COMPLETE' in a_final}")
```

**Expected:** `Mesh complete: True` — Agent A confirmed the relay loop.

---

## Known Failures and Remediation

| Failure | Root Cause | Fix |
|---------|-----------|-----|
| `ERROR: AGENT-A window not found` | WT `--title` not applied yet | Wait 5s after opening, re-run demo |
| `UIA confirms text in buffer: False` | Claude Code TUI not initialized when injection ran | Re-run: `send_string` after `time.sleep(5)` at top of script |
| `Agent A responded: False` | Claude took >8s to respond (slow machine / approval prompt pending) | Increase `time.sleep(8)` to `time.sleep(15)` in sc_mesh_demo.py |
| `capture_window() returns None` | WT window minimized or off-screen | Restore window to visible, retry |
| `get_text_uia returns empty string` | UIA accessibility bridge not initialized | Run `python -c "import comtypes.client; comtypes.client.GetModule('UIAutomationCore.dll')"` |
| `send_string mode="turbo" injects garbled text` | High CPU load causes WM_CHAR race | Switch to `mode="wm_char"` (default) |
| Agent receives text but doesn't respond | Claude Code waiting for `[Y/n]` approval prompt | Inject approval: `send_string(agent, 'y\r')` or start `python approval_partner.py` |
| Both agents show same hwnd | title strings collide | Re-title one window: use WT settings JSON or click tab title to rename |

---

## What You're Seeing (Patent Relevance)

When the demo runs successfully, these patent claims are live-proven:

| Claim | Evidence |
|-------|---------|
| Background PostMessage(WM_CHAR) to ConPTY | SC-CONTROLLER injected text; agents received it without focus |
| PrintWindow visual readback as receive channel | `capture_window()` captured live screenshots of agents mid-response |
| UIA readback | `get_text_uia()` confirmed injected text appears in agent TUI buffers |
| Cross-vendor AI-to-AI mesh | Two separate Claude Code processes exchanged information with zero API calls |
| Policy-gated relay | SC-CONTROLLER relayed B's status to A only after reading and verifying response |

---

## Verification Checklist

- [ ] 3 separate WT windows opened (AGENT-A, AGENT-B, SC-CONTROLLER)
- [ ] SC-CONTROLLER output shows `UIA confirms text in buffer: True` for both agents
- [ ] SC-CONTROLLER output shows `Agent A responded: True` and `Agent B responded: True`
- [ ] `demo_agent_a_briefed.png` shows Claude Code TUI with injected text visible
- [ ] `demo_relay_to_a.png` shows relay message in AGENT-A's TUI
- [ ] No focus was stolen from user's current window during the entire run

---

## Rollback

No persistent state modified. All 3 windows can be closed freely.
PNG screenshots are in `selfconnect-alt/` — delete if not needed.

---

## Escalation

| Condition | Contact | Method |
|-----------|---------|--------|
| `send_string` injects but Claude never receives text | Repo owner | GitHub Issue — include WT version and `wt --version` output |
| `get_text_uia` returns empty on all windows | Repo owner | GitHub Issue — include pywinauto version and UIA accessibility tree dump |
| Demo hangs at `[5/5]` > 30s | Kill with Ctrl+C; check if approval prompt is blocking agent | File issue if it happens consistently |

---

## Post-Run

- [ ] Archive screenshots: copy `demo_*.png` to a dated folder
- [ ] Push any changes to `sc_mesh_demo.py` to `rblake2320/selfconnect-alt`
- [ ] If adding new agent types (Codex, Gemini), reference `runbooks/fix_antigravity_gemini.md`
  and `runbooks/spawn_claude_terminal.md` for setup
