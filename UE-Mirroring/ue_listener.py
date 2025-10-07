import socket
import select
import signal
import subprocess
import threading
import logging
import os
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

UE_PROCESSES = {}
shutdown_flag = threading.Event()

def start_ue(imsi, config):
    logging.info(f"Starting UE {imsi}: {config}")
    proc = subprocess.Popen(
        ["sudo", "./nr-ue", "-c", config],
        preexec_fn=os.setsid  # start in new process group
    )
    UE_PROCESSES[imsi] = proc

def stop_ue(imsi):
    proc = UE_PROCESSES.get(imsi)
    if not proc:
        logging.warning(f"No UE process found for {imsi}")
        return

    logging.info(f"Stopping UE {imsi} (pid {proc.pid})")
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)  # terminate whole process group
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        logging.warning(f"UE {imsi} did not stop, killing...")
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    finally:
        UE_PROCESSES.pop(imsi, None)

def signal_handler(sig, frame):
    logging.info("Ctrl+C received, shutting down...")
    shutdown_flag.set()

def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(("0.0.0.0", 5000))
    server_socket.listen(5)
    server_socket.setblocking(False)

    logging.info("Listening on 0.0.0.0:5000")

    while not shutdown_flag.is_set():
        r, _, _ = select.select([server_socket], [], [], 1)  # timeout every 1s
        if server_socket in r:
            conn, addr = server_socket.accept()
            with conn:
                data = conn.recv(1024).decode()
                logging.info(f"Received: {data.strip()}")

                if "Registration complete" in data:
                    imsi = data.split("[imsi-")[1].split("]")[0]
                    start_ue(imsi, f"../ueransim_configs/ue_{imsi[-3:]}.yaml")

                elif "Deregistration request" in data:
                    imsi = data.split("[imsi-")[1].split("]")[0]
                    stop_ue(imsi)

    logging.info("Cleaning up...")
    for imsi in list(UE_PROCESSES.keys()):
        stop_ue(imsi)

    server_socket.close()
    logging.info("Shutdown complete.")

if __name__ == "__main__":
    main()
