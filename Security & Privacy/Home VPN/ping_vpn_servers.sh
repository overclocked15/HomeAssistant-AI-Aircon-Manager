#!/bin/bash

VPN_FILE="/Users/nicholas/Library/CloudStorage/ProtonDrive-nicholashamann@proton.me-folder/Code Repo/Security & Privacy/au.protonvpn.udp.ovpn"

echo "Extracting unique IP addresses from VPN file..."
UNIQUE_IPS=$(grep "^remote " "$VPN_FILE" | awk '{print $2}' | sort -u)

echo "Found $(echo "$UNIQUE_IPS" | wc -l) unique IP addresses"
echo "Starting ping tests (4 pings per IP)..."
echo ""

# Use temporary files to store results
RESULTS_FILE=$(mktemp)
FAILED_FILE=$(mktemp)

for ip in $UNIQUE_IPS; do
    echo -n "Testing $ip... "
    
    ping_output=$(ping -c 4 "$ip" 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        avg_time=$(echo "$ping_output" | tail -1 | grep -o '[0-9]*\.[0-9]*/[0-9]*\.[0-9]*/[0-9]*\.[0-9]*' | cut -d'/' -f2)
        if [ -n "$avg_time" ]; then
            echo "$ip $avg_time" >> "$RESULTS_FILE"
            echo "${avg_time}ms"
        else
            echo "$ip" >> "$FAILED_FILE"
            echo "FAILED (no timing data)"
        fi
    else
        echo "$ip" >> "$FAILED_FILE"
        echo "FAILED (unreachable)"
    fi
done

echo ""
echo "=== RESULTS (sorted by average response time) ==="
echo ""

if [ -s "$RESULTS_FILE" ]; then
    sort -k2 -n "$RESULTS_FILE" | while read ip time; do
        printf "%-15s %8.2fms\n" "$ip" "$time"
    done
fi

if [ -s "$FAILED_FILE" ]; then
    echo ""
    echo "=== FAILED/UNREACHABLE IPs ==="
    cat "$FAILED_FILE"
fi

echo ""
echo "=== FASTEST SERVER ==="
if [ -s "$RESULTS_FILE" ]; then
    fastest_line=$(sort -k2 -n "$RESULTS_FILE" | head -1)
    fastest_ip=$(echo "$fastest_line" | awk '{print $1}')
    fastest_time=$(echo "$fastest_line" | awk '{print $2}')
    echo "Fastest server: $fastest_ip (${fastest_time}ms average)"
else
    echo "No servers responded to ping"
fi

# Clean up temporary files
rm -f "$RESULTS_FILE" "$FAILED_FILE"