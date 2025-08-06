#!/bin/bash
"""
Service Setup Script for BathyCat Seabed Imager
==============================================

Sets up systemd services and configuration for automatic startup.

Author: BathyCat Systems
Date: August 2025
"""

set -e

# Configuration
SERVICE_NAME="bathycat-imager"
INSTALL_DIR="/opt/bathycat"
CONFIG_DIR="/etc/bathycat"
LOG_DIR="/var/log/bathycat"
USER="pi"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "This script must be run as root (use sudo)"
    exit 1
fi

print_status "Setting up BathyCat Seabed Imager services..."

# Create systemd service file
print_status "Creating systemd service..."

cat > /etc/systemd/system/$SERVICE_NAME.service << EOF
[Unit]
Description=BathyCat Seabed Imager
Documentation=https://github.com/bathycat/seabed-imager
After=network.target gpsd.service
Wants=gpsd.service
StartLimitIntervalSec=0

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONPATH=$INSTALL_DIR/src
ExecStart=$INSTALL_DIR/venv/bin/python3 $INSTALL_DIR/src/bathycat_imager.py --config $CONFIG_DIR/config.json
ExecReload=/bin/kill -HUP \$MAINPID
KillMode=process
Restart=always
RestartSec=10
TimeoutStopSec=30

# Performance optimizations
Nice=-10
IOSchedulingClass=2
IOSchedulingPriority=4

# Resource limits
LimitNOFILE=65536
LimitNPROC=32768

# Security settings
NoNewPrivileges=yes
PrivateTmp=yes
ProtectHome=yes
ProtectSystem=strict
ReadWritePaths=$LOG_DIR /media/ssd

[Install]
WantedBy=multi-user.target
EOF

# Create log rotation configuration
print_status "Setting up log rotation..."

cat > /etc/logrotate.d/bathycat << EOF
$LOG_DIR/bathycat.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $USER $USER
    postrotate
        systemctl reload-or-restart $SERVICE_NAME
    endscript
}
EOF

# Create maintenance timer service
print_status "Creating maintenance timer..."

cat > /etc/systemd/system/bathycat-maintenance.service << EOF
[Unit]
Description=BathyCat Maintenance Tasks
Requires=bathycat-imager.service

[Service]
Type=oneshot
User=$USER
Group=$USER
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/venv/bin
ExecStart=$INSTALL_DIR/venv/bin/python3 -c "
import sys
sys.path.insert(0, '$INSTALL_DIR/src')
from storage_manager import StorageManager
from config import Config
import asyncio

async def maintenance():
    config = Config('$CONFIG_DIR/config.json')
    storage = StorageManager(config)
    await storage.initialize()
    await storage.auto_cleanup_if_needed()
    print('Maintenance complete')

asyncio.run(maintenance())
"
EOF

cat > /etc/systemd/system/bathycat-maintenance.timer << EOF
[Unit]
Description=Run BathyCat maintenance tasks daily
Requires=bathycat-maintenance.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Create status monitoring service
print_status "Creating status monitoring..."

cat > /etc/systemd/system/bathycat-monitor.service << EOF
[Unit]
Description=BathyCat Status Monitor
After=bathycat-imager.service
Requires=bathycat-imager.service

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/venv/bin
ExecStart=/bin/bash -c '
while true; do
    sleep 300  # 5 minutes
    if ! systemctl is-active --quiet bathycat-imager; then
        logger "BathyCat service is not running, attempting restart"
        systemctl restart bathycat-imager
    fi
done
'
Restart=always
RestartSec=60

[Install]
WantedBy=multi-user.target
EOF

# Set up GPS service dependency
print_status "Configuring GPS service..."

# Create GPS service override to ensure proper startup
mkdir -p /etc/systemd/system/gpsd.service.d

cat > /etc/systemd/system/gpsd.service.d/override.conf << EOF
[Unit]
Before=bathycat-imager.service

[Service]
ExecStartPre=/bin/sleep 5
RestartSec=5
Restart=always
EOF

# Create network monitoring for remote access
print_status "Setting up network monitoring..."

cat > /etc/systemd/system/bathycat-network.service << EOF
[Unit]
Description=BathyCat Network Monitor
After=network.target

[Service]
Type=simple
User=$USER
Group=$USER
ExecStart=/bin/bash -c '
WIFI_INTERFACE=wlan0
ETH_INTERFACE=eth0
LOG_FILE=$LOG_DIR/network.log

