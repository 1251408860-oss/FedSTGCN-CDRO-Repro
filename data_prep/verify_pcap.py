#!/usr/bin/env python3
"""
Phase 1 - Verify captured PCAP data (Overhauled).

Updated for new scale:
  - 20 benign users  (10.0.0.10-29)
  - 70 attack bots   (10.0.0.30-99)
  - pcap size target: >= 50MB
  - Bot type clustering by IAT pattern

Usage: python verify_pcap.py [pcap_file]
"""
import sys
import math
import os
from collections import Counter, defaultdict

try:
    from scapy.all import rdpcap, IP, TCP, Raw
except ImportError:
    print("ERROR: scapy required. Install with: pip install scapy")
    sys.exit(1)

PCAP_FILE = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser('~/full_arena_v2.pcap')
TARGET_IP = '10.0.0.100'
EXPECTED_USERS = 20   # 10.0.0.10 - 10.0.0.29
EXPECTED_BOTS = 70    # 10.0.0.30 - 10.0.0.99
MIN_PCAP_MB = 50      # Target minimum pcap size


def calculate_shannon_entropy(data_bytes):
    if not data_bytes:
        return 0.0
    length = len(data_bytes)
    counts = Counter(data_bytes)
    entropy = 0.0
    for count in counts.values():
        p = count / length
        entropy -= p * math.log2(p)
    return entropy


def classify_bot_type_by_iat(timestamps):
    """
    Heuristic bot type classification based on IAT pattern:
      - slowburn: low variance, IAT mostly 2-8s
      - burst:    bimodal IAT (long gaps + short bursts)
      - mimic:    moderate variance, session-like grouping
    """
    if len(timestamps) < 5:
        return "unknown"

    ts = sorted(timestamps)
    iats = [ts[i+1] - ts[i] for i in range(len(ts)-1)]
    if not iats:
        return "unknown"

    mean_iat = sum(iats) / len(iats)
    variance = sum((x - mean_iat) ** 2 for x in iats) / len(iats)
    std_iat = math.sqrt(variance) if variance > 0 else 0

    # Count how many IATs are very short (<1s) vs very long (>15s)
    short_iats = sum(1 for x in iats if x < 1.0)
    long_iats = sum(1 for x in iats if x > 15.0)
    short_ratio = short_iats / len(iats)
    long_ratio = long_iats / len(iats)

    # Burst: has both very short and very long IATs
    if short_ratio > 0.2 and long_ratio > 0.1:
        return "burst"

    # Mimic: moderate variance, some longer gaps (session boundaries)
    if std_iat > 5.0 and long_ratio > 0.05:
        return "mimic"

    # Slowburn: steady, low variance
    if mean_iat >= 1.5 and std_iat < 4.0:
        return "slowburn"

    return "unknown"


