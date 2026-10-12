"""Verify Ctrl-C makes the app exit cleanly (no traceback). Throws away the pty afterwards."""
import fcntl
import os
import pty
import select
import struct
import sys
import termios
import time


def main():
    pid, fd = pty.fork()
    if pid == 0:
        env = dict(os.environ, TERM="xterm-256color")
        os.execve(sys.executable, [sys.executable, "-m", "nodecc"], env)

    # Give the child a sane window size (pty defaults to 0x0).
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", 30, 100, 0, 0))

    time.sleep(2.0)
    os.write(fd, b"\x03")  # Ctrl-C

    out = b""
    for _ in range(60):  # read for up to ~6s
        r, _, _ = select.select([fd], [], [], 0.1)
        if not r:
            continue
        try:
            chunk = os.read(fd, 65536)
        except OSError:
            break
        if not chunk:
            break
        out += chunk

    try:
        _, status = os.waitpid(pid, 0)
    except ChildProcessError:
        status = -1

    exited = os.WIFEXITED(status)
    code = os.WEXITSTATUS(status) if exited else -1
    print("exit_code:", code)
    print("has_traceback:", b"Traceback" in out)
    print("rendered_ui:", b"Node Control Center" in out and b"actions" in out)
    if exited and code == 0 and b"Traceback" not in out:
        print("CTRLC_OK")
    else:
        print("CTRLC_FAIL")
        print(out.decode(errors="replace")[-2000:])


if __name__ == "__main__":
    main()