while true; do
    TIMESTAMP=\$(date "+%Y-%m-%d %H:%M:%S")
    
    # Check WiFi
    if ip link show \$WIFI_INTERFACE >/dev/null 2>&1; then
        WIFI_STATUS=\$(cat /sys/class/net/\$WIFI_INTERFACE/operstate 2>/dev/null || echo "down")
        if [ "\$WIFI_STATUS" = "up" ]; then
            WIFI_IP=\$(ip -4 addr show \$WIFI_INTERFACE | grep -oP "(?<=inet )[\d.]+")
            echo "\$TIMESTAMP WiFi: UP (\$WIFI_IP)" >> \$LOG_FILE
        else
            echo "\$TIMESTAMP WiFi: DOWN" >> \$LOG_FILE
        fi
    fi
    
    # Check Ethernet
    if ip link show \$ETH_INTERFACE >/dev/null 2>&1; then
        ETH_STATUS=\$(cat /sys/class/net/\$ETH_INTERFACE/operstate 2>/dev/null || echo "down")
        if [ "\$ETH_STATUS" = "up" ]; then
            ETH_IP=\$(ip -4 addr show \$ETH_INTERFACE | grep -oP "(?<=inet )[\d.]+")
            echo "\$TIMESTAMP Ethernet: UP (\$ETH_IP)" >> \$LOG_FILE
        else
            echo "\$TIMESTAMP Ethernet: DOWN" >> \$LOG_FILE
        fi
    fi
    
    sleep 60
done
'
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable services
print_status "Enabling services..."

systemctl daemon-reload

# Enable main service
systemctl enable $SERVICE_NAME

# Enable maintenance timer
systemctl enable bathycat-maintenance.timer

# Enable monitoring services
systemctl enable bathycat-monitor.service
systemctl enable bathycat-network.service

# Enable and restart GPS service
systemctl enable gpsd
systemctl restart gpsd

print_success "Services configured and enabled"

# Create convenience scripts
print_status "Creating management scripts..."

# Service management script
cat > $INSTALL_DIR/manage_service.sh << 'EOF'
#!/bin/bash
# BathyCat Service Management Script

SERVICE_NAME="bathycat-imager"

case "$1" in
    start)
        echo "Starting BathyCat services..."
        sudo systemctl start $SERVICE_NAME
        sudo systemctl start bathycat-monitor
        sudo systemctl start bathycat-network
        echo "Services started"
        ;;
    stop)
        echo "Stopping BathyCat services..."
        sudo systemctl stop bathycat-monitor
        sudo systemctl stop bathycat-network
        sudo systemctl stop $SERVICE_NAME
        echo "Services stopped"
        ;;
    restart)
        echo "Restarting BathyCat service..."
        sudo systemctl restart $SERVICE_NAME
        echo "Service restarted"
        ;;
    status)
        echo "=== BathyCat Service Status ==="
        sudo systemctl status $SERVICE_NAME --no-pager -l
        echo
        echo "=== Monitor Service Status ==="
        sudo systemctl status bathycat-monitor --no-pager -l
        echo
        echo "=== Network Service Status ==="
        sudo systemctl status bathycat-network --no-pager -l
        ;;
    logs)
        echo "=== BathyCat Service Logs ==="
        sudo journalctl -u $SERVICE_NAME -f
        ;;
    enable)
        echo "Enabling BathyCat services for auto-start..."
        sudo systemctl enable $SERVICE_NAME
        sudo systemctl enable bathycat-monitor
        sudo systemctl enable bathycat-network
        sudo systemctl enable bathycat-maintenance.timer
        echo "Services enabled"
        ;;
    disable)
        echo "Disabling BathyCat auto-start..."
        sudo systemctl disable $SERVICE_NAME
        sudo systemctl disable bathycat-monitor
        sudo systemctl disable bathycat-network
        sudo systemctl disable bathycat-maintenance.timer
        echo "Services disabled"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|enable|disable}"
        echo
        echo "Commands:"
        echo "  start   - Start all BathyCat services"
        echo "  stop    - Stop all BathyCat services"
        echo "  restart - Restart main BathyCat service"
        echo "  status  - Show service status"
        echo "  logs    - Show live service logs"
        echo "  enable  - Enable auto-start on boot"
        echo "  disable - Disable auto-start"
        exit 1
        ;;
esac
EOF

