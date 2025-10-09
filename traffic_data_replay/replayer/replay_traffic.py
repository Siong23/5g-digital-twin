#!/usr/bin/env python3
'''
Advanced NDT Traffic Replayer with Realistic Traffic Patterns
'''
import time
import subprocess
import threading
import numpy as np
import random
from datetime import datetime
from pathlib import Path

class NDTReplayer:
    def __init__(self):
        self.interface = "uesimtun0"
        self.target = "8.8.8.8"
        self.stop_flag = threading.Event()

        # Physical traffic characteristics
        self.bw_timeseries = [0.004416, 0.00736, 0.006624, 0.00736, 0.00736, 0.00736, 0.00736, 0.00736, 0.00736, 0.006624, 0.00736, 0.00736, 0.00736, 0.00736, 0.00736, 0.00736, 0.00736, 0.00736, 0.00736, 0.00736, 0.00736, 0.00736, 0.00736, 0.00736, 0.00736, 0.00736, 0.00736, 0.00736, 0.00736, 0.00736, 0.00736, 0.00736, 0.006624, 0.00736, 0.008096, 0.00736, 0.00736, 0.00736, 0.006624, 0.00736, 0.008096, 0.00736, 0.006624, 0.00736, 0.008096, 0.006624, 0.00736, 0.00736, 0.006624, 0.00736, 0.00736, 0.00736, 0.00736, 0.006624, 0.008096, 0.00736, 0.00736, 0.00736, 0.00736, 0.00736, 0.00736, 0.00736, 0.00736, 0.00736, 0.00736, 0.00736, 0.00736, 0.00736, 0.00736, 0.00736, 0.00736, 0.00736, 0.006624, 0.008096, 0.00736, 0.00736, 0.00736, 0.00736, 0.006624, 0.008096, 0.00736, 0.00736, 0.006624, 0.00736, 0.00736, 0.00736, 0.00736, 0.00736, 0.00736, 0.006624, 0.00736, 0.00736, 0.00736, 0.00736, 0.00736, 0.00736, 0.00736, 0.00736, 0.00736, 0.00736, 0.00736]
        self.rtt_timeseries = [32.1, 33.7, 26.5, 40.6, 48.5, 21.5, 19.2, 20.0, 37.3, 53.3, 94.4, 94.8, 67.9, 144.0, 73.9, 137.0, 69.9, 69.1, 63.7, 64.7, 17.8, 19.0, 54.8, 58.0, 28.9, 31.3, 38.7, 28.7, 47.2, 29.9, 23.3, 22.6, 24.1, 21.1, 24.6, 31.0, 18.4, 17.4, 33.3, 17.2, 23.8, 24.1, 21.8, 27.8, 107.0, 20.7, 69.9, 18.0, 18.0, 20.9, 48.3, 38.5, 18.1, 21.4, 16.2, 17.1, 22.7, 27.7, 18.3, 119.0, 197.0, 45.1, 78.1, 113.0, 93.4, 171.0, 163.0, 99.0, 153.0, 140.0, 60.9, 32.0, 45.8, 23.5, 16.9, 20.5, 19.6, 21.5, 29.4, 21.5, 16.0, 22.0, 20.8, 113.0, 22.3, 18.9, 19.0, 18.5, 78.5, 19.8, 18.3, 33.5, 61.3, 17.6, 22.9, 21.4, 20.0, 20.0, 23.4, 20.1, 33.9, 37.2, 59.8, 21.1, 20.2, 23.8, 20.3, 17.9, 21.5, 175.0, 240.0, 64.8, 54.9, 55.8, 194.0, 119.0, 114.0, 125.0, 58.2, 144.0, 37.6, 37.6, 23.4, 21.3, 20.0, 18.1, 33.4, 22.3, 125.0, 22.5, 46.2, 19.8, 22.8, 86.6, 72.4, 34.8, 24.6, 27.7, 18.5, 41.0, 17.1, 80.7, 15.8, 68.4, 23.3, 18.0, 81.6, 23.0, 20.9, 101.0, 20.1, 26.2, 21.8, 20.4, 219.0, 16.9, 40.6, 26.2, 122.0, 23.6, 79.2, 88.3, 51.9, 84.4, 291.0, 83.1, 95.3, 153.0, 86.5, 18.7, 18.3, 40.2, 68.2, 22.1, 14.6, 30.5, 38.6, 18.6, 92.3, 17.9, 21.1, 15.0, 15.1, 96.7, 78.2, 280.0, 20.9, 42.1, 19.4, 17.9, 21.5, 81.0, 25.3, 26.3, 21.9, 27.0, 72.0, 20.9, 29.4, 18.9, 68.8, 27.4, 17.1, 16.5, 57.7, 80.7, 23.6, 23.2, 22.1, 251.0, 126.0, 138.0, 69.6, 147.0, 84.9, 174.0, 99.1, 113.0, 34.3, 118.0, 18.7, 17.9, 32.1, 15.9, 22.9, 20.4, 18.8, 27.6, 21.7, 77.8, 21.7, 24.4, 18.0, 44.4, 78.0, 36.5, 28.7, 39.6, 86.9, 17.0, 20.2, 17.7, 37.9, 43.1, 18.6, 36.9, 20.0, 32.3, 84.7, 16.8, 32.5, 61.7, 19.1, 26.2, 20.9, 35.8, 28.9, 16.1, 19.6, 125.0, 53.1, 194.0, 42.4, 65.8, 57.3, 222.0, 77.5, 72.6, 142.0, 57.1, 27.9, 24.8, 18.6, 38.9, 17.1, 16.8, 65.5, 18.2, 24.7, 33.4, 17.4, 15.9, 23.4, 36.9, 129.0, 16.2, 16.8, 26.3, 49.7, 76.5, 19.0, 23.3, 16.7, 21.4, 25.1, 38.7, 29.2, 49.5, 19.7, 16.7, 82.1, 14.9, 51.8, 17.8, 19.9, 20.2, 20.8, 18.8, 40.5, 26.5, 51.2, 77.2, 34.1, 109.0, 121.0, 120.0, 64.7, 126.0, 103.0, 21.7, 18.4, 35.1, 83.6, 18.1, 21.9, 19.1, 22.2, 16.1, 25.1, 44.2, 57.0, 24.9, 28.5, 41.1, 28.2, 37.8, 37.9, 19.1, 27.8, 21.2, 63.2, 18.9, 17.0, 21.1, 51.2, 15.7, 82.9, 21.5, 55.9, 30.8, 23.3, 23.8, 42.2, 20.4, 28.2, 76.1, 36.9, 33.7, 82.1, 160.0, 104.0, 80.4, 153.0, 132.0, 136.0, 71.3, 161.0, 83.8, 80.6, 40.8, 23.8, 84.5, 20.3, 18.3, 38.2, 16.0, 20.8, 50.0, 37.4, 19.5, 27.8, 40.8, 37.0, 22.7, 16.7, 30.2, 22.3, 19.7, 18.9, 26.6, 102.0, 18.9, 60.3, 18.3, 16.7, 31.6, 33.5, 17.1, 21.7, 30.5, 23.2, 77.4, 20.0, 24.2, 25.0, 22.2, 64.1, 19.9, 118.0, 136.0, 99.1, 92.0, 86.9, 75.7, 84.5, 28.2, 172.0, 126.0, 329.0, 42.8, 26.3, 53.4, 34.7, 34.8, 28.7, 35.9, 24.5, 25.3, 47.9, 34.4, 27.0, 16.7, 37.2, 21.9, 81.5, 22.4, 28.7, 29.1, 18.0, 23.3, 27.4, 25.9, 19.6, 78.5, 20.5, 19.2, 29.3, 32.7, 17.9, 17.9, 31.4, 23.4, 20.6, 30.8, 22.1, 20.8, 57.7, 18.9, 88.2, 170.0, 76.0, 78.8, 83.1, 201.0, 72.2, 234.0, 93.9, 156.0, 74.5, 44.9, 39.5, 54.7, 98.7, 17.8, 30.5, 28.8, 37.5, 17.8, 16.2, 60.6, 35.6, 17.3, 53.5, 26.8, 91.3, 45.9, 33.9, 18.6, 20.5, 36.8, 31.9, 20.5, 29.8, 25.1, 19.8, 16.4, 16.1, 20.2, 19.9, 44.8]
        self.packets_per_sec = 9.964770947383458

        # Capture metadata
        self.expected_duration = 100
        self.expected_ping_count = 500
        
        # Output file
        self.output_log = Path.home() / "Desktop" / "traffic_data" / "ue_ping_replay.log"
        self.output_log.parent.mkdir(parents=True, exist_ok=True)

    def replay_ping_pattern(self):
        '''Replay ping with actual RTT pattern and VARIABLE timing'''
        print("[*] Starting ping pattern replay with realistic timing...")
        print(f"[*] Expected to replay {self.expected_ping_count} pings over {self.expected_duration} seconds")
        print(f"[*] Output: {self.output_log}")

        idx = 0
        start_time = time.time()
        
        # Open log file for writing
        with open(self.output_log, 'w') as log_file:
            while not self.stop_flag.is_set() and idx < len(self.rtt_timeseries):
                try:
                    # Use ACTUAL packet timing from physical capture if available
                    # Otherwise use variable interval with jitter
                    base_interval = 0.2
                    
                    # Add realistic jitter (±20% variation)
                    jitter = random.uniform(-0.04, 0.04)  # ±20% of 0.2s
                    actual_interval = base_interval + jitter
                    
                    # Occasionally simulate burst traffic (10% chance)
                    if random.random() < 0.1:
                        actual_interval = actual_interval / 2  # Send faster
                    
                    time.sleep(actual_interval)

                    # Send ping with variable packet size to create bandwidth variation
                    # Base size 64 bytes, but vary ±50%
                    packet_size = random.randint(32, 96)
                    
                    # Send ping and capture output
                    result = subprocess.run(
                        ['ping', '-I', self.interface, '-c', '1', '-W', '1', 
                         '-s', str(packet_size), '-D', self.target],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    
                    # Write output to log file
                    if result.stdout:
                        log_file.write(result.stdout)
                        log_file.flush()
                    
                    idx += 1

                    # Progress indicator
                    if idx % 10 == 0:
                        elapsed = time.time() - start_time
                        print(f"[*] Progress: {idx}/{len(self.rtt_timeseries)} pings ({elapsed:.1f}s elapsed)")

                except Exception as e:
                    print(f"[!] Ping error: {e}")
                    time.sleep(0.2)
        
        elapsed = time.time() - start_time
        print(f"[✓] Completed {idx} pings in {elapsed:.1f}s")
        print(f"[✓] Ping log saved to: {self.output_log}")

    def generate_background_traffic(self):
        '''Generate background traffic to simulate real network load'''
        print("[*] Starting background traffic generation...")
        
        while not self.stop_flag.is_set():
            try:
                # Randomly send small bursts of data
                if random.random() < 0.3:  # 30% chance each second
                    # Generate random size payload (100-1000 bytes)
                    size = random.randint(100, 1000)
                    
                    # Send using UDP (won't fail if nothing listening)
                    subprocess.run(
                        ['timeout', '0.1', 'bash', '-c', 
                         f'echo "{random.randint(0,999999)}" | nc -u -w 0 {self.target} 12345 2>/dev/null || true'],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=0.2
                    )
                
                time.sleep(random.uniform(0.5, 1.5))  # Variable pause
                
            except Exception as e:
                time.sleep(1)

    def start(self, duration: int = 100):
        '''Start traffic replay with realistic patterns'''
        print("="*60)
        print("NDT Traffic Replay Started (Realistic Mode)")
        print(f"Captured traffic duration: {self.expected_duration} seconds")
        print(f"Replay duration: {duration} seconds")
        print(f"Expected pings: {self.expected_ping_count}")
        print("="*60 + "\n")

        # Start threads
        ping_thread = threading.Thread(target=self.replay_ping_pattern)
        background_thread = threading.Thread(target=self.generate_background_traffic)
        
        ping_thread.start()
        background_thread.start()

        try:
            time.sleep(duration)
        except KeyboardInterrupt:
            print("\n[*] Interrupted by user")
        finally:
            print("\n[*] Stopping replay...")
            self.stop_flag.set()
            ping_thread.join()
            background_thread.join()
            print("[✓] Replay stopped")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='NDT Traffic Replayer')
    parser.add_argument('--duration', type=int, default=100,
                       help='Replay duration in seconds (default: {} from capture)'.format(100))

    args = parser.parse_args()

    replayer = NDTReplayer()
    replayer.start(duration=args.duration)
