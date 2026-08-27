#!/usr/bin/env python3
"""Minimal TCP service-banner listener for the Mission 1.6 lab.

Usage: sdc-listener <port>

Binds 0.0.0.0:<port> and answers each connection with a fixed banner. Its only
job is to make the port show as *open* so the cadet can fingerprint the node's
role (80=web, 5432=db, 6379=comms, 8080=decoy). Bound to 0.0.0.0 so it keeps
serving through a live IP rotation without a restart.
"""
import socket
import sys

BANNER = b"SDC-SERVICE\r\n"


def main():
    port = int(sys.argv[1])
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", port))
    srv.listen(64)
    while True:
        try:
            conn, _ = srv.accept()
        except OSError:
            continue
        try:
            conn.sendall(BANNER)
        except OSError:
            pass
        finally:
            conn.close()


if __name__ == "__main__":
    main()
