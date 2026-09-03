from __future__ import annotations

import glob
import platform
import subprocess
import sys

# ----------------------------  public facade  ---------------------------- #


def is_cam_active() -> tuple[bool, str]:
    """Return webcam activity status for the current OS."""
    osname = platform.system().lower()
    if osname.startswith("win"):
        return _win_cam_active()
    if osname == "darwin":
        return _mac_cam_active()
    if osname == "linux":
        return _nix_cam_active()
    return (False, "Not supported")


def _safe_run(cmd: list[str]) -> subprocess.CompletedProcess:
    """Run *cmd*; never raise use returncode & output instead."""
    try:
        return subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except FileNotFoundError:
        return subprocess.CompletedProcess(cmd, returncode=1)


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
    open file handle and report the processes using it (requires `fuser`
    from procps-ng).
    """
    try:
        import psutil
    except ModuleNotFoundError:
        psutil = None

    active = False
    users = []
    for node in glob.glob("/dev/video*"):
        result = _safe_run(["fuser", node])
        if result.returncode != 0:
            continue
        active = True

        if psutil is None:
            return (True, "active")

        for pid in result.stdout.split():
            try:
                process = psutil.Process(int(pid))
                name = process.name()
            except (psutil.Error, ValueError):
                continue

            user = f"{name} (pid {pid})" if name else f"pid {pid}"
            if user not in users:
                users.append(user)

    if users:
        return (True, ", ".join(users))
    if active:
        return (True, "active")
    return (False, "off")


if __name__ == "__main__":
    print("camera :", is_cam_active())
