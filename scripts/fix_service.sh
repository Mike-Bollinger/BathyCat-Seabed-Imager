#!/bin/bash
#
# BathyImager Service Fix Script
# =============================
#
# Fixes systemd service configuration issues
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo "🔧 BathyImager Service Fix"
echo "========================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "This script must be run as root (use sudo)"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "src/main.py" ]; then
    print_error "Please run this from the BathyCat-Seabed-Imager directory"
    exit 1
fi

PROJECT_DIR="$(pwd)"
SERVICE_USER="bathyimager"

print_status "Current project directory: $PROJECT_DIR"

# Stop service if running
print_status "Stopping bathyimager service..."
systemctl stop bathyimager 2>/dev/null || true

# Check current service file
if [ -f "/etc/systemd/system/bathyimager.service" ]; then
    print_status "Current service configuration:"
    grep -E "(WorkingDirectory|ExecStart|User)" /etc/systemd/system/bathyimager.service | sed 's/^/  /'
    
    # Check for old paths
    if grep -q "/opt/bathyimager" /etc/systemd/system/bathyimager.service; then
        print_warning "Service still using old /opt/bathyimager paths!"
        NEEDS_UPDATE=true
    else
        NEEDS_UPDATE=false
    fi
else
    print_warning "No service file found at /etc/systemd/system/bathyimager.service"
    NEEDS_UPDATE=true
fi

# Update service file if needed
if [ "$NEEDS_UPDATE" = true ]; then
    print_status "Installing updated service file..."
    cp scripts/bathyimager.service /etc/systemd/system/
    print_success "Service file updated"
fi

# Ensure run script exists and is executable
if [ ! -f "$PROJECT_DIR/run_bathyimager.sh" ]; then
    print_status "Creating run script..."
    cat > "$PROJECT_DIR/run_bathyimager.sh" << EOF
#!/bin/bash
cd "\$(dirname "\$0")/src"
exec ../venv/bin/python main.py --config ../config/bathyimager_config.json "\$@"
EOF
    chmod +x "$PROJECT_DIR/run_bathyimager.sh"
    print_success "Run script created"
fi

# Fix ownership
print_status "Fixing ownership..."
chown -R $SERVICE_USER:$SERVICE_USER "$PROJECT_DIR"
print_success "Ownership fixed"

# Reload systemd
print_status "Reloading systemd configuration..."
systemctl daemon-reload
print_success "Systemd reloaded"

# Test service file
print_status "Testing service configuration..."
if systemctl cat bathyimager >/dev/null 2>&1; then
    print_success "Service file valid"
    
    # Show current configuration
    echo "Current service configuration:"
    systemctl cat bathyimager | grep -E "(WorkingDirectory|ExecStart|User)" | sed 's/^/  /'
else
    print_error "Service file invalid!"
    exit 1
fi

# Check if user exists
if id "$SERVICE_USER" >/dev/null 2>&1; then
    print_success "Service user '$SERVICE_USER' exists"
else
    print_error "Service user '$SERVICE_USER' does not exist!"
    print_status "Run the full install script to create the user"
    exit 1
fi

# Check configuration file
CONFIG_FILE="$PROJECT_DIR/config/bathyimager_config.json"
if [ -f "$CONFIG_FILE" ]; then
    print_success "Configuration file exists: $CONFIG_FILE"
    
    # Validate JSON
    if python3 -c "import json; json.load(open('$CONFIG_FILE'))" 2>/dev/null; then
        print_success "Configuration file is valid JSON"
    else
        print_error "Configuration file has JSON errors!"
        python3 -c "import json; json.load(open('$CONFIG_FILE'))" 2>&1 | sed 's/^/  /'
    fi
else
    print_warning "Configuration file not found: $CONFIG_FILE"
    print_status "Create it with: cp config/bathyimager_config.json.example config/bathyimager_config.json"
fi

# Try to start service
print_status "Attempting to start service..."
if systemctl start bathyimager; then
    print_success "Service started successfully!"
    
    # Check status
    sleep 2
    if systemctl is-active bathyimager >/dev/null 2>&1; then
        print_success "Service is running"
        systemctl status bathyimager --no-pager -l
    else
        print_error "Service failed to start"
        echo "Logs:"
        journalctl -u bathyimager --no-pager -l | tail -10
    fi
else
    print_error "Failed to start service"
    echo "Check logs with: sudo journalctl -u bathyimager -f"
fi

print_status "Service fix complete!"
echo
echo "Useful commands:"
echo "  sudo systemctl status bathyimager    - Check service status"
echo "  sudo journalctl -u bathyimager -f   - View live logs"
echo "  sudo systemctl restart bathyimager  - Restart service"