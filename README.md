aw-watcher-cam-status
==================

This is a watcher that checks if a webcam is active or not. It does not save images or videos. This can be great to check if you had a meeting during a period of time.

This watcher is currently in a early stage of development, please submit PRs if you find bugs! It has been smoke-tested on Linux and Windows. Please let me know if you have tested it on other OS's such as macOS.


## Usage

### Step 1: Install package

Create the environment and install the project:

```sh
uv sync
```

First run (generates config):
```sh
uv run aw-watcher-cam-status
```

### Step 2: Enter config

The only thing that you might need to change is the poll time. This is the time that the checking loop will run.


### Step 3: Restart the server and enable the watcher

Don't forget to add it to the aw-qt.toml file so that it gets started automatically when AW starts.