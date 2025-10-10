#!/bin/bash
# Auto-generated NDT Traffic Replay Script
# Based on physical network capture from run20251010_125936
# Generated: 2025-10-10 13:51:39.358180

set -e

# Configuration
UE_INTERFACE="uesimtun0"
TARGET_IP="8.8.8.8"
TEST_DURATION=100
PING_COUNT=500
OUTPUT_LOG="$HOME/Desktop/traffic_data/ue_ping_replay.log"

echo "========================================="
echo "NDT Traffic Replay"
echo "Duration: ${TEST_DURATION} seconds"
echo "Ping count: ${PING_COUNT}"
echo "Output: ${OUTPUT_LOG}"
echo "========================================="

# Create output directory
mkdir -p "$(dirname "${OUTPUT_LOG}")"

# Function to generate ping traffic matching physical pattern
replay_ping() {
    local mean_rtt=50.477
    local mean_interval=0.100353536
    
    echo "[*] Starting ping replay (interval: ${mean_interval}s, count: ${PING_COUNT})"
    ping -I ${UE_INTERFACE} ${TARGET_IP} -i ${mean_interval} -s 64 -D -c ${PING_COUNT} > "${OUTPUT_LOG}" &
    PING_PID=$!
    echo "[✓] Ping started (PID: ${PING_PID}) → ${OUTPUT_LOG}"
}

# Function to generate traffic matching bandwidth pattern
replay_bandwidth() {
    local mean_bw=0.007287128712871289
    local max_bw=0.008096
    
    echo "[*] Starting bandwidth replay (mean: ${mean_bw} Mbps, max: ${max_bw} Mbps)"
    
    # Use iperf3 or curl to generate traffic
    # This is a placeholder - adjust based on available tools
    while true; do
        # Generate burst traffic
        dd if=/dev/zero bs=1M count=1 2>/dev/null | nc -w 1 ${TARGET_IP} 1234 || true
        sleep 0.1
    done &
    BW_PID=$!
    echo "[✓] Bandwidth generator started (PID: ${BW_PID})"
}

# Cleanup function
cleanup() {
    echo ""
    echo "[*] Stopping replay..."
    kill ${PING_PID} 2>/dev/null || true
    kill ${BW_PID} 2>/dev/null || true
    echo "[✓] Replay stopped"
}
trap cleanup EXIT INT TERM

# Start replay
replay_ping
#replay_bandwidth  # Uncomment if needed

# Run for specified duration
echo "[*] Running replay for ${TEST_DURATION} seconds..."
sleep ${TEST_DURATION}

echo "[✓] Replay complete"
echo "[✓] Ping log saved to: ${OUTPUT_LOG}"
