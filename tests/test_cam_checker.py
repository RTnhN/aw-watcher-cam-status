import subprocess
import unittest
from unittest.mock import Mock, call, patch

from aw_watcher_cam_status.helper import cam_checker


class LinuxCameraCheckerTests(unittest.TestCase):
    @patch.object(cam_checker.glob, "glob", return_value=["/dev/video0", "/dev/video1"])
    @patch.object(cam_checker, "_safe_run")
    @patch("psutil.Process")
    def test_reports_processes_using_active_camera(
        self, process, safe_run, glob
    ):
        safe_run.side_effect = [
            subprocess.CompletedProcess(["fuser", "/dev/video0"], 0, "123 456"),
            subprocess.CompletedProcess(["fuser", "/dev/video1"], 0, "456"),
        ]
        firefox = Mock()
        firefox.name.return_value = "firefox"
        zoom = Mock()
        zoom.name.return_value = "zoom"
        process.side_effect = [firefox, zoom, zoom]

        self.assertEqual(
            cam_checker._nix_cam_active(),
            (True, "firefox (pid 123), zoom (pid 456)"),
        )
        self.assertEqual(
            safe_run.call_args_list,
            [
                call(["fuser", "/dev/video0"]),
                call(["fuser", "/dev/video1"]),
            ],
        )

    @patch.object(cam_checker.glob, "glob", return_value=["/dev/video0"])
    @patch.object(cam_checker, "_safe_run")
    def test_returns_off_when_fuser_finds_no_camera_user(self, safe_run, glob):
        safe_run.return_value = subprocess.CompletedProcess(
            ["fuser", "/dev/video0"], 1, ""
        )

        self.assertEqual(cam_checker._nix_cam_active(), (False, "off"))


if __name__ == "__main__":
    unittest.main()
