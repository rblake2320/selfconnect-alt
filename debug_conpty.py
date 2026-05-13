import sys, ctypes, ctypes.wintypes as wt, time, re
sys.path.insert(0, '.')
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
from self_connect import _COORD, _STARTUPINFOW, _STARTUPINFOEX, PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE

rin = wt.HANDLE(); win = wt.HANDLE()
rout = wt.HANDLE(); wout = wt.HANDLE()
kernel32.CreatePipe(ctypes.byref(rin), ctypes.byref(win), None, 0)
kernel32.CreatePipe(ctypes.byref(rout), ctypes.byref(wout), None, 0)
print(f'stdin  pipe: read={rin.value}  write={win.value}')
print(f'stdout pipe: read={rout.value} write={wout.value}')

coord = _COORD(80, 25)
hpc = ctypes.c_void_p()
hr = kernel32.CreatePseudoConsole(coord, rin, wout, 0, ctypes.byref(hpc))
print(f'CreatePseudoConsole: hr=0x{hr&0xFFFFFFFF:08X}  hpc={hpc.value}')
kernel32.CloseHandle(rin)
kernel32.CloseHandle(wout)

als = ctypes.c_size_t(0)
kernel32.InitializeProcThreadAttributeList(None, 1, 0, ctypes.byref(als))
ab = ctypes.create_string_buffer(als.value)
al = ctypes.cast(ab, ctypes.c_void_p)
kernel32.InitializeProcThreadAttributeList(al, 1, 0, ctypes.byref(als))
kernel32.UpdateProcThreadAttribute(al, 0, PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE,
                                    hpc, ctypes.sizeof(ctypes.c_void_p), None, None)
si = _STARTUPINFOEX()
si.StartupInfo.cb = ctypes.sizeof(_STARTUPINFOEX)
si.lpAttributeList = al

class PI(ctypes.Structure):
    _fields_ = [('hProcess', wt.HANDLE), ('hThread', wt.HANDLE),
                ('dwProcessId', wt.DWORD), ('dwThreadId', wt.DWORD)]
pi = PI()

flags = 0x00080000 | 0x00000400
cmd = ctypes.create_unicode_buffer('cmd.exe /c echo CONPTY_TEST')
ok = kernel32.CreateProcessW(None, cmd, None, None, False, flags, None, None,
                              ctypes.byref(si), ctypes.byref(pi))
print(f'CreateProcessW: ok={ok}  pid={pi.dwProcessId}  err={ctypes.get_last_error()}')

# Wait for process to exit
wait = kernel32.WaitForSingleObject(pi.hProcess, 5000)
print(f'WaitForSingleObject: {wait} (0=exited, 258=timeout)')
time.sleep(0.3)

# CRITICAL: close ConPTY BEFORE reading final output
# ConPTY holds the write end of the output pipe; closing it flushes and signals EOF
print('Closing ConPTY to flush output...')
kernel32.ClosePseudoConsole(hpc)
time.sleep(0.1)

# Read ALL remaining data (write end is now closed = ReadFile won't block forever)
all_data = b''
while True:
    ba = wt.DWORD(0)
    kernel32.PeekNamedPipe(rout, None, 0, None, ctypes.byref(ba), None)
    if ba.value == 0:
        break
    buf = ctypes.create_string_buffer(ba.value)
    rc = wt.DWORD(0)
    rfok = kernel32.ReadFile(rout, buf, ba.value, ctypes.byref(rc), None)
    if not rfok or rc.value == 0:
        break
    all_data += buf.raw[:rc.value]

print(f'Total bytes: {len(all_data)}')
print(f'Raw: {all_data!r}')
text = all_data.decode('utf-8', errors='replace')
clean = re.sub(r'\x1b\[[0-9;?]*[a-zA-Z]', '', text)
clean = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', clean)
print(f'Text: {clean!r}')
print(f'CONPTY_TEST found: {"CONPTY_TEST" in clean}')

kernel32.CloseHandle(pi.hProcess); kernel32.CloseHandle(pi.hThread)
kernel32.DeleteProcThreadAttributeList(al)
kernel32.CloseHandle(win); kernel32.CloseHandle(rout)
print('Done')
