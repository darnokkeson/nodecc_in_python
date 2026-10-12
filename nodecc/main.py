from __future__ import annotations

import curses
import sys
import threading
from collections.abc import Callable

from .lib import create_vm, list_amis, list_subnets, list_vms, show_vm, terminate_vm

MENU_ITEMS = [
    "list virtual machines",
    "create virtual machine",
    "terminate virtual machine",
]


class App:
    """Holds the UI state and the AWS-backed action for each menu item."""

    def __init__(self) -> None:
        # "menu" plus the sub-views; None signals "quit".
        self.view: str | None = "menu"
        self.menu_index = 0

        # Shared state for the list views (vm_list, ami_list, subnet_list).
        self.list_items = []
        self.list_ids = []
        self.list_index = 0
        self.list_mode = "show"

        # Text for the detail / notice views.
        self.detail_text: str | None = None
        self.notice_text: str | None = None
        self.error: str | None = None

        # State used by the create flow.
        self.ami_ids = []
        self.selected_ami = None

        # Progress + background AWS task state.
        self.progress = 0.0
        self.running = False
        self.task_result: tuple[object, object] | None = None
        self.on_done: Callable[[object, object], None] | None = None

    # ------------------------------------------------------------------ #
    # Background AWS task handling
    # ------------------------------------------------------------------ #
    def start_task(self, func, args, on_done):
        if self.running:
            # A request is already in flight; ignore duplicates so that
            # results and callbacks cannot get crossed.
            return
        self.running = True
        self.progress = 0.0
        self.on_done = on_done
        self.task_result = None

        def worker():
            try:
                result = func(*args)
                self.task_result = (result, None)
            except Exception as exc:  # noqa: BLE001 - surface any AWS error in the UI
                self.task_result = (None, exc)
            self.running = False

        threading.Thread(target=worker, daemon=True).start()

    # ------------------------------------------------------------------ #
    # Actions reachable from the main menu
    # ------------------------------------------------------------------ #
    def select_menu(self, index):
        if index == 0:
            self.list_mode = "show"
            self._load_vm_list()
        elif index == 1:
            self._load_amis()
        elif index == 2:
            self.list_mode = "terminate"
            self._load_vm_list()
        else:
            self.error = "not supported"
            self.view = "error"

    # -- list / terminate virtual machines ---------------------------- #
    def _load_vm_list(self):
        self.start_task(list_vms.list_vms, (), self._vm_list_done)

    def _vm_list_done(self, result, err):
        if err:
            self.error = "listVMs: " + str(err)
            self.view = "error"
        else:
            self.list_items = result
            self.list_ids = result
            self.list_index = 0
            self.view = "vm_list"

    def select_vm(self, index):
        instance_id = self.list_ids[index]
        if self.list_mode == "show":
            self.start_task(show_vm.show_vm, (instance_id,), self._vm_detail_done)
        else:
            self.start_task(
                terminate_vm.terminate_vm, (instance_id,), self._vm_terminated_done
            )

    def _vm_detail_done(self, result, err):
        if err:
            self.error = "showVM: " + str(err)
            self.view = "error"
        else:
            instance = result
            state = instance.get("State", {}).get("Name", "")
            self.detail_text = "\n".join(
                [
                    "InstanceId: " + instance.get("InstanceId", ""),
                    "InstanceType: " + instance.get("InstanceType", ""),
                    "State: " + state,
                    "LaunchTime: " + str(instance.get("LaunchTime", "")),
                    "ImageId: " + instance.get("ImageId", ""),
                    "PublicDnsName: " + instance.get("PublicDnsName", ""),
                ]
            )
            self.view = "vm_detail"

    def _vm_terminated_done(self, result, err):
        if err:
            self.error = "terminateVM: " + str(err)
            self.view = "error"
        else:
            self.notice_text = (
                "terminating ...\n\n"
                "You can always go back with the left arrow key."
            )
            self.view = "notice"

    # -- create virtual machine --------------------------------------- #
    def _load_amis(self):
        self.start_task(list_amis.list_amis, (), self._amis_done)

    def _amis_done(self, result, err):
        if err:
            self.error = "listAMIs: " + str(err)
            self.view = "error"
        else:
            self.ami_ids = result["ami_ids"]
            self.list_items = result["descriptions"]
            self.list_ids = result["ami_ids"]
            self.list_index = 0
            self.view = "ami_list"

    def select_ami(self, index):
        self.selected_ami = self.list_ids[index]
        self.start_task(list_subnets.list_subnets, (), self._subnets_done)

    def _subnets_done(self, result, err):
        if err:
            self.error = "listSubnets: " + str(err)
            self.view = "error"
        else:
            self.list_items = result
            self.list_ids = result
            self.list_index = 0
            self.view = "subnet_list"

    def select_subnet(self, index):
        subnet_id = self.list_ids[index]
        self.start_task(
            create_vm.create_vm, (self.selected_ami, subnet_id), self._vm_created_done
        )

    def _vm_created_done(self, result, err):
        if err:
            self.error = "createVM: " + str(err)
            self.view = "error"
        else:
            self.notice_text = (
                "starting ...\n\n"
                "You can always go back with the left arrow key."
            )
            self.view = "notice"

    # ------------------------------------------------------------------ #
    # Navigation
    # ------------------------------------------------------------------ #
    def go_back(self):
        self.view = "menu"
        self.menu_index = 0
        self.list_index = 0
        self.list_items = []
        self.list_ids = []
        self.detail_text = None
        self.notice_text = None
        self.error = None

    def move(self, delta):
        if self.view == "menu":
            self.menu_index = (self.menu_index + delta) % len(MENU_ITEMS)
        elif self.list_items:
            self.list_index = (self.list_index + delta) % len(self.list_items)

    def confirm(self):
        if self.view == "menu":
            self.select_menu(self.menu_index)
        elif self.view == "vm_list" and self.list_items:
            self.select_vm(self.list_index)
        elif self.view == "ami_list" and self.list_items:
            self.select_ami(self.list_index)
        elif self.view == "subnet_list" and self.list_items:
            self.select_subnet(self.list_index)


