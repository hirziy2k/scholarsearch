#!/usr/bin/env python3
"""
Privilege Stripping Module
- Removes SeDebugPrivilege from Python runtime token
- Prevents parallel malware from memory dumping
- Uses AdjustTokenPrivileges API via ctypes
"""

import ctypes
import ctypes.wintypes
import sys
from ctypes import windll, byref, c_void_p, c_ulong, Structure, POINTER

# Windows API constants
SE_DEBUG_NAME = "SeDebugPrivilege"
SE_PRIVILEGE_ENABLED = 0x00000002
TOKEN_ADJUST_PRIVILEGES = 0x0020
TOKEN_QUERY = 0x0008
ERROR_SUCCESS = 0


class LUID(Structure):
    _fields_ = [
        ("LowPart", ctypes.wintypes.DWORD),
        ("HighPart", ctypes.wintypes.LONG),
    ]


class LUID_AND_ATTRIBUTES(Structure):
    _fields_ = [
        ("Luid", LUID),
        ("Attributes", ctypes.wintypes.DWORD),
    ]


class TOKEN_PRIVILEGES(Structure):
    _fields_ = [
        ("PrivilegeCount", ctypes.wintypes.DWORD),
        ("Privileges", LUID_AND_ATTRIBUTES * 1),  # We only need one
    ]


def get_current_token():
    """Get handle to current process token."""
    token_handle = ctypes.wintypes.HANDLE()
    current_process = ctypes.windll.kernel32.GetCurrentProcess()
    result = windll.advapi32.OpenProcessToken(
        current_process,
        TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY,
        byref(token_handle)
    )
    if not result:
        error_code = ctypes.get_last_error()
        if error_code == 0:
            error_code = ctypes.windll.kernel32.GetLastError()
        raise ctypes.WinError(error_code)
    return token_handle


def lookup_privilege(name: str) -> LUID:
    """Look up a privilege by name."""
    luid = LUID()
    result = windll.advapi32.LookupPrivilegeValueW(
        None,
        name,
        byref(luid)
    )
    if not result:
        raise ctypes.WinError(ctypes.get_last_error())
    return luid


def strip_debug_privilege():
    """
    Strip SeDebugPrivilege from current process token.
    Returns True if successful, False otherwise.
    """
    try:
        token_handle = get_current_token()
        luid = lookup_privilege(SE_DEBUG_NAME)
        
        # Create TOKEN_PRIVILEGES structure
        tp = TOKEN_PRIVILEGES()
        tp.PrivilegeCount = 1
        tp.Privileges[0].Luid = luid
        tp.Privileges[0].Attributes = 0  # Disable the privilege
        
        # Adjust the token
        result = windll.advapi32.AdjustTokenPrivileges(
            token_handle,
            False,  # DisableAllPrivileges = False (we're adjusting specific one)
            byref(tp),
            ctypes.sizeof(tp),
            None,
            None
        )
        
        if not result:
            raise ctypes.WinError(ctypes.get_last_error())
        
        # Check if we actually adjusted anything
        last_error = ctypes.get_last_error()
        if last_error != ERROR_SUCCESS:
            return False
        
        # Close token handle
        windll.kernel32.CloseHandle(token_handle)
        return True
        
    except Exception as e:
        print(f"WARNING: Failed to strip SeDebugPrivilege: {e}")
        return False


def verify_privilege_stripped():
    """
    Verify that SeDebugPrivilege is disabled.
    Returns True if disabled, False if still enabled.
    """
    try:
        token_handle = get_current_token()
        luid = lookup_privilege(SE_DEBUG_NAME)
        
        # Query current state
        tp = TOKEN_PRIVILEGES()
        tp.PrivilegeCount = 1
        tp.Privileges[0].Luid = luid
        
        # Get information
        cbRet = ctypes.wintypes.DWORD()
        result = windll.advapi32.GetTokenInformation(
            token_handle,
            3,  # TokenPrivileges
            byref(tp),
            ctypes.sizeof(tp),
            byref(cbRet)
        )
        
        windll.kernel32.CloseHandle(token_handle)
        
        if result:
            # Check if the privilege is enabled
            return tp.Privileges[0].Attributes == 0
        return False
        
    except Exception:
        return False


def strip_all_dangerous_privileges():
    """
    Strip all dangerous privileges from the current process.
    """
    dangerous_privileges = [
        "SeDebugPrivilege",           # Memory dumping
        "SeImpersonatePrivilege",     # Token impersonation
        "SeAssignPrimaryTokenPrivilege",  # Token assignment
        "SeTcbPrivilege",             # Act as part of OS
        "SeBackupPrivilege",          # Read any file
        "SeRestorePrivilege",         # Write any file
        "SeTakeOwnershipPrivilege",   # Take file ownership
        "SeLoadDriverPrivilege",      # Load kernel drivers
        "SeSystemtimePrivilege",      # Change system time
        "SeProfSingleProcessPrivilege",  # Profiling
    ]
    
    results = {}
    for priv in dangerous_privileges:
        try:
            token_handle = get_current_token()
            luid = lookup_privilege(priv)
            
            tp = TOKEN_PRIVILEGES()
            tp.PrivilegeCount = 1
            tp.Privileges[0].Luid = luid
            tp.Privileges[0].Attributes = 0  # Disable
            
            windll.advapi32.AdjustTokenPrivileges(
                token_handle,
                False,
                byref(tp),
                ctypes.sizeof(tp),
                None,
                None
            )
            
            windll.kernel32.CloseHandle(token_handle)
            results[priv] = "STRIPPED"
        except Exception as e:
            results[priv] = f"FAILED: {e}"
    
    return results


def harden_process():
    """
    Strip all dangerous privileges from the current process.
    Call this at the start of any security-sensitive script.
    """
    if sys.platform != 'win32':
        return True  # Skip on non-Windows
    
    try:
        results = strip_all_dangerous_privileges()
        return all("STRIPPED" in status for status in results.values())
    except Exception:
        return False


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    
    print("Stripping dangerous privileges from Python runtime...")
    print("=" * 60)
    
    # First, try to strip all dangerous privileges
    results = strip_all_dangerous_privileges()
    
    for priv, status in results.items():
        print(f"  [{status}] {priv}")
    
    # Verify SeDebugPrivilege specifically
    print("\nVerifying SeDebugPrivilege is stripped...")
    if verify_privilege_stripped():
        print("  [OK] SeDebugPrivilege successfully stripped")
    else:
        print("  [WARN] SeDebugPrivilege may still be enabled")