# System health check script
cat > $INSTALL_DIR/health_check.sh << 'EOF'
#!/bin/bash
# BathyCat System Health Check

echo "========================================"
echo "BathyCat System Health Check"
echo "$(date)"
echo "========================================"

# Service status
echo
echo "=== Service Status ==="
systemctl is-active bathycat-imager && echo "✓ Main service: RUNNING" || echo "✗ Main service: STOPPED"
systemctl is-active bathycat-monitor && echo "✓ Monitor service: RUNNING" || echo "✗ Monitor service: STOPPED"
systemctl is-active gpsd && echo "✓ GPS service: RUNNING" || echo "✗ GPS service: STOPPED"

# Hardware status
echo
echo "=== Hardware Status ==="

# GPS
if [ -e /dev/serial0 ]; then
    echo "✓ GPS serial port: AVAILABLE"
    if timeout 5 gpspipe -r -n 1 >/dev/null 2>&1; then
        echo "✓ GPS data: RECEIVING"
    else
        echo "✗ GPS data: NO SIGNAL"
    fi
else
    echo "✗ GPS serial port: NOT FOUND"
fi

# Camera
if lsusb | grep -qi camera; then
    echo "✓ Camera: DETECTED"
else
    echo "✗ Camera: NOT DETECTED"
fi

# Storage
if mountpoint -q /media/ssd; then
    STORAGE_FREE=$(df -h /media/ssd | awk 'NR==2 {print $4}')
    echo "✓ Storage: MOUNTED ($STORAGE_FREE free)"
else
    echo "✗ Storage: NOT MOUNTED"
fi

# System resources
echo
echo "=== System Resources ==="
CPU_TEMP=$(vcgencmd measure_temp | cut -d= -f2)
echo "CPU Temperature: $CPU_TEMP"

MEM_USAGE=$(free | grep Mem | awk '{printf "%.1f%%", $3/$2 * 100.0}')
echo "Memory Usage: $MEM_USAGE"

LOAD_AVG=$(uptime | awk -F'load average:' '{print $2}')
echo "Load Average:$LOAD_AVG"

# Recent errors
echo
echo "=== Recent Errors ==="
ERROR_COUNT=$(journalctl -u bathycat-imager --since "1 hour ago" | grep -i error | wc -l)
echo "Errors in last hour: $ERROR_COUNT"

if [ $ERROR_COUNT -gt 0 ]; then
    echo "Recent errors:"
    journalctl -u bathycat-imager --since "1 hour ago" | grep -i error | tail -5
fi

echo
echo "========================================"
EOF

# Make scripts executable
chmod +x $INSTALL_DIR/manage_service.sh
chmod +x $INSTALL_DIR/health_check.sh

# Set proper ownership
chown $USER:$USER $INSTALL_DIR/*.sh

print_success "Management scripts created"

# Create desktop shortcuts if desktop environment exists
if [ -d "/home/$USER/Desktop" ]; then
    print_status "Creating desktop shortcuts..."
    
    cat > /home/$USER/Desktop/BathyCat-Status.desktop << EOF
[Desktop Entry]
Name=BathyCat Status
Comment=Check BathyCat System Status
Exec=lxterminal -e $INSTALL_DIR/health_check.sh
Icon=applications-system
Terminal=true
Type=Application
Categories=System;
EOF

    cat > /home/$USER/Desktop/BathyCat-Logs.desktop << EOF
[Desktop Entry]
Name=BathyCat Logs
Comment=View BathyCat Service Logs
Exec=lxterminal -e $INSTALL_DIR/manage_service.sh logs
Icon=utilities-log-viewer
Terminal=true
Type=Application
Categories=System;
EOF

    chmod +x /home/$USER/Desktop/BathyCat-*.desktop
    chown $USER:$USER /home/$USER/Desktop/BathyCat-*.desktop
    
    print_success "Desktop shortcuts created"
fi

print_success "Service setup complete!"

echo
echo "Service Management Commands:"
echo "  Start:   $INSTALL_DIR/manage_service.sh start"
echo "  Stop:    $INSTALL_DIR/manage_service.sh stop"
echo "  Status:  $INSTALL_DIR/manage_service.sh status"
echo "  Logs:    $INSTALL_DIR/manage_service.sh logs"
echo "  Health:  $INSTALL_DIR/health_check.sh"
echo
echo "The services will start automatically on next boot."
echo "To start now: sudo systemctl start bathycat-imager"
