#!/usr/bin/env python3
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
        print(f"\n{'='*50}")
        print(f"Running Attack Scenario: {scenario}")
        print(f"{'='*50}\n")

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

        print(f"\n{'='*50}")
        print("Attack Scenario Complete")
        print(f"{'='*50}\n")

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
