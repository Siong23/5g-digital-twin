#!/usr/bin/env python3
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import sys
import argparse

def clean_timestamp(ts: str) -> str:
    """Fix nanoseconds and timezone formatting"""
    if pd.isna(ts):
        return ts
    # Example: "Sep 30, 2025 15:22:49.374809000 +08"
    parts = ts.split()
    if len(parts) < 5:
        return ts
    # Remove extra digits in fractional seconds (keep 6 digits max)
    if "." in parts[3]:
        frac = parts[3].split(".")[1]
        if len(frac) > 6:
            parts[3] = parts[3].split(".")[0] + "." + frac[:6]
    # Fix timezone +08 → +08:00
    if parts[4].startswith("+") and len(parts[4]) == 3:
        parts[4] = parts[4] + ":00"
    return " ".join(parts)

def parse_traffic(csv_file: Path, out_file: Path, label: str):
    """Parse traffic CSV -> bandwidth per second"""
    # Check if file exists
    if not csv_file.exists():
        print(f"[✗] {label} file not found: {csv_file}")
        return pd.Series(dtype=float)
    
    try:
        df = pd.read_csv(
            csv_file,
            sep="\t",
            names=["time", "src", "dst", "teid", "len"],
            usecols=["time", "len"],
        )
        print(f"[{label}] Read {len(df)} rows from CSV")
        
        if df.empty:
            print(f"[✗] {label} CSV is empty")
            return pd.Series(dtype=float)
        
        # Clean timestamps
        df["time"] = df["time"].apply(clean_timestamp)
        
        # Parse to datetime
        df["time"] = pd.to_datetime(df["time"], errors="coerce", utc=True)
        print(f"[{label}] Valid timestamps: {df['time'].notna().sum()}/{len(df)}")
        
        df = df.dropna(subset=["time"])
        
        if df.empty:
            print(f"[✗] {label} No valid timestamps after parsing")
            return pd.Series(dtype=float)
        
        print(f"[{label}] Sample parsed times:", df["time"].head())
        
        # Bandwidth in Mbps (resample per 1 second)
        df_bw = df.set_index("time").resample("1s")["len"].sum() * 8 / 1e6
        
        if df_bw.empty or df_bw.sum() == 0:
            print(f"[✗] {label} No bandwidth data after resampling")
            return pd.Series(dtype=float)
        
        df_bw.to_csv(out_file, header=["bandwidth_mbps"])
        print(f"[✔] {label} traffic processed → {out_file.name} ({len(df_bw)} samples)")
        return df_bw
        
    except Exception as e:
        print(f"[✗] {label} Error parsing: {e}")
        return pd.Series(dtype=float)

def parse_ping(log_file: Path, out_file: Path):
    """Parse ping/fping log into RTT & Jitter"""
    if not log_file.exists():
        print(f"[✗] Ping log not found: {log_file}")
        return None
    
    rows = []
    with open(log_file) as f:
        for line in f:
            if "time=" in line:  # UERANSIM style
                try:
                    rtt = float([x for x in line.split() if "time=" in x][0].split("=")[1])
                    rows.append((pd.Timestamp.now(), rtt))
                except Exception:
                    pass
    
    if not rows:
        print("[✗] No ping data found in log")
        return None
    
    df = pd.DataFrame(rows, columns=["time", "rtt_ms"]).dropna()
    df["jitter_ms"] = df["rtt_ms"].diff().abs().fillna(0)
    df.to_csv(out_file, index=False)
    print(f"[✔] UE ping processed → {out_file.name} ({len(df)} samples)")
    return df

def validate_data_directory(data_dir: Path) -> bool:
    """Validate that the data directory exists and contains required files"""
    if not data_dir.exists():
        print(f"\n❌ Error: Directory does not exist: {data_dir}")
        print(f"   Please check the path and try again.")
        return False
    
    if not data_dir.is_dir():
        print(f"\n❌ Error: Path is not a directory: {data_dir}")
        return False
    
    # Check for at least one of the required files
    required_files = ["core_traffic.csv", "gnb_gtp.csv", "ue_ping.log"]
    found_files = [f for f in required_files if (data_dir / f).exists()]
    
    if not found_files:
        print(f"\n❌ Error: No traffic data files found in: {data_dir}")
        print(f"   Looking for: {', '.join(required_files)}")
        print(f"\n   Files in directory:")
        try:
            files = list(data_dir.iterdir())
            if files:
                for f in files[:10]:  # Show first 10 files
                    print(f"   - {f.name}")
                if len(files) > 10:
                    print(f"   ... and {len(files) - 10} more files")
            else:
                print("   (directory is empty)")
        except PermissionError:
            print("   (permission denied)")
        return False
    
    print(f"✓ Found {len(found_files)} data file(s): {', '.join(found_files)}")
    return True

