#!/usr/bin/env python3
import subprocess, shlex, time, select, socket, re, logging

# Config
SSH_USER = "ubuntu"
REMOTE_HOST = "192.168.0.188"
AMF_LOG = "/var/log/open5gs/amf.log"
UPF_LOG = "/var/log/open5gs/upf.log"

# Where to forward
NDT_HOST = "192.168.0.115"
NDT_PORT = 5000

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def run_ssh_tail(logfile):
    ssh_cmd = f"ssh {SSH_USER}@{REMOTE_HOST} tail -F {logfile}"
    proc = subprocess.Popen(
        shlex.split(ssh_cmd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        bufsize=1
    )

    try:
        while True:
            rlist, _, _ = select.select([proc.stdout], [], [], 1)
            if rlist:
                line = proc.stdout.readline()
                if not line:
                    break
                yield line.strip()
    finally:
        proc.terminate()
        proc.wait()

def forward_lines(logfile):
    for line in run_ssh_tail(logfile):
        if "Registration complete" in line or "Deregistration request" in line:
            try:
                sock = socket.create_connection((NDT_HOST, NDT_PORT), timeout=3)
                sock.sendall((line + "\n").encode())
                sock.close()
                logging.info(f"Forwarded: {line}")
            except Exception as e:
                logging.error(f"Failed to forward line: {e}")

def main():
    import threading
    threading.Thread(target=forward_lines, args=(AMF_LOG,), daemon=True).start()
    threading.Thread(target=forward_lines, args=(UPF_LOG,), daemon=True).start()

    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()

