# SelfConnect Alt — Deep Win32 Optimization Fork

`selfconnect-alt` is a performance-focused fork of the [SelfConnect core SDK](https://github.com/rblake2320/selfconnect). It preserves the full core API while layering eight Win32 optimizations for high-throughput, low-latency, and screen-intensive agent workloads.

**When to use `alt` instead of `core`:**
- You need capture rates above ~5 fps (DXGI replaces GDI)
- You're injecting into ConPTY and need guaranteed delivery (WriteConsoleInput)
- You're passing large data between agents on the same machine (SharedMemIPC)
- You're managing a 3+ agent swarm and UIA polling is a bottleneck (push events)

---

## What Alt Adds Over Core

| Optimization | API | What it fixes |
|---|---|---|
| **UIA CacheRequest** | `get_uia_cache(hwnd)` | Replaces per-property UIA round-trips with a single batched read. ~4× faster for window enumeration in large swarms. |
| **WriteConsoleInput** | `write_console_input(hwnd, text)` | Directly writes INPUT_RECORDs to the ConPTY input queue. More reliable than WM_CHAR for high-speed injection; bypasses the message queue entirely. |
| **ConPTY own-pipe** | `open_conpty_pipe(pid)` | Opens a direct read/write handle to a ConPTY process's pseudo-terminal pipe. Enables streaming I/O without screen capture. |
| **DXGI screen capture** | `capture_dxgi(hwnd)` | GPU-accelerated frame grab via `dxcam`. Replaces `PrintWindow`/`BitBlt` for GPU-composited targets (terminals, Electron, Chrome). 10–60 fps sustained. |
| **SharedMemIPC** | `SharedMemChannel(name)` | Zero-copy shared memory channel between agents on the same host. Eliminates PostMessage overhead for large payloads (>1 KB). |
| **SendInput batching** | `send_keys_batch(hwnd, keys)` | Batches multiple `SendInput` calls into one system call. Reduces per-keystroke overhead for foreground-window injection. |
| **ReadConsoleOutput** | `read_console_output(hwnd)` | Reads the ConPTY screen buffer directly as a character grid. More reliable than PrintWindow + OCR for terminal text extraction. |
| **UIA push events** | `subscribe_uia_events(hwnd, cb)` | Registers a UIA event handler instead of polling. Eliminates polling loops; callback fires on text change, focus, or value change. |

---

## Installation

```bash
pip install selfconnect-alt                    # core optimizations
pip install selfconnect-alt[dxgi]              # + dxcam (GPU capture)
pip install selfconnect-alt[ipc]               # + SharedMemIPC
pip install selfconnect-alt[full]              # everything
```

Requires: Python 3.10+, Windows 10/11, `pywin32`, `comtypes`

---

## API Compatibility

`selfconnect-alt` is a drop-in superset of the core SDK. All core exports work unchanged:

```python
from self_connect import list_windows, send_string, save_capture  # core API — unchanged
from self_connect_alt import capture_dxgi, SharedMemChannel        # alt additions
```

---

## Performance Comparison

| Operation | core | alt | Notes |
|---|---|---|---|
| Window enumeration (50 windows) | ~120ms | ~30ms | UIA CacheRequest |
| Screen capture (1080p terminal) | ~40ms | ~4ms | DXGI vs PrintWindow |
| Inject 100 chars | ~2.1s | ~0.9s | WriteConsoleInput vs WM_CHAR |
| Read terminal text | ~25ms (OCR) | ~3ms | ReadConsoleOutput vs image |
| Agent-to-agent 10 KB payload | ~18ms | ~0.4ms | SharedMemIPC vs PostMessage |

---

## Tests

```bash
python -m pytest tests/ -v                  # 170 unit tests (no Win32 needed)
python -m pytest tests/integration/ -v     # 39 Win32 integration checks (live desktop)
```

---

## When to Stay on Core

- You need the simplest possible dependency surface
- Your workload is single-agent or low-frequency
- You're targeting non-Windows platforms (use `SelfConnect-Mac` for macOS)
- You don't need capture rates above ~5 fps

---

## Relationship to the Ecosystem

```
core/       ← base SDK (use for most cases)
alt/        ← this repo — performance fork of core
enterprise/ ← governance/policy layer (works with both core and alt)
agent-wire/ ← dispatch gateway (sits above core or alt)
```

See [selfconnect-ecosystem](https://github.com/rblake2320/selfconnect-ecosystem) for the full picture.
