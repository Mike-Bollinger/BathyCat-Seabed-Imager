#!/bin/bash
# Device permissions setup script for BathyImager
# This script sets up proper permissions for camera, GPS, and GPIO devices

# Function to log messages
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - SETUP - $1"
}

log "Setting up device permissions for BathyImager..."

# Wait for devices to be available
sleep 2

# Set permissions for video devices (camera)
if ls /dev/video* >/dev/null 2>&1; then
    chmod 666 /dev/video* 2>/dev/null || true
    chgrp video /dev/video* 2>/dev/null || true
    log "Video device permissions set"
else
    log "WARNING: No video devices found"
fi

# Set permissions for USB serial devices (GPS)
if ls /dev/ttyUSB* >/dev/null 2>&1; then
    chmod 666 /dev/ttyUSB* 2>/dev/null || true
    chgrp dialout /dev/ttyUSB* 2>/dev/null || true
    log "USB serial device permissions set"
else
    log "WARNING: No USB serial devices found"
fi

# Set permissions for ACM serial devices (alternative GPS)
if ls /dev/ttyACM* >/dev/null 2>&1; then
    chmod 666 /dev/ttyACM* 2>/dev/null || true
    chgrp dialout /dev/ttyACM* 2>/dev/null || true
    log "ACM serial device permissions set"
fi

# Set permissions for GPIO memory device
if [ -e /dev/gpiomem ]; then
    chmod 666 /dev/gpiomem 2>/dev/null || true
    chgrp gpio /dev/gpiomem 2>/dev/null || true
    log "GPIO memory device permissions set"
else
    log "WARNING: GPIO memory device not found"
fi

# Set permissions for memory device (fallback)
if [ -e /dev/mem ]; then
    chmod 666 /dev/mem 2>/dev/null || true
    log "Memory device permissions set"
fi

# Setup sudo privileges for GPS time synchronization
log "Setting up sudo privileges for GPS time synchronization..."
SUDOERS_FILE="/etc/sudoers.d/bathyimager-gps-sync"

# Create sudoers entry for date command (GPS time sync)
cat > "$SUDOERS_FILE" << 'EOF'
# Allow bathyimager user to set system date for GPS time synchronization
# This is required for accurate GPS-synchronized timestamps on images
bathyimager ALL=(root) NOPASSWD: /usr/bin/date
EOF

# Set proper permissions on sudoers file
chmod 440 "$SUDOERS_FILE"
chown root:root "$SUDOERS_FILE"

# Verify sudoers syntax
if visudo -c -f "$SUDOERS_FILE" >/dev/null 2>&1; then
    log "GPS time sync sudo privileges configured successfully"
else
    log "ERROR: Invalid sudoers configuration, removing file"
    rm -f "$SUDOERS_FILE"
fi

# Verify user group membership
log "Verifying user 'bathyimager' group membership..."
groups bathyimager | grep -q video && log "User is in video group" || log "WARNING: User not in video group"
groups bathyimager | grep -q dialout && log "User is in dialout group" || log "WARNING: User not in dialout group"
groups bathyimager | grep -q gpio && log "User is in gpio group" || log "WARNING: User not in gpio group"

log "Device permissions setup complete"