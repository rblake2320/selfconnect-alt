"""
Stress: WM_CHAR flood INTO a live Claude Code terminal.
Injects real prompts, reads the screen back with PrintWindow,
confirms the text landed in the TUI buffer.
"""
import sys, time, ctypes, win32gui, win32ui, win32con
from PIL import Image
sys.path.insert(0, r'C:\Users\techai\PKA testing\selfconnect-alt')
from self_connect import list_windows, send_string, get_text_uia, capture_window

# Find the Claude Code WT window
wins = [w for w in list_windows() if 'claude' in w.title.lower() and 'windowsterminal' in w.exe_name.lower()]
if not wins:
    print("ERROR: No Claude Code WT window found — open claude in a terminal first")
    sys.exit(1)

target = wins[0]
print(f"[STRESS] Target: hwnd={target.hwnd}  title={target.title!r}")
print(f"[STRESS] Injecting 50 WM_CHAR probes with visual readback verification\n")

hits = 0; misses = 0; t0 = time.monotonic()

for i in range(50):
    marker = f"SC_PROBE_{i:03d}"

    # 1. Inject the marker via PostMessage WM_CHAR (background-safe, no focus steal)
    send_string(target, marker, mode="turbo")
    time.sleep(0.15)

    # 2. Read the TUI buffer via UIA text extraction
    text = get_text_uia(target.hwnd) or ""
    found = marker in text

    # 3. Every 10 probes, capture a PrintWindow screenshot as visual proof
    if i % 10 == 0:
        img = capture_window(target.hwnd)
        if img:
            img.save(fr"C:\Users\techai\PKA testing\selfconnect-alt\probe_{i:03d}.png")
            print(f"  [{i:3d}] marker={marker}  UIA_found={found}  screenshot=probe_{i:03d}.png")
        else:
            print(f"  [{i:3d}] marker={marker}  UIA_found={found}  screenshot=FAILED")
    else:
        print(f"  [{i:3d}] marker={marker}  UIA_found={found}")

    if found: hits += 1
    else: misses += 1

    # Clear the injected text so next probe is clean
    send_string(target, "\x1b", mode="turbo")  # ESC to clear input line
    time.sleep(0.05)

elapsed = time.monotonic() - t0
print(f"\n{'='*60}")
print(f"STRESS RESULTS: {hits}/50 confirmed in TUI buffer")
print(f"Misses: {misses}  Elapsed: {elapsed:.1f}s  Rate: {50/elapsed:.1f} probes/s")
print("PASS" if hits >= 45 else f"DEGRADED: only {hits}/50 confirmed")
