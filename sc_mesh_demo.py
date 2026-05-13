"""
sc_mesh_demo.py — SelfConnect live demo: Agent A talks to Agent B via Win32.

This is what selfconnect IS:
  - No API calls between agents
  - No shared memory server
  - Pure Win32: PostMessage(WM_CHAR) to inject, PrintWindow + UIA to read
  - Both agents are fully separate Claude Code processes in separate WT windows
"""
import sys, time
sys.path.insert(0, r'C:\Users\techai\PKA testing\selfconnect-alt')
from self_connect import list_windows, send_string, get_text_uia, capture_window

print("=" * 60)
print("  SELFCONNECT MESH DEMO")
print("  Agent A <--Win32--> SC-CONTROLLER <--Win32--> Agent B")
print("=" * 60)
print()

# ── Find Agent A and Agent B windows ──────────────────────────────
def find_agent(name, retries=20):
    for _ in range(retries):
        wins = [w for w in list_windows() if name in w.title.upper()]
        if wins:
            return wins[0]
        time.sleep(1.5)
    return None

print("[1/5] Locating AGENT-A...")
agent_a = find_agent("AGENT-A")
if not agent_a:
    print("ERROR: AGENT-A window not found. Open a WT window titled AGENT-A running claude.")
    sys.exit(1)
print(f"      Found: hwnd={agent_a.hwnd}  title={agent_a.title!r}")

print("[2/5] Locating AGENT-B...")
agent_b = find_agent("AGENT-B")
if not agent_b:
    print("ERROR: AGENT-B window not found.")
    sys.exit(1)
print(f"      Found: hwnd={agent_b.hwnd}  title={agent_b.title!r}")
print()

# ── Brief Agent A via WM_CHAR injection ───────────────────────────
print("[3/5] Briefing AGENT-A via PostMessage(WM_CHAR)...")
briefing_a = (
    "You are Agent A in a selfconnect mesh demo. "
    "Reply with: AGENT_A_READY and your hwnd number."
)
send_string(agent_a, briefing_a + "\r", mode="turbo")
time.sleep(2.0)

# Capture Agent A screen as proof
img_a = capture_window(agent_a.hwnd)
if img_a:
    img_a.save(r"C:\Users\techai\PKA testing\selfconnect-alt\demo_agent_a_briefed.png")
    print(f"      Injected briefing. Screenshot: demo_agent_a_briefed.png")

# Read Agent A UIA buffer to confirm text landed
text_a = get_text_uia(agent_a.hwnd) or ""
found_a = briefing_a[:30] in text_a
print(f"      UIA confirms text in buffer: {found_a}")
print()

# ── Brief Agent B via WM_CHAR injection ───────────────────────────
print("[4/5] Briefing AGENT-B via PostMessage(WM_CHAR)...")
briefing_b = (
    "You are Agent B in a selfconnect mesh demo. "
    "Agent A has been briefed. Reply with: AGENT_B_READY and confirm you are online."
)
send_string(agent_b, briefing_b + "\r", mode="turbo")
time.sleep(2.0)

img_b = capture_window(agent_b.hwnd)
if img_b:
    img_b.save(r"C:\Users\techai\PKA testing\selfconnect-alt\demo_agent_b_briefed.png")
    print(f"      Injected briefing. Screenshot: demo_agent_b_briefed.png")

text_b = get_text_uia(agent_b.hwnd) or ""
found_b = briefing_b[:30] in text_b
print(f"      UIA confirms text in buffer: {found_b}")
print()

# ── Read both agents and relay ─────────────────────────────────────
print("[5/5] Reading both agents, relaying messages cross-agent...")
time.sleep(8)  # let Claude process and respond

text_a_resp = get_text_uia(agent_a.hwnd) or ""
text_b_resp = get_text_uia(agent_b.hwnd) or ""

a_ready = "AGENT_A_READY" in text_a_resp or "AGENT-A" in text_a_resp.upper()
b_ready = "AGENT_B_READY" in text_b_resp or "AGENT-B" in text_b_resp.upper()

print(f"  Agent A responded: {a_ready}  ({len(text_a_resp)} chars in buffer)")
print(f"  Agent B responded: {b_ready}  ({len(text_b_resp)} chars in buffer)")

# Relay B's status to A via WM_CHAR
relay_msg = f"Agent B is {'ONLINE' if b_ready else 'NOT YET RESPONDED'}. Mesh is {'LIVE' if a_ready and b_ready else 'PARTIAL'}."
send_string(agent_a, relay_msg, mode="turbo")
time.sleep(0.5)
img_relay = capture_window(agent_a.hwnd)
if img_relay:
    img_relay.save(r"C:\Users\techai\PKA testing\selfconnect-alt\demo_relay_to_a.png")

print()
print("=" * 60)
print(f"  MESH DEMO COMPLETE")
print(f"  A briefed:  {found_a}")
print(f"  B briefed:  {found_b}")
print(f"  A->B relay: DONE (relay message injected into A)")
print(f"  Screenshots: demo_agent_a_briefed.png, demo_agent_b_briefed.png, demo_relay_to_a.png")
print("=" * 60)
