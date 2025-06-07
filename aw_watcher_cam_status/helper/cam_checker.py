from __future__ import annotations

import glob
import platform
import subprocess
import sys
from typing import Callable, Optional

# ----------------------------  public facade  ---------------------------- #

def is_cam_active() -> Optional[bool]:
    """Return webcam activity status for the current OS."""
    return _dispatch(
        windows=_win_cam_active,
        darwin=_mac_cam_active,
        linux=_nix_cam_active,
    )

def _dispatch(**impl: Callable[[], Optional[bool]]) -> Optional[bool]:
    osname = platform.system().lower()
    if osname.startswith("win"):
        return impl["windows"]()
    if osname == "darwin":
        return impl["darwin"]()
    if osname == "linux":
        return impl["linux"]()
    return None  # unsupported platform


def _safe_run(cmd: list[str]) -> subprocess.CompletedProcess:
    """Run *cmd*; never raise use returncode & output instead."""
    return subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )


if sys.platform.startswith("win"):
    import ctypes
    import winreg

    _REG_PATH = r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore"

    def _win_cap_active(cap: str) -> Optional[bool]:
        """
        Check CapabilityAccessManager usage counters.
        A value `LastUsedTimeStart` > `LastUsedTimeStop`
        means the capability is in use *right now*.
        """
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, rf"{_REG_PATH}\{cap}") as root:
                if _subkeys_active(root):
                    return True
                # packaged & non-packaged subkeys live one level deeper
                for idx in range(winreg.QueryInfoKey(root)[0]):
                    sub = winreg.EnumKey(root, idx)
                    with winreg.OpenKey(root, sub) as key:
                        if _subkeys_active(key):
                            return True
        except OSError:
            pass
        return False

    def _subkeys_active(hkey) -> bool:
        try:
            start, _ = winreg.QueryValueEx(hkey, "LastUsedTimeStart")
            stop, _ = winreg.QueryValueEx(hkey, "LastUsedTimeStop")
            # both are Windows FILETIME (100-ns since 1601-01-01); 0 means never
            return start > stop
        except FileNotFoundError:
            return False

    def _win_cam_active() -> Optional[bool]:
        return _win_cap_active("webcam")



def _mac_cam_active() -> Optional[bool]:
    """
    Camera is considered active when either `VDCAssistant`
    *or* `AppleCameraAssistant` helper processes are running.
    """
    try:
        import psutil  # external; tiny
    except ModuleNotFoundError:
        return None

    cam_helpers = {"VDCAssistant", "AppleCameraAssistant"}
    for p in psutil.process_iter(["name"]):
        if p.info["name"] in cam_helpers:
            return True
    return False


def _nix_cam_active() -> Optional[bool]:
    """
    Mark camera active if *any* /dev/video* node has an
    open file handle (requires `fuser` from procps-ng).
    """
    for node in glob.glob("/dev/video*"):
        if _safe_run(["fuser", "-s", node]).returncode == 0:
            return True
    return False

if __name__ == "__main__":
    print("camera :", is_cam_active())

