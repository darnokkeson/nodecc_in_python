# Node Control Center for AWS (Python port)

A terminal UI for managing EC2 virtual machines, ported from the original
Node.js application (`../nodecc`, which used `blessed` + `aws-sdk`).

This Python port uses:

- **`curses`** (standard library) for the terminal UI, and
- **`boto3`** for the AWS EC2 calls.

## Features

From the left-hand menu you can:

1. **list virtual machines** — browse pending/running instances, then open an
   instance to see its details.
2. **create virtual machine** — pick an Amazon Linux 2 AMI, then a subnet in
   your default VPC, and launch a `t3.micro` with the `ec2-ssm-core` profile.
3. **terminate virtual machine** — browse running instances and terminate one.

Controls:

- `up` / `down` — move the selection
- `return` — confirm the selection
- `left` — go back to the main menu
- `esc`, `q` or `ctrl-c` — quit

## Install

### Virtual environment (recommended)

Use a virtual environment to keep dependencies isolated and to avoid the
`externally-managed-environment` error you can hit when installing Python
packages system-wide (this is particularly useful on Ubuntu).

If you haven't created the environment yet, run these commands from your
project directory:

```sh
sudo apt install python3-venv
python3 -m venv venv
source venv/bin/activate
```

You can then install packages inside the environment:

```sh
pip install -r requirements.txt
```

To deactivate the environment when you're finished:

```sh
deactivate
```

### Install without a virtual environment

```sh
pip install -r requirements.txt
```

`boto3` is the only third-party dependency; the UI is built on the standard
library `curses` module.

Requires Python 3.8+. `curses` ships with the standard library on Linux and
Windows; on macOS 3.11+ prefer Homebrew's Python, since the python.org
installers no longer include `curses`.

## AWS configuration

The app targets the `us-east-1` region and reads credentials from the standard
AWS locations (environment variables, `~/.aws/credentials`, and — via
`AWS_SDK_LOAD_CONFIG=1` — `~/.aws/config`). It does not hard-code any
credentials. Make sure the configured identity has permission for the EC2
actions used (`describeInstances`, `describeImages`, `describeVpcs`,
`describeSubnets`, `runInstances`, `terminateInstances`).

## Run

From this directory (`nodecc-python`) — make sure the virtual environment is
activated first if you used one:

```sh
source venv/bin/activate   # only if you set up a virtual environment
python3 -m nodecc
```

NOTE! Click 'enter' if you dont see anything after launching an app in terminal.

## Quick offline check

No AWS account needed — stubs boto3 and drives the whole menu flow
(list, create, terminate, errors) through the state machine:

```sh
python3 smoke_test.py
```
# nodecc_in_python
