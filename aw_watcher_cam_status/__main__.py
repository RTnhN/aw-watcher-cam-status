import sys
import os

path = os.path.dirname(sys.modules[__name__].__file__)
path = os.path.join(path, "..")
sys.path.insert(0, path)

import aw_watcher_cam_status

aw_watcher_cam_status.main()
