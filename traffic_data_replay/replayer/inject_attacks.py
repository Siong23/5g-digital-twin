#!/usr/bin/env python3
'''
Attack Injection Module for NDT (Network-Safe Version)
Inject various attacks during traffic replay without crashing the network
'''
import time
import subprocess
import random
import sys
from enum import Enum

class AttackType(Enum):
    PACKET_DROP = "packet_drop"
    DELAY_INJECTION = "delay_injection"
    BANDWIDTH_EXHAUSTION = "bandwidth_exhaustion"
    SIGNALING_STORM = "signaling_storm"
    JITTER_INJECTION = "jitter_injection"

class AttackInjector:
    def __init__(self, interface: str = "uesimtun0"):
        self.interface = interface
        self.attack_active = False
        
    def check_interface(self) -> bool:
        '''Verify interface exists before applying attacks'''
        result = subprocess.run(
            ['ip', 'link', 'show', self.interface],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return result.returncode == 0
    
    def cleanup_tc(self):
        '''Clean up any existing tc rules'''
        subprocess.run([
            'sudo', 'tc', 'qdisc', 'del', 'dev', self.interface, 'root'
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.5)  # Wait for cleanup
    
    def verify_connectivity(self, target: str = "8.8.8.8") -> bool:
        '''Check if basic connectivity still works'''
        result = subprocess.run(
            ['ping', '-I', self.interface, '-c', '1', '-W', '2', target],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return result.returncode == 0
    
    def inject_packet_drop(self, drop_rate: float = 0.1, duration: int = 10):
        '''
        Inject packet drop using tc (traffic control)
        Args:
            drop_rate: Percentage of packets to drop (0.0-1.0)
            duration: Duration in seconds
        
        Safe limits: max 25% drop rate
        '''
        # Cap at 25% to prevent network collapse
        safe_drop_rate = min(drop_rate, 0.25)
        
        print(f"[ATTACK] Packet Drop: {safe_drop_rate*100:.1f}% for {duration}s")
        
        self.cleanup_tc()
        
        # Add packet loss
        result = subprocess.run([
            'sudo', 'tc', 'qdisc', 'add', 'dev', self.interface,
            'root', 'netem', 'loss', f'{safe_drop_rate*100}%'
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"[ERROR] Failed to apply packet drop: {result.stderr}")
            return
        
        # Monitor connectivity during attack
        start_time = time.time()
        check_interval = max(2, duration // 5)  # Check 5 times during attack
        last_check = start_time
        
        while time.time() - start_time < duration:
            time.sleep(1)
            
            # Periodic connectivity check
            if time.time() - last_check >= check_interval:
                if not self.verify_connectivity():
                    print("[WARNING] Connectivity lost! Reducing attack intensity...")
                    self.cleanup_tc()
                    # Reapply with reduced rate
                    subprocess.run([
                        'sudo', 'tc', 'qdisc', 'add', 'dev', self.interface,
                        'root', 'netem', 'loss', f'{safe_drop_rate*50}%'  # Half the rate
                    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                last_check = time.time()
        
        # Remove packet loss
        self.cleanup_tc()
        
        # Verify recovery
        if self.verify_connectivity():
            print("[ATTACK] Packet Drop stopped - connectivity restored")
        else:
            print("[WARNING] Connectivity issues persist - waiting for recovery...")
            time.sleep(5)
    
    def inject_delay(self, delay_ms: int = 100, jitter_ms: int = 50, duration: int = 10):
        '''
        Inject network delay/latency
        Args:
            delay_ms: Base delay in milliseconds
            jitter_ms: Jitter variation in milliseconds
            duration: Duration in seconds
        
        Safe limits: max 500ms delay, 200ms jitter
        '''
        # Cap at safe levels
        safe_delay = min(delay_ms, 500)
        safe_jitter = min(jitter_ms, 200)
        
        print(f"[ATTACK] Delay Injection: {safe_delay}ms ±{safe_jitter}ms for {duration}s")
        
        self.cleanup_tc()
        
        subprocess.run([
            'sudo', 'tc', 'qdisc', 'add', 'dev', self.interface,
            'root', 'netem', 'delay', f'{safe_delay}ms', f'{safe_jitter}ms'
        ])
        
        time.sleep(duration)
        
        self.cleanup_tc()
        print("[ATTACK] Delay Injection stopped")
    
    def inject_jitter(self, base_delay_ms: int = 50, jitter_ms: int = 100, duration: int = 10):
        '''
        Inject high jitter (variable delay)
        Args:
            base_delay_ms: Base delay in milliseconds
            jitter_ms: Jitter variation (can be larger than base)
            duration: Duration in seconds
        '''
        print(f"[ATTACK] Jitter Injection: {base_delay_ms}ms ±{jitter_ms}ms for {duration}s")
        
        self.cleanup_tc()
        
        subprocess.run([
            'sudo', 'tc', 'qdisc', 'add', 'dev', self.interface,
            'root', 'netem', 'delay', f'{base_delay_ms}ms', f'{jitter_ms}ms',
            'distribution', 'normal'  # More realistic jitter distribution
        ])
        
        time.sleep(duration)
        
        self.cleanup_tc()
        print("[ATTACK] Jitter Injection stopped")
    
    def inject_bandwidth_limit(self, limit_mbps: float = 1.0, duration: int = 10):
        '''
        Limit bandwidth to simulate exhaustion
        Args:
            limit_mbps: Bandwidth limit in Mbps
            duration: Duration in seconds
        
        Safe limits: min 0.5 Mbps (enough to keep connection alive)
        '''
        # Ensure minimum bandwidth for connectivity
        safe_limit = max(limit_mbps, 0.5)
        
        print(f"[ATTACK] Bandwidth Limit: {safe_limit} Mbps for {duration}s")
        
        self.cleanup_tc()
        
        limit_kbps = int(safe_limit * 1000)
        burst_kbps = max(32, int(limit_kbps * 0.1))  # 10% of rate or 32kbit
        
        subprocess.run([
            'sudo', 'tc', 'qdisc', 'add', 'dev', self.interface,
            'root', 'tbf', 'rate', f'{limit_kbps}kbit',
            'burst', f'{burst_kbps}kbit', 'latency', '400ms'
        ])
        
        time.sleep(duration)
        
        self.cleanup_tc()
        print("[ATTACK] Bandwidth Limit removed")
    
    def inject_signaling_storm(self, target: str, duration: int = 10, rate: int = 10):
        '''
        Inject signaling storm (rapid connection attempts)
        Args:
            target: Target IP
            duration: Duration in seconds
            rate: Requests per second (safe limit: 10-20)
        
        Safe limits: max 20 requests/second
        '''
        safe_rate = min(rate, 20)  # Cap at 20 req/s
        interval = 1.0 / safe_rate
        
        print(f"[ATTACK] Signaling Storm: {safe_rate} req/s for {duration}s")
        
        start_time = time.time()
        count = 0
        
        while time.time() - start_time < duration:
            # Send ping with short timeout
            subprocess.run(
                ['ping', '-I', self.interface, '-c', '1', '-W', '1', target],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            count += 1
            
            if count % 50 == 0:
                # Periodic check to prevent overwhelming
                time.sleep(0.5)
            else:
                time.sleep(interval)
        
        print(f"[ATTACK] Signaling Storm stopped ({count} requests sent)")
    
    def inject_combined_stress(self, duration: int = 20):
        '''
        Apply multiple mild attacks simultaneously
        More realistic than single severe attack
        '''
        print(f"[ATTACK] Combined Stress Test for {duration}s")
        print("  - 10% packet loss")
        print("  - 100ms delay ±30ms jitter")
        print("  - 3 Mbps bandwidth limit")
        
        self.cleanup_tc()
        
        # Apply combined netem rules
        subprocess.run([
            'sudo', 'tc', 'qdisc', 'add', 'dev', self.interface,
            'root', 'netem',
            'loss', '10%',           # Moderate packet loss
            'delay', '100ms', '30ms', # Moderate delay with jitter
            'rate', '3mbit'          # Moderate bandwidth limit
        ])
        
        # Monitor during attack
        check_interval = 5
        for i in range(0, duration, check_interval):
            time.sleep(check_interval)
            if not self.verify_connectivity():
                print("[WARNING] Connectivity degraded, easing attack...")
                self.cleanup_tc()
                # Reapply with gentler settings
                subprocess.run([
                    'sudo', 'tc', 'qdisc', 'add', 'dev', self.interface,
                    'root', 'netem',
                    'loss', '5%',
                    'delay', '50ms', '20ms',
                    'rate', '5mbit'
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        self.cleanup_tc()
        print("[ATTACK] Combined Stress Test stopped")
    
    def run_attack_scenario(self, scenario: str = "moderate"):
        '''
        Run predefined attack scenario (network-safe versions)
        '''
        if not self.check_interface():
            print(f"[ERROR] Interface {self.interface} not found!")
            sys.exit(1)
        
        print(f"{'='*60}")
        print(f"Running Attack Scenario: {scenario.upper()}")
        print(f"Interface: {self.interface}")
        print(f"{'='*60}")
        
        # Verify initial connectivity
        if not self.verify_connectivity():
            print("[ERROR] No initial connectivity! Check network setup.")
            sys.exit(1)
        
        print("[✓] Initial connectivity verified")
        
        if scenario == "mild":
            # Mild attack: slight delay and packet loss
            print("[Phase 1] Baseline period (30s)")
            time.sleep(30)
            
            print("[Phase 2] Mild packet loss")
            self.inject_packet_drop(drop_rate=0.05, duration=20)
            
            print("[Phase 3] Recovery period (20s)")
            time.sleep(20)
            
            print("[Phase 4] Mild delay")
            self.inject_delay(delay_ms=50, jitter_ms=20, duration=20)
            
        elif scenario == "moderate":
            # Moderate attack: noticeable impact but stable
            print("[Phase 1] Baseline period (20s)")
            time.sleep(20)
            
            print("[Phase 2] Moderate packet loss")
            self.inject_packet_drop(drop_rate=0.15, duration=30)
            
            print("[Phase 3] Recovery period (15s)")
            time.sleep(15)
            
            print("[Phase 4] Bandwidth limitation")
            self.inject_bandwidth_limit(limit_mbps=2.0, duration=30)
            
            print("[Phase 5] Recovery period (15s)")
            time.sleep(15)
            
            print("[Phase 6] Delay injection")
            self.inject_delay(delay_ms=150, jitter_ms=50, duration=30)
            
        elif scenario == "heavy":
            # Heavy but SAFE: strong impact without network collapse
            print("[Phase 1] Baseline period (15s)")
            time.sleep(15)
            
            print("[Phase 2] Heavy packet loss (20%)")
            self.inject_packet_drop(drop_rate=0.20, duration=25)
            
            print("[Phase 3] Short recovery (10s)")
            time.sleep(10)
            
            print("[Phase 4] Severe bandwidth limit (1 Mbps)")
            self.inject_bandwidth_limit(limit_mbps=1.0, duration=25)
            
            print("[Phase 5] Short recovery (10s)")
            time.sleep(10)
            
            print("[Phase 6] High jitter")
            self.inject_jitter(base_delay_ms=100, jitter_ms=150, duration=25)
            
            print("[Phase 7] Short recovery (10s)")
            time.sleep(10)
            
            print("[Phase 8] Combined stress")
            self.inject_combined_stress(duration=25)
            
        elif scenario == "extreme":
            # Extreme but CONTROLLED: multiple phases with recovery
            print("[Phase 1] Baseline period (15s)")
            time.sleep(15)
            
            print("[Phase 2] Signaling storm")
            self.inject_signaling_storm(target="8.8.8.8", duration=20, rate=15)
            
            print("[Phase 3] Recovery period (10s)")
            time.sleep(10)
            
            print("[Phase 4] Heavy packet loss (25% - max safe)")
            self.inject_packet_drop(drop_rate=0.25, duration=20)
            
            print("[Phase 5] Recovery period (10s)")
            time.sleep(10)
            
            print("[Phase 6] Minimum bandwidth (0.5 Mbps)")
            self.inject_bandwidth_limit(limit_mbps=0.5, duration=20)
            
            print("[Phase 7] Recovery period (10s)")
            time.sleep(10)
            
            print("[Phase 8] Combined stress test")
            self.inject_combined_stress(duration=30)
            
        elif scenario == "mixed":
            # Random attacks with safe limits
            attacks = [
                lambda: self.inject_packet_drop(0.10, 15),
                lambda: self.inject_delay(100, 40, 15),
                lambda: self.inject_bandwidth_limit(2.0, 15),
                lambda: self.inject_jitter(50, 80, 15),
            ]
            
            print("[Phase 1] Baseline period (20s)")
            time.sleep(20)
            
            for i in range(4):
                print(f"[Phase {i+2}] Random attack #{i+1}")
                attack = random.choice(attacks)
                attack()
                
                print(f"[Phase {i+2}] Recovery period (15s)")
                time.sleep(15)
        
        else:
            print(f"[ERROR] Unknown scenario: {scenario}")
            print("Available scenarios: mild, moderate, heavy, extreme, mixed")
            sys.exit(1)
        
        # Final cleanup and verification
        self.cleanup_tc()
        print(f"{'='*60}")
        print("Attack Scenario Complete")
        
        if self.verify_connectivity():
            print("[✓] Connectivity verified - network is stable")
        else:
            print("[WARNING] Connectivity issues detected - network may need recovery time")
        
        print(f"{'='*60}")

# Example usage
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='NDT Attack Injector (Network-Safe)')
    parser.add_argument(
        '--scenario', 
        choices=['mild', 'moderate', 'heavy', 'extreme', 'mixed'],
        default='moderate', 
        help='Attack scenario (default: moderate)'
    )
    parser.add_argument(
        '--interface', 
        default='uesimtun0', 
        help='Network interface (default: uesimtun0)'
    )
    
    args = parser.parse_args()
    
    try:
        injector = AttackInjector(interface=args.interface)
        injector.run_attack_scenario(args.scenario)
    except KeyboardInterrupt:
        print("[!] Interrupted by user - cleaning up...")
        injector.cleanup_tc()
        print("[✓] Cleanup complete")
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        print("[*] Attempting cleanup...")
        injector.cleanup_tc()
