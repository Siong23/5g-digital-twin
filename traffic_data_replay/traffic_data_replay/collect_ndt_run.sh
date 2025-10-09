#!/usr/bin/env bash
set -uo pipefail

# Generate destination with today's date
DATE=$(date +%Y%m%d)
DEST="/home/open5gs/Desktop/traffic_data_replay/gnb_core_replay/NDT_run${DATE}"

echo "========================================="
echo "NDT Data Collection"
echo "Date: $(date)"
echo "Destination: $DEST"
echo "========================================="

# Create destination directory
mkdir -p "$DEST"

# List of sources: "user@host:/path"
SOURCES=(
  "server2@192.168.0.115:/home/server2/Desktop/traffic_data/gnb_gtp_replay.pcap"
  "open5gs@192.168.0.132:/home/open5gs/Desktop/traffic_data/core_traffic_replay.pcap"
  "server2@192.168.0.115:/home/server2/Desktop/traffic_data/ue_ping_replay.log"
)

# Counter for tracking
SUCCESS=0
FAILED=0

for src in "${SOURCES[@]}"; do
  echo ""
  echo "Pulling $src ..."
  if rsync -avh --progress "$src" "$DEST"/; then
    ((SUCCESS++))
  else
    echo "⚠️  Failed to pull $src"
    ((FAILED++))
  fi
done

echo ""
echo "========================================="
echo "Collection Summary:"
echo "  Success: $SUCCESS"
echo "  Failed: $FAILED"
echo "  Location: $DEST"
echo "========================================="

# Convert PCAPs to CSV automatically
echo ""
echo "Converting PCAPs to CSV..."

# Convert gNB PCAP
if [ -f "$DEST/gnb_gtp_replay.pcap" ]; then
  echo "Converting gnb_gtp_replay.pcap..."
  tshark -r "$DEST/gnb_gtp_replay.pcap" \
    -T fields \
    -e frame.time \
    -e ip.src \
    -e ip.dst \
    -e gtp.teid \
    -e frame.len \
    -E separator=$'\t' \
    > "$DEST/gnb_gtp_replay.csv" 2>/dev/null || echo "⚠️  tshark failed for gnb_gtp_replay.pcap"
fi

# Convert Core PCAP
if [ -f "$DEST/core_traffic_replay.pcap" ]; then
  echo "Converting core_traffic_replay.pcap..."
  tshark -r "$DEST/core_traffic_replay.pcap" \
    -T fields \
    -e frame.time \
    -e ip.src \
    -e ip.dst \
    -e gtp.teid \
    -e frame.len \
    -E separator=$'\t' \
    > "$DEST/core_traffic_replay.csv" 2>/dev/null || echo "⚠️  tshark failed for core_traffic_replay.pcap"
fi

echo ""
echo "========================================="
echo "Files in $DEST:"
ls -lh "$DEST"
echo "========================================="
echo "✓ All done! Ready for analysis."
