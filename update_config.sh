#!/bin/bash
echo "Updating BathyCat configuration..."

# Copy updated config to system location  
sudo cp config/bathycat_config.json /etc/bathycat/config.json

echo "Configuration updated successfully!"
echo ""
echo "Key changes:"
echo "- GPS port set to /dev/ttyUSB0 (your detected GPS device)"
echo "- GPS fix requirement disabled for testing"
echo ""
echo "Now run: ./scripts/start_capture.sh"
