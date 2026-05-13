# Runbook: Deep Win32 Optimization — selfconnect-alt Build and Test Process

## What
Complete procedure to implement, test, and verify all 8 deep Win32 optimizations in selfconnect-alt. Covers CacheRequest UIA (8-10x faster get_ui_tree), WriteConsoleInput (fixes Codex stdin), ConPTY own-pipe spawn, dxcam DXGI capture, SharedMemIPC (~1.9us latency), SendInput batching, ReadConsoleOutput, and UIA push events. Produces 170 passing unit tests + 39/39 real Win32 integration checks.

## Prerequisites
- Python 3.12+
- dxcam>=0.0.5  (pip install dxcam)
- pywin32  (pip install pywin32)
- comtypes>=1.4.0  (pip install comtypes)
- pywinauto>=0.6.8  (pip install pywinauto)
- Pillow>=10.0.0  (pip install Pillow)
- psutil>=5.9.0  (pip install psutil)
- Windows 10 build 17763+ for ConPTY (CreatePseudoConsole API)

## Steps
1. Clone selfconnect as selfconnect-alt:  git clone https://github.com/rblake2320/selfconnect.git selfconnect-alt && cd selfconnect-alt && git remote rename origin upstream && git remote add origin https://github.com/rblake2320/selfconnect-alt.git
2. Rename package: in pyproject.toml change name="selfconnect" -> "selfconnect-alt" and version to "0.10.0-alt". Add dxcam>=0.0.5 to optional deps.
3. UIA CacheRequest: import comtypes.gen.UIAutomationClient as _uia_gen. Use CreateObject(clsid, interface=_uia_gen.IUIAutomation) — NOT bare CreateObject which returns IUnknown. Call CreateCacheRequest(), add properties (Name, ControlType, AutomationId, BoundingRectangle), call ElementFromHandleBuildCache(). Wrap in try/except — fall back to original walker on any COM failure.
4. WriteConsoleInput stale handle fix: after FreeConsole()/AttachConsole(pid), GetStdHandle(STD_INPUT_HANDLE) returns the OLD handle (error 6). Fix: use CreateFileW("CONIN$", GENERIC_READ|GENERIC_WRITE, FILE_SHARE_READ_WRITE, None, OPEN_EXISTING, 0, None) to open the ACTUAL attached console input. CloseHandle when done. Same pattern for CONOUT$.
5. ReadConsoleOutput: same CONOUT$ pattern. After AttachConsole(pid): h = CreateFileW("CONOUT$", ...). Call GetConsoleScreenBufferInfo(h, &csbi) to get window region, then ReadConsoleOutputW(h, buf, size, coord, &region). Only works on conhost-backed windows — WT/ConPTY windows do NOT populate the legacy screen buffer.
6. spawn_agent_conpty: CreatePipe x2 (stdin pair + stdout pair). CreatePseudoConsole(coord, h_pipe_in_read, h_pipe_out_write, 0, &hpc). Close h_pipe_in_read and h_pipe_out_write (ConPTY owns them). InitializeProcThreadAttributeList + UpdateProcThreadAttribute(PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE). CreateProcessW with EXTENDED_STARTUPINFO_PRESENT|CREATE_UNICODE_ENVIRONMENT — DO NOT add CREATE_NO_WINDOW or DETACH_PROCESS, those prevent the child from attaching to the ConPTY.
7. ConPTYHandle.flush_read(): call ClosePseudoConsole(hpc) FIRST — this flushes the ConPTY output buffer to h_pipe_out_read. Then drain with PeekNamedPipe loop. NOTE: close() closes h_pipe_out_read before ConPTY — so flush_read() must be called before close() when you need to read final output.
8. SharedMemChannel: use Python mmap(tagname=name) for named shared memory. CreateEvent/SetEvent/WaitForSingleObject for send/recv notification. Header = [4-byte payload_len]. send() writes header+payload then SetEvent(). recv() WaitForSingleObject(timeout) then reads header+payload. Measure with 50-trial median — expect ~1.9 microseconds.
9. dxcam capture: in capture_window(), try dxcam.create() and camera.grab(region=window_rect) first. Fall back to PrintWindow on failure. dxcam works on GPU-composited windows (Chrome, Edge, Electron) where PrintWindow returns a black image.
10. importlib SDK loading fix: when loading self_connect.py via importlib.util.spec_from_file_location(), register sys.modules[name] = mod BEFORE spec.loader.exec_module(mod). Without this, @dataclass fails with AttributeError: NoneType has no attribute __dict__ because dataclasses.py cannot resolve the module.
11. Run unit tests and assert green: python -m pytest tests/ -q --ignore=tests/test_antigravity_controller.py. Expected: 170 passed, 0 failed, 3 warnings. Any failure = do not proceed.
12. Run real integration test (no mocks): python real_integration_test.py. Expected: PASSED=39 FAILED=0. This hits live Win32 APIs — requires a running WT window + Chrome window on screen. Tests: list_windows, get_ui_tree CacheRequest speedup (8-10x), dxcam capture, WriteConsoleInput on standalone conhost, SharedMemIPC roundtrip, ConPTY spawn+flush_read, _read_console_output on standalone conhost, UIA node structure.
13. Run head-to-head benchmark: python bench_compare.py. Check bench_results.csv. Key targets: get_ui_tree speedup > 2x, capture_window speedup >= 1.0x, IPC latency < 5 microseconds.
14. Commit and push: git add self_connect.py pyproject.toml bench_compare.py real_integration_test.py tests/test_cache_request.py tests/test_conpty.py tests/test_console_io.py tests/test_new_features.py && git commit -m "feat: selfconnect-alt vX.X.X" && git push -u origin master

## Known Failures
- WriteConsoleInputW returns error 6 (ERROR_INVALID_HANDLE): caused by calling GetStdHandle(STD_INPUT_HANDLE) after AttachConsole — it returns the stale pre-attach handle. Fix: CreateFileW("CONIN$") after AttachConsole.
- ConPTY pipe empty / CREATE_NO_WINDOW: adding CREATE_NO_WINDOW to CreateProcessW flags prevents cmd.exe from connecting to the ConPTY — output goes nowhere. Fix: remove the flag entirely. The ConPTY IS the no-window mechanism.
- UIA CacheRequest returns None silently: comtypes.client.CreateObject(clsid) without interface= returns IUnknown which has no CreateCacheRequest method. Exception is swallowed. Fix: CreateObject(clsid, interface=_uia_gen.IUIAutomation).
- @dataclass AttributeError NoneType.__dict__ when loading via importlib: the module is not in sys.modules before exec_module so dataclasses cannot find the class module. Fix: sys.modules[name] = mod before exec_module().
- _read_console_output returns empty on WT/ConPTY windows: WT uses a VT-rendered screen, not the legacy console screen buffer. ReadConsoleOutputW returns blank rows. Fix: test against CREATE_NEW_CONSOLE conhost windows only.
- ConPTY read returns 0 bytes when running nested inside WT: text output from child ConPTY routes to parent WT session, not to the pipe. VT housekeeping sequences DO arrive on the pipe. Fix: use flush_read() with file-redirect to prove the command ran (cmd.exe /c echo X > file.txt).
- ruff E402 on imports added mid-file: move all imports to top of file or use # noqa: E402.
- ruff RUF012 on ctypes.Union _fields_: add # noqa: RUF012 to _fields_ class variable lines in Union subclasses.

## Verified
- 2026-05-13, session 17