def main():
    if not os.path.exists(PCAP_FILE):
        print(f"ERROR: {PCAP_FILE} not found!")
        return

    file_size = os.path.getsize(PCAP_FILE)
    file_mb = file_size / 1048576
    print(f"Loading {PCAP_FILE} ({file_mb:.1f} MB)...")

    # ---- Pcap size check ----
    print(f"\n{'='*50}")
    print(f"  PCAP SIZE CHECK")
    print(f"{'='*50}")
    if file_mb >= MIN_PCAP_MB:
        print(f"  [PASS] {file_mb:.1f} MB >= {MIN_PCAP_MB} MB target")
    else:
        print(f"  [WARN] {file_mb:.1f} MB < {MIN_PCAP_MB} MB target. Consider longer duration.")

    packets = rdpcap(PCAP_FILE)
    print(f"\nTotal packets: {len(packets)}\n")

    # Aggregate flows by source IP (only traffic TO the target)
    flows = defaultdict(lambda: {
        'packets': 0, 'bytes': 0, 'payloads': b"",
        'timestamps': [], 'src_ports': set()
    })

    for pkt in packets:
        if IP in pkt and TCP in pkt:
            src = pkt[IP].src
            dst = pkt[IP].dst
            if dst == TARGET_IP:
                flows[src]['packets'] += 1
                flows[src]['bytes'] += len(pkt)
                flows[src]['timestamps'].append(float(pkt.time))
                flows[src]['src_ports'].add(pkt[TCP].sport)
                if Raw in pkt:
                    flows[src]['payloads'] += bytes(pkt[Raw].load)

    if not flows:
        print("ERROR: No traffic to target found in PCAP!")
        return

    # Classify and display
    benign_ips = []
    attack_ips = []
    other_ips = []

    header = (f"{'Source IP':<16} | {'Type':<8} | {'BotType':<9} | {'Pkts':>6} | "
              f"{'Bytes':>10} | {'Duration':>8} | {'Entropy':>8} | {'Avg IAT':>8} | {'Ports':>5}")
    sep = "=" * len(header)
    print(sep)
    print(header)
    print(sep)

    bot_type_clusters = defaultdict(list)  # inferred_type -> [ip, ...]

    for ip in sorted(flows.keys(), key=lambda x: tuple(int(p) for p in x.split('.'))):
        f = flows[ip]
        if f['packets'] < 2:
            continue

        ts = sorted(f['timestamps'])
        duration = ts[-1] - ts[0] if len(ts) > 1 else 0
        entropy = calculate_shannon_entropy(f['payloads'])
        avg_iat = duration / (f['packets'] - 1) if f['packets'] > 1 else 0
        n_ports = len(f['src_ports'])

        last_octet = int(ip.split('.')[3])
        if 10 <= last_octet <= 29:
            ip_type = "BENIGN"
            benign_ips.append(ip)
            bot_type_str = "-"
        elif 30 <= last_octet <= 99:
            ip_type = "ATTACK"
            attack_ips.append(ip)
            inferred = classify_bot_type_by_iat(f['timestamps'])
            bot_type_str = inferred
            bot_type_clusters[inferred].append(ip)
        else:
            ip_type = "OTHER"
            other_ips.append(ip)
            bot_type_str = "-"

        print(f"{ip:<16} | {ip_type:<8} | {bot_type_str:<9} | {f['packets']:>6} | "
              f"{f['bytes']:>10} | {duration:>7.1f}s | {entropy:>8.4f} | {avg_iat:>7.2f}s | {n_ports:>5}")

    print(sep)

    # ==========================================
    # Summary
    # ==========================================
    print(f"\n{'='*50}")
    print(f"  SUMMARY")
    print(f"{'='*50}")
    print(f"  Benign IPs captured : {len(benign_ips)}/{EXPECTED_USERS}")
    print(f"  Attack IPs captured : {len(attack_ips)}/{EXPECTED_BOTS}")
    print(f"  Other IPs           : {len(other_ips)}")
    print(f"  Total unique sources: {len(flows)}")

    # Verdict
    if len(benign_ips) == 0:
        print(f"\n  [FAIL] No benign traffic captured!")
    elif len(benign_ips) < EXPECTED_USERS:
        print(f"\n  [WARN] Only {len(benign_ips)}/{EXPECTED_USERS} benign IPs captured")

    if len(attack_ips) == 0:
        print(f"\n  [FAIL] No attack traffic captured! Bot scripts likely failed.")
    elif len(attack_ips) < EXPECTED_BOTS:
        print(f"\n  [WARN] Only {len(attack_ips)}/{EXPECTED_BOTS} attack IPs captured")

    if len(benign_ips) >= EXPECTED_USERS and len(attack_ips) >= EXPECTED_BOTS:
        print(f"\n  [PASS] All expected traffic captured!")

    # ==========================================
    # Bot Type Clustering Analysis
    # ==========================================
    if bot_type_clusters:
        print(f"\n{'='*50}")
        print(f"  BOT TYPE CLUSTERING (IAT-based)")
        print(f"{'='*50}")
        for btype in ["slowburn", "burst", "mimic", "unknown"]:
            ips = bot_type_clusters.get(btype, [])
            if ips:
                # Compute aggregate stats for this cluster
                total_pkts = sum(flows[ip]['packets'] for ip in ips)
                all_iats = []
                for ip in ips:
                    ts = sorted(flows[ip]['timestamps'])
                    all_iats.extend(ts[i+1] - ts[i] for i in range(len(ts)-1))
                mean_iat = sum(all_iats) / len(all_iats) if all_iats else 0
                std_iat = math.sqrt(sum((x - mean_iat)**2 for x in all_iats) / len(all_iats)) if all_iats else 0

                print(f"  {btype:9s}: {len(ips):>3} IPs, {total_pkts:>7} pkts, "
                      f"mean_IAT={mean_iat:.2f}s, std_IAT={std_iat:.2f}s")

        # Expected vs inferred
        print(f"\n  Expected allocation: slowburn=42, burst=18, mimic=10")
        print(f"  Inferred clusters:  slowburn={len(bot_type_clusters.get('slowburn', []))}, "
              f"burst={len(bot_type_clusters.get('burst', []))}, "
              f"mimic={len(bot_type_clusters.get('mimic', []))}, "
              f"unknown={len(bot_type_clusters.get('unknown', []))}")

    # ==========================================
    # Entropy comparison
    # ==========================================
    if benign_ips and attack_ips:
        benign_entropies = [calculate_shannon_entropy(flows[ip]['payloads'])
                           for ip in benign_ips if flows[ip]['payloads']]
        attack_entropies = [calculate_shannon_entropy(flows[ip]['payloads'])
                           for ip in attack_ips if flows[ip]['payloads']]

        if benign_entropies and attack_entropies:
            avg_benign = sum(benign_entropies) / len(benign_entropies)
            avg_attack = sum(attack_entropies) / len(attack_entropies)
            print(f"\n{'='*50}")
            print(f"  ENTROPY ANALYSIS")
            print(f"{'='*50}")
            print(f"  Benign avg entropy : {avg_benign:.4f} bits/byte")
            print(f"  Attack avg entropy : {avg_attack:.4f} bits/byte")
            print(f"  Entropy gap        : {avg_attack - avg_benign:+.4f}")
            if avg_attack > avg_benign:
                print(f"  -> LLM payloads have HIGHER entropy (expected)")
            else:
                print(f"  -> Attack entropy is lower (unexpected)")

    # ==========================================
    # Traffic volume comparison
    # ==========================================
    if benign_ips and attack_ips:
        benign_pkts = sum(flows[ip]['packets'] for ip in benign_ips)
        attack_pkts = sum(flows[ip]['packets'] for ip in attack_ips)
        benign_bytes = sum(flows[ip]['bytes'] for ip in benign_ips)
        attack_bytes = sum(flows[ip]['bytes'] for ip in attack_ips)

        print(f"\n{'='*50}")
        print(f"  TRAFFIC VOLUME")
        print(f"{'='*50}")
        print(f"  Benign: {benign_pkts:>7} pkts, {benign_bytes/1048576:>8.2f} MB")
        print(f"  Attack: {attack_pkts:>7} pkts, {attack_bytes/1048576:>8.2f} MB")
        print(f"  Ratio (attack/benign): {attack_pkts/max(benign_pkts,1):.2f}x packets, "
              f"{attack_bytes/max(benign_bytes,1):.2f}x bytes")

        # Per-type breakdown
        if bot_type_clusters:
            print(f"\n  Per-type volume:")
            for btype in ["slowburn", "burst", "mimic"]:
                ips = bot_type_clusters.get(btype, [])
                if ips:
                    pkts = sum(flows[ip]['packets'] for ip in ips)
                    bts = sum(flows[ip]['bytes'] for ip in ips)
                    print(f"    {btype:9s}: {pkts:>7} pkts, {bts/1048576:>8.2f} MB "
                          f"(avg {pkts/len(ips):.0f} pkts/bot)")

    print()


if __name__ == "__main__":
    main()
