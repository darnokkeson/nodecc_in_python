"""Offline smoke test for the nodecc Python port.

Stubs boto3 so no AWS access is needed, then drives the App state machine
through all three menu flows plus the error path and the in-flight guard.

Run from this directory:  python smoke_test.py
"""
import sys
import time
import types

# --- stub boto3 before importing the app -----------------------------------
boto3_stub = types.ModuleType("boto3")


class FakeEC2:
    def describe_instances(self, **kwargs):
        if "InstanceIds" in kwargs:
            iid = kwargs["InstanceIds"][0]
            return {"Reservations": [{"Instances": [{
                "InstanceId": iid,
                "InstanceType": "t3.micro",
                "State": {"Name": "running"},
                "LaunchTime": "2026-01-01T00:00:00Z",
                "ImageId": "ami-123",
                "PublicDnsName": "ec2.example.com",
            }]}]}
        return {"Reservations": [{"Instances": [
            {"InstanceId": "i-aaaa"},
            {"InstanceId": "i-bbbb"},
        ]}]}

    def describe_images(self, **kwargs):
        return {"Images": [
            {"ImageId": "ami-1", "Description": "AL2 2.0.2023-a"},
            {"ImageId": "ami-2", "Description": "AL2 2.0.2023-b"},
        ]}

    def describe_vpcs(self, **kwargs):
        return {"Vpcs": [{"VpcId": "vpc-1"}]}

    def describe_subnets(self, **kwargs):
        return {"Subnets": [{"SubnetId": "subnet-1"}, {"SubnetId": "subnet-2"}]}

    def run_instances(self, **kwargs):
        return {}

    def terminate_instances(self, **kwargs):
        return {}


def _client(*args, **kwargs):
    return FakeEC2()


boto3_stub.client = _client  # type: ignore[attr-defined]
sys.modules["boto3"] = boto3_stub

# curses may be unavailable in minimal environments; stub it if so.
try:
    import curses  # noqa: F401
except ImportError:
    sys.modules["curses"] = types.ModuleType("curses")

from nodecc.main import App


def complete(app):
    """Wait for the background worker, then do the same hand-off run() does."""
    while app.running:
        time.sleep(0.01)
    assert app.on_done is not None and app.task_result is not None
    result, err = app.task_result
    callback = app.on_done
    app.on_done = None
    app.progress = 1.0
    callback(result, err)


def main():
    app = App()
    assert app.view == "menu"

    # 1. List VMs -> open detail -> back
    app.menu_index = 0
    app.confirm()
    complete(app)
    assert app.view == "vm_list", app.view
    assert app.list_items == ["i-aaaa", "i-bbbb"]
    app.confirm()
    complete(app)
    assert app.view == "vm_detail"
    assert (
        app.detail_text is not None
        and "i-aaaa" in app.detail_text
        and "t3.micro" in app.detail_text
    )
    app.go_back()
    assert app.view == "menu"

    # 2. Create VM: AMI -> subnet -> launch
    app.menu_index = 1
    app.confirm()
    complete(app)
    assert app.view == "ami_list"
    assert app.list_items == ["AL2 2.0.2023-a", "AL2 2.0.2023-b"]
    app.move(1)
    assert app.list_index == 1
    app.confirm()
    complete(app)
    assert app.view == "subnet_list"
    assert app.selected_ami == "ami-2"
    assert app.list_items == ["subnet-1", "subnet-2"]
    app.confirm()
    complete(app)
    assert (
        app.view == "notice"
        and app.notice_text is not None
        and app.notice_text.startswith("starting ...")
    )
    app.go_back()

    # 3. Terminate VM
    app.menu_index = 2
    app.confirm()
    complete(app)
    assert app.view == "vm_list" and app.list_mode == "terminate"
    app.confirm()
    complete(app)
    assert (
        app.view == "notice"
        and app.notice_text is not None
        and app.notice_text.startswith("terminating ...")
    )

    # 4. Error path
    def on_error(result, err):
        app.error = str(err)
        app.view = "error"

    def boom():
        raise RuntimeError("nope")

    app.start_task(boom, (), on_error)
    complete(app)
    assert app.view == "error" and app.error is not None and "nope" in app.error

    # 5. In-flight guard: a second task while one is running is ignored.
    seen = []

    def slow():
        time.sleep(0.05)

    app.start_task(slow, (), lambda r, e: seen.append("first"))
    app.start_task(boom, (), lambda r, e: seen.append("second"))
    complete(app)
    assert seen == ["first"], seen

    # 6. ...and a new task works once the previous one finished.
    app.start_task(slow, (), lambda r, e: seen.append("third"))
    complete(app)
    assert seen == ["first", "third"], seen

    print("SMOKE_TEST_OK")


if __name__ == "__main__":
    main()
