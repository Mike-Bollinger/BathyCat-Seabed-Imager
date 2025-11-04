#!/bin/bash
#
# GPS Time Sync Helper Script
# ===========================
#
# This script sets the system time from GPS UTC time
# Called by the BathyImager GPS module when time sync is needed
#
# Usage: ./gps_set_time.sh "YYYY-MM-DD HH:MM:SS"

set -e

if [ $# -ne 1 ]; then
    echo "Usage: $0 'YYYY-MM-DD HH:MM:SS'"
    exit 1
fi

GPS_TIME_STR="$1"

# Validate time format (basic check)
if [[ ! "$GPS_TIME_STR" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}\ [0-9]{2}:[0-9]{2}:[0-9]{2}$ ]]; then
    echo "Error: Invalid time format. Expected: YYYY-MM-DD HH:MM:SS"
    exit 1
fi

# Set timezone to UTC first
timedatectl set-timezone UTC >/dev/null 2>&1 || true

# Check if NTP is active (could prevent time setting)
NTP_STATUS=""
if command -v timedatectl >/dev/null 2>&1; then
    NTP_STATUS=$(timedatectl status 2>/dev/null | grep -E "NTP|synchronization" | head -1 || true)
fi

# Try timedatectl first (preferred method)
if command -v timedatectl >/dev/null 2>&1; then
    echo "Attempting to set time using timedatectl..."
    
    # Disable NTP temporarily if it's active
    if echo "$NTP_STATUS" | grep -q "active\|yes" 2>/dev/null; then
        echo "Disabling NTP temporarily for manual time sync..."
        timedatectl set-ntp false 2>/dev/null || true
        sleep 1
    fi
    
    # Set system time
    if timedatectl set-time "$GPS_TIME_STR" 2>/dev/null; then
        echo "System time set to GPS time: $GPS_TIME_STR UTC"
        
        # Re-enable NTP if it was active
        if echo "$NTP_STATUS" | grep -q "active\|yes" 2>/dev/null; then
            timedatectl set-ntp true 2>/dev/null || true
        fi
        exit 0
    else
        echo "Error: timedatectl failed to set time" >&2
        timedatectl status 2>&1 | head -5 >&2 || true
    fi
fi

# Fallback to date command if timedatectl fails
echo "Falling back to date command..." >&2
if command -v date >/dev/null 2>&1; then
    # Convert format: "YYYY-MM-DD HH:MM:SS" to "MMDDhhmmYYYY.ss"
    DATE_STR=$(echo "$GPS_TIME_STR" | sed 's/\([0-9]\{4\}\)-\([0-9]\{2\}\)-\([0-9]\{2\}\) \([0-9]\{2\}\):\([0-9]\{2\}\):\([0-9]\{2\}\)/\2\3\4\5\1.\6/')
    
    if date "$DATE_STR" 2>/dev/null; then
        echo "System time set to GPS time (date cmd): $GPS_TIME_STR UTC"
        exit 0
    else
        echo "Error: date command failed with format $DATE_STR" >&2
    fi
else
    echo "Error: date command not available" >&2
fi

echo "Error: All time setting methods failed" >&2
echo "GPS time: $GPS_TIME_STR UTC" >&2
echo "Current system time: $(date)" >&2
echo "NTP status: $NTP_STATUS" >&2
exit 1