# ---------------------------------------------------------------------- #
# Rendering
# ---------------------------------------------------------------------- #
def _add(win, y, x, text, attr=0):
    try:
        win.addstr(y, x, text, attr)
    except curses.error:
        pass


def _draw_items(win, items, index, top=2, title=None):
    h, w = win.getmaxyx()
    if title is not None:
        _add(win, 1, 1, title, curses.A_BOLD)
    last = h - 1
    for idx, item in enumerate(items):
        y = top + idx
        if y < top or y >= last:
            continue
        attr = curses.A_REVERSE if idx == index else 0
        _add(win, y, 2, str(item)[: w - 4], attr)


def _draw_progress(win, fraction):
    h, w = win.getmaxyx()
    fraction = max(0.0, min(1.0, fraction))
    y = h // 2
    # Inside the border: bar at x=2..(1+bar_len), then a gap, then a 4-char
    # percent label ending at x=w-2 (right border at x=w-1 stays intact).
    bar_len = max(0, w - 8)
    filled = int(bar_len * fraction)
    _add(win, 0, 1, "progress", curses.A_BOLD)
    _add(win, y, 2, "#" * filled + "-" * (bar_len - filled))
    if bar_len > 0:
        _add(win, y, 3 + bar_len, f"{int(fraction * 100):3d}%")


def _draw_menu(win, app):
    h, w = win.getmaxyx()
    _add(win, 0, 1, "actions", curses.A_BOLD)
    selected = app.view == "menu"
    last = h - 1
    for idx, item in enumerate(MENU_ITEMS):
        y = 2 + idx
        if y >= last:
            continue
        attr = curses.A_REVERSE if (selected and idx == app.menu_index) else 0
        _add(win, y, 2, item[: w - 4], attr)


def _draw_content(win, app):
    h, w = win.getmaxyx()
    last = h - 1

    def put(text):
        y = 1
        for line in (text or "").split("\n"):
            if y >= last:
                break
            _add(win, y, 1, line[: w - 2])
            y += 1

    if app.view == "menu":
        put(
            "Node Control Center for AWS\n\n"
            "Please select one of the actions from the left and press return.\n\n"
            "You can always go back with the left arrow key.\n\n"
            "You can terminate the application by pressing ESC or q."
        )
    elif app.view in ("vm_list", "ami_list", "subnet_list"):
        title = {
            "vm_list": "Virtual Machines",
            "ami_list": "Amazon Linux 2 AMIs",
            "subnet_list": "Subnets (default VPC)",
        }[app.view]
        _draw_items(win, app.list_items, app.list_index, top=2, title=title)
    elif app.view == "vm_detail":
        put(app.detail_text)
    elif app.view == "notice":
        put(app.notice_text)
    elif app.view == "error":
        put("Error\n\n" + str(app.error))


def draw(stdscr, app):
    h, w = stdscr.getmaxyx()

    left_w = max(10, min(int(w * 0.30), w - 1))
    right_x = left_w
    right_w = max(1, w - left_w)
    prog_h = max(1, int(h * 0.10))
    content_h = max(1, h - prog_h)

    menu_win = curses.newwin(h, left_w, 0, 0)
    menu_win.box()
    _draw_menu(menu_win, app)

    prog_win = curses.newwin(prog_h, right_w, 0, right_x)
    prog_win.box()
    _draw_progress(prog_win, app.progress)

    content_win = curses.newwin(content_h, right_w, prog_h, right_x)
    content_win.box()
    _draw_content(content_win, app)

    # The panels are independent windows (curses.newwin), not subwindows, so
    # each one must refresh itself. Refreshing only stdscr (as before) left
    # all three panels blank.
    menu_win.refresh()
    prog_win.refresh()
    content_win.refresh()


# ---------------------------------------------------------------------- #
# Main loop
# ---------------------------------------------------------------------- #
def _get_key(stdscr, running):
    stdscr.timeout(200 if running else -1)
    ch = stdscr.getch()
    return None if ch == -1 else ch


def run(stdscr):
    curses.curs_set(0)
    app = App()

    while app.view is not None:
        # Animate the progress bar while an AWS call is in flight.
        if app.running and app.progress < 0.75:
            app.progress = min(0.75, app.progress + 0.05)
        draw(stdscr, app)

        ch = _get_key(stdscr, app.running)

        # A background AWS task finished: hand off to its callback.
        if (
            not app.running
            and app.on_done is not None
            and app.task_result is not None
        ):
            result, err = app.task_result
            callback = app.on_done
            app.on_done = None
            app.progress = 1.0
            callback(result, err)
            continue

        if ch is None:
            continue

        if ch in (27, ord("q"), 3):  # ESC, q, Ctrl-C
            app.view = None
        elif ch == curses.KEY_LEFT:
            app.go_back()
        elif ch == curses.KEY_UP:
            app.move(-1)
        elif ch == curses.KEY_DOWN:
            app.move(1)
        elif ch in (10, 13, curses.KEY_ENTER):
            app.confirm()


def main():
    sys.stdout.write("\033]0;Node Control Center for AWS\007")
    sys.stdout.flush()
    try:
        curses.wrapper(run)
    except KeyboardInterrupt:
        # Ctrl-C arrives as SIGINT before getch() can see key code 3; exit
        # cleanly like the original app's C-c handler (process.exit(0)).
        # curses.wrapper restores the terminal in its finally block.
        pass


if __name__ == "__main__":
    main()