def get_data_directory() -> Path:
    """Get data directory from user input with validation"""
    while True:
        print("\n" + "="*60)
        print("NDT Traffic Data Parser")
        print("="*60)
        user_input = input("\nEnter data directory path (or 'q' to quit): ").strip()
        
        if user_input.lower() == 'q':
            print("Exiting...")
            sys.exit(0)
        
        if not user_input:
            print("\n❌ Error: No path provided. Please enter a valid directory path.")
            continue
        
        # Expand user path (handle ~ for home directory)
        data_dir = Path(user_input).expanduser().resolve()
        
        if validate_data_directory(data_dir):
            return data_dir
        
        retry = input("\nTry another path? (y/n): ").strip().lower()
        if retry != 'y':
            print("Exiting...")
            sys.exit(1)

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Parse and plot NDT traffic data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 parse_traffic.py /srv/ndt_data/run20251008
  python3 parse_traffic.py ~/ndt_data/run20251008
  python3 parse_traffic.py  # Interactive mode
        """
    )
    parser.add_argument(
        'data_dir',
        nargs='?',  # Make it optional
        type=str,
        help='Directory containing traffic data files (core_traffic.csv, gnb_gtp.csv, ue_ping.log)'
    )
    parser.add_argument(
        '--no-plot',
        action='store_true',
        help='Skip plotting, only parse data'
    )
    
    args = parser.parse_args()
    
    # Get data directory
    if args.data_dir:
        data_dir = Path(args.data_dir).expanduser().resolve()
        if not validate_data_directory(data_dir):
            print("\n❌ Invalid data directory. Exiting.")
            sys.exit(1)
    else:
        # Interactive mode
        data_dir = get_data_directory()
    
    print(f"\n{'='*60}")
    print(f"Processing data from: {data_dir}")
    print(f"{'='*60}\n")
    
    # Define file paths
    core_csv = data_dir / "core_traffic.csv"
    gnb_csv = data_dir / "gnb_gtp.csv"
    ping_log = data_dir / "ue_ping.log"
    
    print(f"Checking files:")
    print(f"  Core CSV: {'✓ Found' if core_csv.exists() else '✗ Not found'}")
    print(f"  gNB CSV: {'✓ Found' if gnb_csv.exists() else '✗ Not found'}")
    print(f"  Ping log: {'✓ Found' if ping_log.exists() else '✗ Not found'}")
    print("-" * 60)
    
    # Parse traffic
    core_bw = parse_traffic(core_csv, data_dir / "core_bandwidth.csv", "Core")
    gnb_bw = parse_traffic(gnb_csv, data_dir / "gnb_bandwidth.csv", "gNB")
    ue_ping = parse_ping(ping_log, data_dir / "ue_ping.csv")
    
    print("-" * 60)
    print(f"Results:")
    print(f"  Core bandwidth samples: {len(core_bw)}")
    print(f"  gNB bandwidth samples: {len(gnb_bw)}")
    print(f"  UE ping samples: {len(ue_ping) if ue_ping is not None else 0}")
    print("-" * 60)
    
    # Check if we have any data to plot
    has_data = not core_bw.empty or not gnb_bw.empty or (ue_ping is not None and not ue_ping.empty)
    
    if not has_data:
        print("\n❌ No data available to plot. Please check your input files.")
        sys.exit(1)
    
    if args.no_plot:
        print("\n✓ Data parsing complete (plotting skipped)")
        return
    
    # ---- Plotting ----
    print("\nGenerating plots...")
    plot_count = 0
    
    if not core_bw.empty:
        fig1, ax1 = plt.subplots(figsize=(10, 6))
        ax1.plot(core_bw.index, core_bw.values, linewidth=1.5)
        ax1.set_title("Core Bandwidth (Mbps)", fontsize=14, fontweight='bold')
        ax1.set_xlabel("Time", fontsize=12)
        ax1.set_ylabel("Mbps", fontsize=12)
        ax1.grid(True, alpha=0.3)
        plt.tight_layout()
        print("[✔] Core bandwidth plot created (Figure 1)")
        plot_count += 1
    else:
        print("[!] No core bandwidth data to plot")
    
    if not gnb_bw.empty:
        fig2, ax2 = plt.subplots(figsize=(10, 6))
        ax2.plot(gnb_bw.index, gnb_bw.values, linewidth=1.5, color='orange')
        ax2.set_title("gNB Bandwidth (Mbps)", fontsize=14, fontweight='bold')
        ax2.set_xlabel("Time", fontsize=12)
        ax2.set_ylabel("Mbps", fontsize=12)
        ax2.grid(True, alpha=0.3)
        plt.tight_layout()
        print("[✔] gNB bandwidth plot created (Figure 2)")
        plot_count += 1
    else:
        print("[!] No gNB bandwidth data to plot")
    
    if ue_ping is not None and not ue_ping.empty:
        fig3, ax3 = plt.subplots(figsize=(10, 6))
        ax3.plot(ue_ping["time"], ue_ping["rtt_ms"], label="RTT", marker='o', 
                markersize=3, linewidth=1.5, color='green')
        ax3.plot(ue_ping["time"], ue_ping["jitter_ms"], label="Jitter", marker='s', 
                markersize=3, linewidth=1.5, color='red')
        ax3.set_title("UE Ping RTT & Jitter", fontsize=14, fontweight='bold')
        ax3.set_xlabel("Time", fontsize=12)
        ax3.set_ylabel("ms", fontsize=12)
        ax3.legend(fontsize=10)
        ax3.grid(True, alpha=0.3)
        plt.tight_layout()
        print("[✔] UE ping plot created (Figure 3)")
        plot_count += 1
    else:
        print("[!] No UE ping data to plot")
    
    print(f"\n{'='*60}")
    print(f"Summary: Generated {plot_count} plot(s)")
    print(f"{'='*60}")
    print("\nDisplaying plots... (Close plot windows to exit)")
    plt.show()
    print("\n✓ Complete!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user. Exiting...")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
