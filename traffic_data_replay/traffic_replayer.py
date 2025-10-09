#!/usr/bin/env python3
"""
Traffic Pattern Replay for NDT (Network Digital Twin)
Replays physical network traffic patterns onto NDT simulation
"""
import argparse
import json
import subprocess
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd


class TrafficReplayer:
    """Replays traffic patterns from physical network onto NDT"""

    def __init__(self, physical_data_dir: Path, config_file: Path = None):
        self.physical_dir = physical_data_dir
        self.config = self.load_config(config_file) if config_file else {}
        self.stop_flag = threading.Event()

    def load_config(self, config_file: Path) -> dict:
        """Load replay configuration"""
        with open(config_file) as f:
            return json.load(f)

    def analyze_physical_traffic(self):
        """Analyze physical traffic to extract patterns"""
        print("[*] Analyzing physical traffic patterns...")

        # Load physical data
        core_csv = self.physical_dir / "core_traffic.csv"
        gnb_csv = self.physical_dir / "gnb_gtp.csv"
        ping_log = self.physical_dir / "ue_ping.log"

        analysis = {
            "core": self._analyze_bandwidth(core_csv),
            "gnb": self._analyze_bandwidth(gnb_csv),
            "ping": self._analyze_ping(ping_log),
        }

        # Save analysis
        output_file = self.physical_dir / "traffic_analysis.json"
        with open(output_file, "w") as f:
            json.dump(analysis, f, indent=2, default=str)

        print(f"[✓] Analysis saved to {output_file}")
        return analysis

    def _analyze_bandwidth(self, csv_file: Path) -> dict:
        """Extract bandwidth characteristics"""
        if not csv_file.exists():
            return {}

        df = pd.read_csv(
            csv_file,
            sep="\t",
            names=["time", "src", "dst", "teid", "len"],
            usecols=["time", "len"],
        )

        # Convert to bandwidth (Mbps)
        df["time"] = pd.to_datetime(df["time"], errors="coerce", utc=True)
        df = df.dropna(subset=["time"])

        if df.empty:
            return {}

        df_bw = df.set_index("time").resample("1s")["len"].sum() * 8 / 1e6

        # Calculate ACTUAL duration from timestamps
        if len(df) > 0:
            start_time = df["time"].min()
            end_time = df["time"].max()
            actual_duration = (end_time - start_time).total_seconds()
        else:
            actual_duration = len(df_bw)

        return {
            "duration_sec": int(actual_duration),  # Use actual time span, not row count
            "mean_mbps": float(df_bw.mean()),
            "max_mbps": float(df_bw.max()),
            "min_mbps": float(df_bw.min()),
            "std_mbps": float(df_bw.std()),
            "percentile_50": float(df_bw.quantile(0.5)),
            "percentile_95": float(df_bw.quantile(0.95)),
            "percentile_99": float(df_bw.quantile(0.99)),
            "total_packets": len(df),
            "packets_per_sec": len(df) / actual_duration if actual_duration > 0 else 0,
            "timeseries": df_bw.tolist(),
        }

    def _analyze_ping(self, log_file: Path) -> dict:
        """Extract ping characteristics"""
        if not log_file.exists():
            return {}

        rtts = []
        timestamps = []

        with open(log_file) as f:
            for line in f:
                if "time=" in line:
                    try:
                        rtt = float([x for x in line.split() if "time=" in x][0].split("=")[1])
                        rtts.append(rtt)

                        # Try to extract timestamp if available (from -D flag)
                        if "[" in line and "]" in line:
                            ts_str = line.split("[")[1].split("]")[0]
                            try:
                                timestamps.append(float(ts_str))
                            except:
                                pass
                    except:
                        pass

        if not rtts:
            return {}

        rtts_array = np.array(rtts)
        jitter = np.abs(np.diff(rtts_array))

        # Calculate actual duration from timestamps or count
        if len(timestamps) > 1:
            actual_duration = timestamps[-1] - timestamps[0]
        else:
            # Fallback: estimate from count (assuming 0.2s interval from command)
            actual_duration = len(rtts) * 0.2

        return {
            "count": len(rtts),
            "duration_sec": int(actual_duration),  # Actua duration, not just count)
            "mean_rtt_ms": float(rtts_array.mean()),
            "max_rtt_ms": float(rtts_array.max()),
            "min_rtt_ms": float(rtts_array.min()),
            "std_rtt_ms": float(rtts_array.std()),
            "mean_jitter_ms": float(jitter.mean()) if len(jitter) > 0 else 0,
            "max_jitter_ms": float(jitter.max()) if len(jitter) > 0 else 0,
            "packet_loss_rate": 0,  # TODO: extract from ping output
            "timeseries": rtts,
        }

    def generate_replay_script(self, analysis: dict, output_file: Path):
    	"""Generate bash script to replay traffic on NDT"""

    	# Get ping parameters
    	ping_count = analysis['ping'].get('count', 100)
    	packets_per_sec = analysis['core'].get('packets_per_sec', 5)
    	mean_interval = 1.0 / packets_per_sec if packets_per_sec > 0 else 0.2

    	script = f"""#!/bin/bash
# Auto-generated NDT Traffic Replay Script
# Based on physical network capture from {self.physical_dir}
# Generated: {datetime.now()}
# Auto-generated NDT Traffic Replay Script
# Based on physical network capture from {self.physical_dir}
# Generated: {datetime.now()}

set -e

# Configuration
UE_INTERFACE="uesimtun0"
TARGET_IP="8.8.8.8"
TEST_DURATION={analysis['core'].get('duration_sec', 300)}
PING_COUNT={ping_count}
OUTPUT_LOG="$HOME/Desktop/traffic_data/ue_ping_replay.log"

echo "========================================="
echo "NDT Traffic Replay"
echo "Duration: ${{TEST_DURATION}} seconds"
echo "Ping count: ${{PING_COUNT}}"
echo "Output: ${{OUTPUT_LOG}}"
echo "========================================="

# Create output directory
mkdir -p "$(dirname "${{OUTPUT_LOG}}")"

# Function to generate ping traffic matching physical pattern
replay_ping() {{
    local mean_rtt={analysis['ping'].get('mean_rtt_ms', 20)}
    local mean_interval={mean_interval}
    
    echo "[*] Starting ping replay (interval: ${{mean_interval}}s, count: ${{PING_COUNT}})"
    ping -I ${{UE_INTERFACE}} ${{TARGET_IP}} -i ${{mean_interval}} -s 64 -D -c ${{PING_COUNT}} > "${{OUTPUT_LOG}}" &
    PING_PID=$!
    echo "[✓] Ping started (PID: ${{PING_PID}}) → ${{OUTPUT_LOG}}"
}}

# Function to generate traffic matching bandwidth pattern
replay_bandwidth() {{
    local mean_bw={analysis['core'].get('mean_mbps', 1)}
    local max_bw={analysis['core'].get('max_mbps', 5)}
    
    echo "[*] Starting bandwidth replay (mean: ${{mean_bw}} Mbps, max: ${{max_bw}} Mbps)"
    
    # Use iperf3 or curl to generate traffic
    # This is a placeholder - adjust based on available tools
    while true; do
        # Generate burst traffic
        dd if=/dev/zero bs=1M count=1 2>/dev/null | nc -w 1 ${{TARGET_IP}} 1234 || true
        sleep 0.1
    done &
    BW_PID=$!
    echo "[✓] Bandwidth generator started (PID: ${{BW_PID}})"
}}

# Cleanup function
cleanup() {{
    echo ""
    echo "[*] Stopping replay..."
    kill ${{PING_PID}} 2>/dev/null || true
    kill ${{BW_PID}} 2>/dev/null || true
    echo "[✓] Replay stopped"
}}
trap cleanup EXIT INT TERM

# Start replay
replay_ping
#replay_bandwidth  # Uncomment if needed

# Run for specified duration
echo "[*] Running replay for ${{TEST_DURATION}} seconds..."
sleep ${{TEST_DURATION}}

echo "[✓] Replay complete"
echo "[✓] Ping log saved to: ${{OUTPUT_LOG}}"
"""
    
    	with open(output_file, "w") as f:
        	f.write(script)
    
    	# Make executable
    	output_file.chmod(0o755)
    	print(f"[✓] Replay script generated: {output_file}")

    def generate_python_replayer(self, analysis: dict, output_file: Path):
        """Generate advanced Python-based traffic replayer"""

        # Determine the actual replay duration from all sources
        core_duration = analysis.get("core", {}).get("duration_sec", 0)
        gnb_duration = analysis.get("gnb", {}).get("duration_sec", 0)
        ping_duration = analysis.get("ping", {}).get("duration_sec", 0)

        # Use the maximum duration from all sources (they should match if captured simultaneously.
        # But default to core if available
        if core_duration > 0:
            replay_duration = core_duration
        elif gnb_duration > 0:
            replay_duration = gnb_duration
        elif ping_duration > 0:
            replay_duration = ping_duration
        else:
            replay_duration = 300  # Fallback default

        # Log duration information
        print(f"[INFO] Detected durations - Core: {core_duration}s, gNB: {gnb_duration}s, Ping: {ping_duration}s")
        print(f"[INFO] Using replay duration: {replay_duration}s")
        
        script = f"""#!/usr/bin/env python3
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
        self.bw_timeseries = {analysis['core'].get('timeseries', [])}
        self.rtt_timeseries = {analysis['ping'].get('timeseries', [])}
        self.packets_per_sec = {analysis['core'].get('packets_per_sec', 5)}

        # Capture metadata
        self.expected_duration = {replay_duration}
        self.expected_ping_count = {analysis['ping'].get('count', 0)}
        
        # Output file
        self.output_log = Path.home() / "Desktop" / "traffic_data" / "ue_ping_replay.log"
        self.output_log.parent.mkdir(parents=True, exist_ok=True)

    def replay_ping_pattern(self):
        '''Replay ping with actual RTT pattern and VARIABLE timing'''
        print("[*] Starting ping pattern replay with realistic timing...")
        print(f"[*] Expected to replay {{self.expected_ping_count}} pings over {{self.expected_duration}} seconds")
        print(f"[*] Output: {{self.output_log}}")

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
                        print(f"[*] Progress: {{idx}}/{{len(self.rtt_timeseries)}} pings ({{elapsed:.1f}}s elapsed)")

                except Exception as e:
                    print(f"[!] Ping error: {{e}}")
                    time.sleep(0.2)
        
        elapsed = time.time() - start_time
        print(f"[✓] Completed {{idx}} pings in {{elapsed:.1f}}s")
        print(f"[✓] Ping log saved to: {{self.output_log}}")

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
                         f'echo "{{random.randint(0,999999)}}" | nc -u -w 0 {{self.target}} 12345 2>/dev/null || true'],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=0.2
                    )
                
                time.sleep(random.uniform(0.5, 1.5))  # Variable pause
                
            except Exception as e:
                time.sleep(1)

    def start(self, duration: int = {replay_duration}):
        '''Start traffic replay with realistic patterns'''
        print("="*60)
        print("NDT Traffic Replay Started (Realistic Mode)")
        print(f"Captured traffic duration: {{self.expected_duration}} seconds")
        print(f"Replay duration: {{duration}} seconds")
        print(f"Expected pings: {{self.expected_ping_count}}")
        print("="*60 + "\\n")

        # Start threads
        ping_thread = threading.Thread(target=self.replay_ping_pattern)
        background_thread = threading.Thread(target=self.generate_background_traffic)
        
        ping_thread.start()
        background_thread.start()

        try:
            time.sleep(duration)
        except KeyboardInterrupt:
            print("\\n[*] Interrupted by user")
        finally:
            print("\\n[*] Stopping replay...")
            self.stop_flag.set()
            ping_thread.join()
            background_thread.join()
            print("[✓] Replay stopped")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='NDT Traffic Replayer')
    parser.add_argument('--duration', type=int, default={replay_duration},
                       help='Replay duration in seconds (default: {{}} from capture)'.format({replay_duration}))

    args = parser.parse_args()

    replayer = NDTReplayer()
    replayer.start(duration=args.duration)
"""


        with open(output_file, "w") as f:
            f.write(script)

        output_file.chmod(0o755)
        print(f"[✓] Python replayer generated: {output_file}")

    def create_attack_injection_template(self, output_file: Path):
        """Create template for attack injection during replay"""
        template = """#!/usr/bin/env python3
'''
Attack Injection Module for NDT
Inject various attacks during traffic replay
'''
import time
import subprocess
import random
from enum import Enum

class AttackType(Enum):
    DOS_FLOOD = "dos_flood"
    PACKET_DROP = "packet_drop"
    DELAY_INJECTION = "delay_injection"
    BANDWIDTH_EXHAUSTION = "bandwidth_exhaustion"
    MAN_IN_MIDDLE = "mitm"
    SIGNALING_STORM = "signaling_storm"

class AttackInjector:
    def __init__(self, interface: str = "uesimtun0"):
        self.interface = interface
        self.attack_active = False

    def inject_dos_flood(self, target: str, duration: int = 10, rate: int = 1000):
        '''
        Inject DoS flood attack
        Args:
            target: Target IP
            duration: Attack duration in seconds
            rate: Packets per second
        '''
        print(f"[ATTACK] DoS Flood: {rate} pps for {duration}s")

        # Using hping3 (install: sudo apt install hping3)
        cmd = [
            'sudo', 'hping3',
            '-I', self.interface,
            '-S',  # SYN flood
            '--flood',
            '--rand-source',
            target
        ]

        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(duration)
        proc.terminate()
        print("[ATTACK] DoS Flood stopped")

    def inject_packet_drop(self, drop_rate: float = 0.1, duration: int = 10):
        '''
        Inject packet drop using tc (traffic control)
        Args:
            drop_rate: Percentage of packets to drop (0.0-1.0)
            duration: Duration in seconds
        '''
        print(f"[ATTACK] Packet Drop: {drop_rate*100}% for {duration}s")

        # Add packet loss
        subprocess.run([
            'sudo', 'tc', 'qdisc', 'add', 'dev', self.interface,
            'root', 'netem', 'loss', f'{drop_rate*100}%'
        ])

        time.sleep(duration)

        # Remove packet loss
        subprocess.run([
            'sudo', 'tc', 'qdisc', 'del', 'dev', self.interface, 'root'
        ])
        print("[ATTACK] Packet Drop stopped")

    def inject_delay(self, delay_ms: int = 100, jitter_ms: int = 50, duration: int = 10):
        '''
        Inject network delay/latency
        Args:
            delay_ms: Base delay in milliseconds
            jitter_ms: Jitter variation in milliseconds
            duration: Duration in seconds
        '''
        print(f"[ATTACK] Delay Injection: {delay_ms}ms ±{jitter_ms}ms for {duration}s")

        subprocess.run([
            'sudo', 'tc', 'qdisc', 'add', 'dev', self.interface,
            'root', 'netem', 'delay', f'{delay_ms}ms', f'{jitter_ms}ms'
        ])

        time.sleep(duration)

        subprocess.run([
            'sudo', 'tc', 'qdisc', 'del', 'dev', self.interface, 'root'
        ])
        print("[ATTACK] Delay Injection stopped")

    def inject_bandwidth_limit(self, limit_mbps: float = 1.0, duration: int = 10):
        '''
        Limit bandwidth to simulate exhaustion
        Args:
            limit_mbps: Bandwidth limit in Mbps
            duration: Duration in seconds
        '''
        print(f"[ATTACK] Bandwidth Limit: {limit_mbps} Mbps for {duration}s")

        limit_kbps = int(limit_mbps * 1000)

        subprocess.run([
            'sudo', 'tc', 'qdisc', 'add', 'dev', self.interface,
            'root', 'tbf', 'rate', f'{limit_kbps}kbit',
            'burst', '32kbit', 'latency', '400ms'
        ])

        time.sleep(duration)

        subprocess.run([
            'sudo', 'tc', 'qdisc', 'del', 'dev', self.interface, 'root'
        ])
        print("[ATTACK] Bandwidth Limit removed")

    def inject_signaling_storm(self, target: str, duration: int = 10):
        '''
        Inject signaling storm (rapid connection attempts)
        Args:
            target: Target IP
            duration: Duration in seconds
        '''
        print(f"[ATTACK] Signaling Storm for {duration}s")

        start_time = time.time()
        while time.time() - start_time < duration:
            # Rapid connection attempts
            subprocess.run(
                ['ping', '-I', self.interface, '-c', '1', '-W', '1', target],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

        print("[ATTACK] Signaling Storm stopped")

    def run_attack_scenario(self, scenario: str = "mixed"):
        '''
        Run predefined attack scenario
        '''
        print(f"\\n{'='*50}")
        print(f"Running Attack Scenario: {scenario}")
        print(f"{'='*50}\\n")

        if scenario == "mild":
            # Mild attack: slight delay and packet loss
            time.sleep(30)  # Wait 30s for baseline
            self.inject_packet_drop(drop_rate=0.05, duration=20)
            time.sleep(30)
            self.inject_delay(delay_ms=50, jitter_ms=20, duration=20)

        elif scenario == "moderate":
            # Moderate attack: noticeable impact
            time.sleep(20)
            self.inject_packet_drop(drop_rate=0.15, duration=30)
            time.sleep(20)
            self.inject_bandwidth_limit(limit_mbps=2.0, duration=30)
            time.sleep(20)
            self.inject_delay(delay_ms=150, jitter_ms=50, duration=30)

        elif scenario == "severe":
            # Severe attack: significant disruption
            time.sleep(15)
            self.inject_dos_flood(target="8.8.8.8", duration=20, rate=1000)
            time.sleep(10)
            self.inject_packet_drop(drop_rate=0.30, duration=25)
            time.sleep(10)
            self.inject_bandwidth_limit(limit_mbps=0.5, duration=25)

        elif scenario == "mixed":
            # Mixed attacks with random timing
            attacks = [
                lambda: self.inject_packet_drop(0.10, 15),
                lambda: self.inject_delay(100, 30, 15),
                lambda: self.inject_bandwidth_limit(1.5, 15),
            ]

            for _ in range(3):
                time.sleep(random.randint(20, 40))
                attack = random.choice(attacks)
                attack()

        print(f"\\n{'='*50}")
        print("Attack Scenario Complete")
        print(f"{'='*50}\\n")

# Example usage
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='NDT Attack Injector')
    parser.add_argument(
        '--scenario', choices=['mild', 'moderate', 'severe', 'mixed'],
        default='mild', help='Attack scenario'
    )
    parser.add_argument('--interface', default='uesimtun0', help='Network interface')

    args = parser.parse_args()

    injector = AttackInjector(interface=args.interface)
    injector.run_attack_scenario(args.scenario)
"""

        with open(output_file, "w") as f:
            f.write(template)

        output_file.chmod(0o755)
        print(f"[✓] Attack injection template created: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate NDT traffic replay from physical network capture"
    )
    parser.add_argument("physical_data_dir", type=Path, help="Directory containing physical network data")
    parser.add_argument("--output-dir", type=Path, default=Path("."), help="Output directory for replay scripts")
    parser.add_argument("--analyze-only", action="store_true", help="Only analyze traffic, do not generate scripts")

    args = parser.parse_args()

    # Initialize replayer
    replayer = TrafficReplayer(args.physical_data_dir)

    # Analyze physical traffic
    analysis = replayer.analyze_physical_traffic()

    print("\n" + "=" * 60)
    print("Traffic Analysis Summary:")
    print("=" * 60)
    print(f"Core Traffic:")
    print(f"  - Duration: {analysis['core'].get('duration_sec', 0)} seconds")
    print(f"  - Mean BW: {analysis['core'].get('mean_mbps', 0):.2f} Mbps")
    print(f"  - Peak BW: {analysis['core'].get('max_mbps', 0):.2f} Mbps")
    print(f"  - Packets/sec: {analysis['core'].get('packets_per_sec', 0):.2f}")
    print(f"\nPing Statistics:")
    print(f"  - Mean RTT: {analysis['ping'].get('mean_rtt_ms', 0):.2f} ms")
    print(f"  - Mean Jitter: {analysis['ping'].get('mean_jitter_ms', 0):.2f} ms")
    print("=" * 60 + "\n")

    if not args.analyze_only:
        # Generate replay scripts
        output_dir = args.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        replayer.generate_replay_script(analysis, output_dir / "replay_traffic.sh")

        replayer.generate_python_replayer(analysis, output_dir / "replay_traffic.py")

        replayer.create_attack_injection_template(output_dir / "inject_attacks.py")

        print("\n" + "=" * 60)
        print("Next Steps:")
        print("=" * 60)
        print("1. Copy scripts to UE VM:")
        print(f"   scp {output_dir}/*.py user@ue-vm:~/")
        print(f"   scp {output_dir}/*.sh user@ue-vm:~/")
        print("\n2. On UE VM, start monitoring on other VMs (5GC, gNB)")
        print("\n3. Run traffic replay:")
        print("   ./replay_traffic.py")
        print("\n4. In another terminal, inject attacks:")
        print("   ./inject_attacks.py --scenario moderate")
        print("\n5. Observe NDT behavior under attack conditions")
        print("=" * 60)


if __name__ == "__main__":
    main()

