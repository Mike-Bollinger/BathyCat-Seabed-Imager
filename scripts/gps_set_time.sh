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

# Set system time using timedatectl
if timedatectl set-time "$GPS_TIME_STR" >/dev/null 2>&1; then
    echo "System time set to GPS time: $GPS_TIME_STR UTC"
    exit 0
fi

# Fallback to date command if timedatectl fails
# Convert format: "YYYY-MM-DD HH:MM:SS" to "MMDDhhmmYYYY.ss"
if command -v date >/dev/null 2>&1; then
    DATE_STR=$(echo "$GPS_TIME_STR" | sed 's/\([0-9]\{4\}\)-\([0-9]\{2\}\)-\([0-9]\{2\}\) \([0-9]\{2\}\):\([0-9]\{2\}\):\([0-9]\{2\}\)/\2\3\4\5\1.\6/')
    
    if date "$DATE_STR" >/dev/null 2>&1; then
        echo "System time set to GPS time (date cmd): $GPS_TIME_STR UTC"
        exit 0
    fi
fi

echo "Error: Failed to set system time"
exit 1