#!/usr/bin/env python3

import sys
import logging
import traceback
from time import sleep
from datetime import datetime, timezone

from aw_core import dirs
from aw_core.models import Event
from aw_client.client import ActivityWatchClient

from .helper.cam_checker import is_cam_active


class StatusLinePrinter:
    _last_msg_length = 0

    def print(self, msg: str) -> None:
        print(" " * self._last_msg_length, end="\r")
        print(msg, end="\r")
        self._last_msg_length = len(msg)


printer = StatusLinePrinter()

watcher_name: str = "aw-watcher-cam-status"

logger = logging.getLogger(watcher_name)
DEFAULT_CONFIG = f"""
[{watcher_name}]
poll_time = 0.5
"""


def load_config():
    from aw_core.config import load_config_toml as _load_config

    return _load_config(watcher_name, DEFAULT_CONFIG)


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    # You can use the config_dir in this function to message the user where the config file is located
    config_dir = dirs.get_config_dir(watcher_name)

    config = load_config()
    poll_time = float(config[watcher_name].get("poll_time", None))
    if poll_time is None:
        print("poll_time is not set in the config file.")
        print(f"You can set it in {config_dir}")
        sys.exit(1)

    # TODO: Fix --testing flag and set testing as appropriate
    aw = ActivityWatchClient(watcher_name, testing=False)
    bucketname = "{}_{}".format(aw.client_name, aw.client_hostname)
    if aw.get_buckets().get(bucketname) is None:
        aw.create_bucket(bucketname, event_type="cam_status_data", queued=True)
    aw.connect()

    # The detector can take longer than the configured poll interval while it
    # queries every video device. Keep matching heartbeats together as a
    # visible interval; a state change still creates a new event because its
    # data differs.
    pulse_time = max(5.0, poll_time + 5.0)

    while True:

        try:
            title = "Cam off"
            state, name = is_cam_active()
            if state:
                title = "Cam on"
            data = {"title": title, "active_name": name}
            printer.print(name)
            event = Event(timestamp=datetime.now(timezone.utc), data=data)
            aw.heartbeat(
                bucketname, event, pulsetime=pulse_time, queued=True
            )
        except Exception as e:
            print("An exception occurred: {}".format(e))
            traceback.print_exc()
        sleep(poll_time)


if __name__ == "__main__":
    main()
