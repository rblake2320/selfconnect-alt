"""
bench_compare.py — SelfConnect vs SelfConnect-Alt head-to-head benchmark

Usage:
    python bench_compare.py [--hwnd HWND] [--out bench_results.csv] [--trials 10]

If --hwnd is not given, auto-selects a Windows Terminal window.
Runs each benchmark --trials times and reports median latency.

Output: bench_results.csv with columns:
    operation, original_ms, alt_ms, speedup_factor, notes
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import logging
import statistics
import sys
import time
from pathlib import Path

logging.getLogger("dxcam").setLevel(logging.ERROR)  # suppress "instance already exists" noise

# ── Load both SDKs without module name collision ───────────────────────────────

ORIG_PATH = Path(r"C:\Users\techai\PKA testing\selfconnect\self_connect.py")
ALT_PATH  = Path(r"C:\Users\techai\PKA testing\selfconnect-alt\self_connect.py")


def _load_sdk(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod  = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod   # register BEFORE exec so @dataclass can resolve __module__
    spec.loader.exec_module(mod)
    return mod

print("Loading SDKs...", flush=True)
sc_orig = _load_sdk(ORIG_PATH, "sc_orig")
sc_alt  = _load_sdk(ALT_PATH,  "sc_alt")
print(f"  Original: v{sc_orig.__version__}", flush=True)
print(f"  Alt:      v{sc_alt.__version__}",  flush=True)

# ── Benchmark helpers ─────────────────────────────────────────────────────────

PAYLOAD_500 = "A" * 500   # 500-char string for injection benchmarks


def _time_median(fn, trials: int) -> float:
    """Run fn() `trials` times, return median elapsed ms."""
    times = []
    for _ in range(trials):
        t0 = time.perf_counter()
        try:
            fn()
        except Exception:
            pass
        times.append((time.perf_counter() - t0) * 1000.0)
    return round(statistics.median(times), 2)


def _fmt_speedup(orig_ms: float, alt_ms: float) -> str:
    if alt_ms <= 0:
        return "N/A"
    ratio = orig_ms / alt_ms
    return f"{ratio:.1f}x"


# ── Individual benchmarks ─────────────────────────────────────────────────────

def bench_send_string(target_orig, target_alt, trials: int) -> dict:
    """PostMessage WM_CHAR (orig) vs WriteConsoleInput (alt)."""
    orig_ms = _time_median(
        lambda: sc_orig.send_string(target_orig, PAYLOAD_500, mode="turbo"),
        trials
    )
    alt_ms = _time_median(
        lambda: sc_alt.send_string(target_alt, PAYLOAD_500, mode="console"),
        trials
    )
    return {
        "operation":      "send_string (500 chars)",
        "original_ms":    orig_ms,
        "alt_ms":         alt_ms,
        "speedup_factor": _fmt_speedup(orig_ms, alt_ms),
        "notes":          "orig=PostMessage WM_CHAR, alt=WriteConsoleInput",
    }


def bench_get_ui_tree(hwnd: int, trials: int) -> dict:
    """Per-element COM calls (orig) vs CacheRequest (alt)."""
    orig_ms = _time_median(
        lambda: sc_orig.get_ui_tree(hwnd, max_depth=5),
        trials
    )
    alt_ms = _time_median(
        lambda: sc_alt.get_ui_tree(hwnd, max_depth=5),
        trials
    )
    return {
        "operation":      "get_ui_tree (depth=5)",
        "original_ms":    orig_ms,
        "alt_ms":         alt_ms,
        "speedup_factor": _fmt_speedup(orig_ms, alt_ms),
        "notes":          "orig=per-element COM, alt=CacheRequest single-call",
    }


def bench_capture_window(hwnd: int, trials: int) -> dict:
    """PrintWindow (orig) vs dxcam DXGI (alt)."""
    orig_ms = _time_median(
        lambda: sc_orig.capture_window(hwnd),
        trials
    )
    alt_ms = _time_median(
        lambda: sc_alt.capture_window(hwnd),
        trials
    )
    return {
        "operation":      "capture_window",
        "original_ms":    orig_ms,
        "alt_ms":         alt_ms,
        "speedup_factor": _fmt_speedup(orig_ms, alt_ms),
        "notes":          "orig=PrintWindow, alt=dxcam DXGI",
    }


def bench_get_text(hwnd_orig, hwnd_alt, trials: int) -> dict:
    """UIA text extraction (orig) vs ReadConsoleOutput (alt)."""
    orig_ms = _time_median(
        lambda: sc_orig.get_text_uia(hwnd_orig),
        trials
    )
    alt_ms = _time_median(
        lambda: sc_alt.get_text_uia(hwnd_alt),
        trials
    )
    return {
        "operation":      "get_text_uia",
        "original_ms":    orig_ms,
        "alt_ms":         alt_ms,
        "speedup_factor": _fmt_speedup(orig_ms, alt_ms),
        "notes":          "orig=UIA walker, alt=ReadConsoleOutput",
    }


def bench_submit_claude(hwnd: int, trials: int) -> dict:
    """WM_CHAR 0x000D (orig) vs WriteConsoleInput VK_RETURN (alt)."""
    orig_ms = _time_median(
        lambda: sc_orig.submit_claude_input(hwnd),
        trials
    )
    alt_ms = _time_median(
        lambda: sc_alt.submit_claude_input(hwnd),
        trials
    )
    return {
        "operation":      "submit_claude_input",
        "original_ms":    orig_ms,
        "alt_ms":         alt_ms,
        "speedup_factor": _fmt_speedup(orig_ms, alt_ms),
        "notes":          "orig=WM_CHAR 0x000D, alt=WriteConsoleInput VK_RETURN",
    }


def bench_shared_mem_vs_http(trials: int) -> dict:
    """SharedMemChannel roundtrip vs simulated HTTP (measured via mmap timing)."""
    try:
        ch_w = sc_alt.SharedMemChannel("BenchChannel_SC_Alt_001", size=65536)
        ch_r = sc_alt.SharedMemChannel("BenchChannel_SC_Alt_001", size=65536)

        def roundtrip():
            ch_w.send(b"benchmark payload " + b"x" * 500)
            ch_r.recv(timeout=0.5)

        alt_ms = _time_median(roundtrip, trials)
        ch_w.close()
        ch_r.close()
    except Exception:
        alt_ms = -1.0

    return {
        "operation":      "IPC roundtrip (shared memory)",
        "original_ms":    -1.0,  # HTTP hub not easily benchmarked in isolation
        "alt_ms":         alt_ms,
        "speedup_factor": "N/A (no orig equivalent)",
        "notes":          "alt=SharedMemChannel mmap+event; orig uses HTTP hub_relay",
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="SelfConnect vs SelfConnect-Alt benchmark")
    parser.add_argument("--hwnd",   type=int,   default=None,                 help="Target window HWND")
    parser.add_argument("--out",    type=str,   default="bench_results.csv",  help="Output CSV path")
    parser.add_argument("--trials", type=int,   default=10,                   help="Trials per benchmark")
    args = parser.parse_args()

    # Find or use specified window
    if args.hwnd:
        wins_orig = [w for w in sc_orig.list_windows() if w.hwnd == args.hwnd]
        wins_alt  = [w for w in sc_alt.list_windows()  if w.hwnd == args.hwnd]
        if not wins_orig or not wins_alt:
            print(f"ERROR: hwnd={args.hwnd} not found", file=sys.stderr)
            sys.exit(1)
        target_orig = wins_orig[0]
        target_alt  = wins_alt[0]
    else:
        # Auto-select: prefer a Windows Terminal window, not the current terminal
        own_pid = sc_orig.get_own_terminal_pid()
        candidates = [
            w for w in sc_orig.list_windows()
            if "windowsterminal" in w.exe_name.lower()
            and w.pid != own_pid
        ]
        if not candidates:
            # Fall back to any terminal-ish window
            candidates = [
                w for w in sc_orig.list_windows()
                if any(x in w.title.lower() for x in ("cmd", "powershell", "terminal"))
                and w.pid != own_pid
            ]
        if not candidates:
            print("WARNING: No suitable target window found — some benchmarks will show ~0ms", flush=True)
            print("  Open a Windows Terminal window and re-run, or use --hwnd to specify one.", flush=True)
            # Use hwnd=0 — most operations will fail gracefully and return quickly
            class _FakeTarget:
                hwnd = 0
                pid  = 0
                title = "fake"
                exe_name = ""
            target_orig = _FakeTarget()
            target_alt  = _FakeTarget()
        else:
            target_orig = candidates[0]
            # Find same hwnd in alt's list_windows
            alt_wins = [w for w in sc_alt.list_windows() if w.hwnd == target_orig.hwnd]
            target_alt = alt_wins[0] if alt_wins else target_orig
            print(f"Auto-selected target: hwnd={target_orig.hwnd}  title={target_orig.title!r}", flush=True)

    hwnd = target_orig.hwnd
    print(f"Running {args.trials} trials per benchmark...", flush=True)
    print()

    results = []

    print("1/6  send_string (500 chars)...", flush=True)
    results.append(bench_send_string(target_orig, target_alt, args.trials))
    print(f"     orig={results[-1]['original_ms']}ms  alt={results[-1]['alt_ms']}ms  {results[-1]['speedup_factor']}")

    print("2/6  get_ui_tree (depth=5)...", flush=True)
    results.append(bench_get_ui_tree(hwnd, args.trials))
    print(f"     orig={results[-1]['original_ms']}ms  alt={results[-1]['alt_ms']}ms  {results[-1]['speedup_factor']}")

    print("3/6  capture_window...", flush=True)
    results.append(bench_capture_window(hwnd, args.trials))
    print(f"     orig={results[-1]['original_ms']}ms  alt={results[-1]['alt_ms']}ms  {results[-1]['speedup_factor']}")

    print("4/6  get_text_uia...", flush=True)
    results.append(bench_get_text(hwnd, hwnd, args.trials))
    print(f"     orig={results[-1]['original_ms']}ms  alt={results[-1]['alt_ms']}ms  {results[-1]['speedup_factor']}")

    print("5/6  submit_claude_input...", flush=True)
    results.append(bench_submit_claude(hwnd, args.trials))
    print(f"     orig={results[-1]['original_ms']}ms  alt={results[-1]['alt_ms']}ms  {results[-1]['speedup_factor']}")

    print("6/6  shared memory IPC roundtrip...", flush=True)
    results.append(bench_shared_mem_vs_http(args.trials))
    print(f"     alt={results[-1]['alt_ms']}ms  (no orig equivalent)")

    # Write CSV
    out_path = Path(args.out)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["operation", "original_ms", "alt_ms", "speedup_factor", "notes"])
        w.writeheader()
        w.writerows(results)

    print()
    print("=" * 65)
    print(f"  Results written to: {out_path}")
    print()
    print(f"  {'Operation':<30}  {'Orig':>8}  {'Alt':>8}  {'Speedup':>8}")
    print(f"  {'-'*30}  {'-'*8}  {'-'*8}  {'-'*8}")
    for r in results:
        orig = f"{r['original_ms']:.1f}ms" if r['original_ms'] >= 0 else "N/A"
        alt  = f"{r['alt_ms']:.1f}ms"      if r['alt_ms']      >= 0 else "N/A"
        print(f"  {r['operation']:<30}  {orig:>8}  {alt:>8}  {r['speedup_factor']:>8}")
    print("=" * 65)


if __name__ == "__main__":
    main()
