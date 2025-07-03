from __future__ import annotations

import glob
import platform
import subprocess
import sys
from typing import Callable

# ----------------------------  public facade  ---------------------------- #


def is_cam_active() -> tuple[bool, str]:
    """Return webcam activity status for the current OS."""
    return _dispatch(
        windows=_win_cam_active,
        darwin=_mac_cam_active,
        linux=_nix_cam_active,
    )


def _dispatch(**impl: Callable[[], tuple[bool, str]]) -> tuple[bool, str]:
    osname = platform.system().lower()
    if osname.startswith("win"):
        return impl["windows"]()
    if osname == "darwin":
        return impl["darwin"]()
    if osname == "linux":
        return impl["linux"]()
    return (False, "Not supported")


def _safe_run(cmd: list[str]) -> subprocess.CompletedProcess:
    """Run *cmd*; never raise use returncode & output instead."""
    return subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )


if sys.platform.startswith("win"):
    import winreg

    _REG_PATH = r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore"

    def _win_cap_active(cap: str) -> tuple[bool, str]:
        """
        Check CapabilityAccessManager usage counters.
        A value `LastUsedTimeStart` > `LastUsedTimeStop`
        means the capability is in use *right now*.
        """
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, rf"{_REG_PATH}\{cap}"
            ) as root:
                for idx in range(winreg.QueryInfoKey(root)[0]):
                    sub = winreg.EnumKey(root, idx)
                    with winreg.OpenKey(root, sub) as key:
                        if _subkeys_active(key):
                            return (True, sub)
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, rf"{_REG_PATH}\{cap}\NonPackaged"
            ) as root:
                # packaged & non-packaged subkeys live one level deeper
                for idx in range(winreg.QueryInfoKey(root)[0]):
                    sub = winreg.EnumKey(root, idx)
                    with winreg.OpenKey(root, sub) as key:
                        if _subkeys_active(key):
                            return (True, sub)

        except OSError as e:
            print(f"winreg error: {e}")

        return (False, "off")

    def _subkeys_active(hkey) -> bool:
        try:
            start, _ = winreg.QueryValueEx(hkey, "LastUsedTimeStart")
            stop, _ = winreg.QueryValueEx(hkey, "LastUsedTimeStop")
            # both are Windows FILETIME (100-ns since 1601-01-01); 0 means never
            return start > stop
        except FileNotFoundError:
            return False

    def _win_cam_active() -> tuple[bool, str]:
        return _win_cap_active("webcam")


def _mac_cam_active() -> tuple[bool, str]:
    """
    Camera is considered active when either `VDCAssistant`
    *or* `AppleCameraAssistant` helper processes are running.
    """
    try:
        import psutil  # external; tiny
    except ModuleNotFoundError:
        return (False, "off")

    cam_helpers = {"VDCAssistant", "AppleCameraAssistant"}
    for p in psutil.process_iter(["name"]):
        if p.info["name"] in cam_helpers:
            return (True, "Active")
    return (False, "off")


def _nix_cam_active() -> tuple[bool, str]:
    """
    Mark camera active if *any* /dev/video* node has an
    open file handle (requires `fuser` from procps-ng).
    """
    for node in glob.glob("/dev/video*"):
        if _safe_run(["fuser", "-s", node]).returncode == 0:
            return (True, "active")
    return (False, "off")


if __name__ == "__main__":
    print("camera :", is_cam_active())
