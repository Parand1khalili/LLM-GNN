"""Private, append-only local audit. Raw responses never enter public results."""
import csv
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess

from .inputs import canonical_bytes


class AuditError(ValueError):
    def __init__(self):
        super().__init__("AUDIT_UNAVAILABLE")


def _windows_identity():
    output = subprocess.check_output(["whoami", "/user", "/fo", "csv", "/nh"], text=True)
    return next(csv.reader(output.splitlines()))[1]


def _restrict_windows(path, sid):
    import ctypes as c
    from ctypes import wintypes as w
    adv = c.WinDLL("advapi32", use_last_error=True)
    kernel = c.WinDLL("kernel32", use_last_error=True)
    adv.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [w.LPCWSTR, w.DWORD, c.POINTER(c.c_void_p), c.c_void_p]
    adv.GetSecurityDescriptorDacl.argtypes = [c.c_void_p, c.POINTER(w.BOOL), c.POINTER(c.c_void_p), c.POINTER(w.BOOL)]
    adv.SetNamedSecurityInfoW.argtypes = [w.LPWSTR, w.DWORD, w.DWORD, c.c_void_p, c.c_void_p, c.c_void_p, c.c_void_p]
    kernel.LocalFree.argtypes = [c.c_void_p]
    descriptor, dacl, present, defaulted = c.c_void_p(), c.c_void_p(), w.BOOL(), w.BOOL()
    if not adv.ConvertStringSecurityDescriptorToSecurityDescriptorW(
            f"D:P(A;OICI;FA;;;{sid})", 1, c.byref(descriptor), None):
        raise AuditError()
    try:
        if not adv.GetSecurityDescriptorDacl(descriptor, c.byref(present), c.byref(dacl), c.byref(defaulted)):
            raise AuditError()
        if adv.SetNamedSecurityInfoW(str(path), 1, 0x80000004, None, None, dacl, None) != 0:
            raise AuditError()
    finally:
        kernel.LocalFree(descriptor)


def _private_windows(path, sid):
    # Read the native DACL: allow ACEs for the current SID only.
    import ctypes as c
    from ctypes import wintypes as w
    adv = c.WinDLL("advapi32", use_last_error=True)
    kernel = c.WinDLL("kernel32", use_last_error=True)
    adv.GetNamedSecurityInfoW.argtypes = [w.LPWSTR, w.DWORD, w.DWORD,
        c.c_void_p, c.c_void_p, c.POINTER(c.c_void_p), c.c_void_p, c.POINTER(c.c_void_p)]
    adv.GetAce.argtypes = [c.c_void_p, w.DWORD, c.POINTER(c.c_void_p)]
    adv.ConvertSidToStringSidW.argtypes = [c.c_void_p, c.POINTER(c.c_void_p)]
    kernel.LocalFree.argtypes = [c.c_void_p]
    dacl, descriptor = c.c_void_p(), c.c_void_p()
    if adv.GetNamedSecurityInfoW(str(path), 1, 4, None, None, c.byref(dacl), None,
                                 c.byref(descriptor)) != 0:
        raise AuditError()
    try:
        if not dacl.value: raise AuditError()
        count = c.c_ushort.from_address(dacl.value + 4).value
        if not count: raise AuditError()
        for i in range(count):
            ace, identity = c.c_void_p(), c.c_void_p()
            if not adv.GetAce(dacl, i, c.byref(ace)) or c.c_ubyte.from_address(ace.value).value != 0:
                raise AuditError()
            if not adv.ConvertSidToStringSidW(ace.value + 8, c.byref(identity)):
                raise AuditError()
            try:
                if c.wstring_at(identity.value) != sid: raise AuditError()
            finally:
                kernel.LocalFree(identity)
    finally:
        kernel.LocalFree(descriptor)


class PrivateAudit:
    """Exclusive content-addressed JSON, current-user Windows ACL / POSIX 0700.

    Default path is Git-ignored and outside public exports. Never point a public
    export or artifact backup at this directory. Only canonical decoded responses
    are available offline; this does not claim original provider wire-byte capture.
    """
    def __init__(self, root):
        self.root = Path(root).absolute()
        try:
            for part in (self.root, *self.root.parents):
                if part.is_symlink(): raise AuditError()
            if any(p.casefold() in {"web", "graphscope", "docs", "reports", "prnd-project",
                                   "llmgnn_reference", "mydrive", "my drive"} for p in self.root.parts):
                raise AuditError()
            existed = self.root.exists()
            self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
            self.sid = _windows_identity() if os.name == "nt" else None
            if os.name == "nt":
                if not existed:
                    _restrict_windows(self.root, self.sid)
                _private_windows(self.root, self.sid)
            elif self.root.stat().st_uid != os.getuid() or stat.S_IMODE(self.root.stat().st_mode) != 0o700:
                raise AuditError()
        except (OSError, subprocess.SubprocessError, ValueError, IndexError, StopIteration):
            raise AuditError() from None

    def write(self, record):
        try:
            if self.root.is_symlink(): raise AuditError()
            if os.name == "nt": _private_windows(self.root, self.sid)
            elif stat.S_IMODE(self.root.stat().st_mode) != 0o700: raise AuditError()
            blob = canonical_bytes(record)
            digest = hashlib.sha256(blob).hexdigest()
            path = self.root / (digest + ".json")
            if path.is_symlink(): raise AuditError()
            if path.exists():
                if os.name == "nt": _private_windows(path, self.sid)
                if path.read_bytes() != blob: raise AuditError()
            else:
                descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(blob)
                    stream.flush()
                    os.fsync(stream.fileno())
            if os.name == "nt": _private_windows(path, self.sid)
            elif stat.S_IMODE(path.stat().st_mode) != 0o600: raise AuditError()
            return digest
        except (OSError, subprocess.SubprocessError, ValueError, TypeError, RecursionError):
            raise AuditError() from None

    def read(self, digest):
        if type(digest) is not str or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise AuditError()
        path = self.root / (digest + ".json")
        if self.root.is_symlink() or path.is_symlink(): raise AuditError()
        if os.name == "nt":
            _private_windows(self.root, self.sid)
            _private_windows(path, self.sid)
        elif (stat.S_IMODE(self.root.stat().st_mode) != 0o700
              or stat.S_IMODE(path.stat().st_mode) != 0o600):
            raise AuditError()
        blob = path.read_bytes()
        if hashlib.sha256(blob).hexdigest() != digest: raise AuditError()
        return json.loads(blob)
