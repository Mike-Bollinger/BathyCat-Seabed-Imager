# BathyCat Seabed Imager Network Configuration Guide

Complete network setup guide for the BathyCat Seabed Imager system with dual connectivity and intelligent failover.

## Overview

The BathyCat system provides robust network connectivity essential for GPS time synchronization, remote monitoring, and system updates:

- **🔌 Ethernet (eth0)**: Primary connection with highest priority (metric 100)
- **📶 WiFi (wlan0)**: Secondary/backup connection with lower priority (metric 300)
- **🔄 Automatic Routing**: Traffic prefers Ethernet when available, seamlessly falls back to WiFi
- **⚡ Seamless Failover**: Maintains connectivity during cable disconnections or WiFi outages
- **🛠️ Diagnostic Tools**: Built-in network testing and troubleshooting framework

## ⚠️ No Internet on Pi? - Ethernet Internet Sharing Solution

If your Raspberry Pi can't get online to download packages, use this method to share internet through Ethernet cable connection.

### Method 1: Windows Internet Connection Sharing (ICS)

**Step 1: Enable Internet Connection Sharing on Windows**

1. **Open Network Connections:**
   - Press `Win + R`, type `ncpa.cpl`, press Enter
   - OR: Control Panel → Network and Internet → Network Connections

2. **Configure Internet Connection Sharing:**
   - Right-click your **WiFi/Internet adapter** (the one with internet)
   - Select **Properties**
   - Go to **Sharing** tab
   - Check "**Allow other network users to connect through this computer's Internet connection**"
   - In the dropdown, select your **Ethernet adapter** (connected to Pi)
   - Click **OK**

3. **Verify Ethernet Adapter Settings:**
   - Your Ethernet adapter should automatically get IP: `192.168.137.1`
   - If not, set it manually:

**Step 2: Manual IP Configuration (if needed)**

Open PowerShell as Administrator and run:
```powershell
# Set static IP on Ethernet adapter connected to Pi
netsh interface ip set address "Ethernet" static 192.168.137.1 255.255.255.0

# Verify the configuration
netsh interface ip show config "Ethernet"
```

**Step 3: Configure Raspberry Pi**

Connect to your Pi via SSH (using the shared connection) or with keyboard/monitor:

```bash
# Method A: Use the automated script (recommended)
cd ~/BathyCat-Seabed-Imager
sudo chmod +x scripts/setup_shared_internet.sh
sudo ./scripts/setup_shared_internet.sh

# Method B: Manual configuration
# Configure Pi to use Windows computer as gateway
sudo ip addr add 192.168.137.100/24 dev eth0
sudo ip route add default via 192.168.137.1 dev eth0

# Set DNS servers
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
echo "nameserver 1.1.1.1" | sudo tee -a /etc/resolv.conf

# Test connectivity
ping -c 3 google.com
```

**Step 4: Install Required Packages**

Once internet is working:
```bash
# Update package lists
sudo apt update

# Install network packages
sudo apt install -y dhcpcd5 wpasupplicant wireless-tools net-tools iproute2 dnsutils

# Install any missing packages for BathyImager
sudo apt install -y libopenblas-dev i2c-tools

# Enable network services
sudo systemctl enable dhcpcd
sudo systemctl enable wpa_supplicant@wlan0
```

**Step 5: Configure Permanent Network Setup**

```bash
# Now run the full network setup
sudo ./scripts/network_setup.sh

# Configure WiFi for future use
sudo ./scripts/wifi_config.sh
```

### Method 2: Windows Command Line Setup

**Alternative PowerShell method for advanced users:**

```powershell
# Enable Internet Connection Sharing via PowerShell
# Note: Replace "Wi-Fi" with your internet adapter name
# Replace "Ethernet" with your Ethernet adapter name

# Get adapter names
Get-NetAdapter | Select-Object Name, InterfaceDescription

# Enable ICS (requires manual setup via GUI for most reliable results)
# But you can set the IP manually:
New-NetIPAddress -InterfaceAlias "Ethernet" -IPAddress 192.168.137.1 -PrefixLength 24

# Enable IP forwarding
Set-NetIPInterface -InterfaceAlias "Ethernet" -Forwarding Enabled
```

### Method 3: Linux/macOS Internet Sharing

**For Linux systems:**
```bash
# Enable IP forwarding
echo 1 | sudo tee /proc/sys/net/ipv4/ip_forward

# Configure Ethernet interface  
sudo ip addr add 192.168.137.1/24 dev eth0
sudo ip link set eth0 up

# Set up NAT (replace wlan0 with your internet interface)
sudo iptables -t nat -A POSTROUTING -o wlan0 -j MASQUERADE
sudo iptables -A FORWARD -i eth0 -o wlan0 -j ACCEPT
sudo iptables -A FORWARD -i wlan0 -o eth0 -m state --state RELATED,ESTABLISHED -j ACCEPT

# Start DHCP server (optional)
sudo dnsmasq --interface=eth0 --dhcp-range=192.168.137.100,192.168.137.200,12h
```

**For macOS:**
```bash
# System Preferences → Sharing → Internet Sharing
# Select Wi-Fi as source, Ethernet as destination
# Or use command line:
sudo sysctl -w net.inet.ip.forwarding=1
sudo pfctl -e -f /etc/pf.conf
```

### Troubleshooting Internet Sharing

#### Windows Issues

**Issue: "Internet Connection Sharing is already enabled"**
```cmd
# Disable and re-enable ICS
# Go to Network Connections → Right-click WiFi adapter → Properties
# → Sharing tab → Uncheck sharing → Apply → Check again → Apply
```

**Issue: Wrong IP address on Ethernet adapter**
```powershell
# Remove existing IP and set correct one
netsh interface ip delete address "Ethernet" addr=192.168.137.1
netsh interface ip set address "Ethernet" static 192.168.137.1 255.255.255.0
```

**Issue: Pi can't reach internet**
```bash
# On Pi, check routing
ip route list

# Should see: default via 192.168.137.1 dev eth0
# If not, add it:
sudo ip route add default via 192.168.137.1 dev eth0

# Check if you can reach the gateway
ping 192.168.137.1

# Check DNS
nslookup google.com
```

#### Pi-side Issues

**Issue: Can't get IP address**
```bash
# Check Ethernet link
ip link show eth0

# Manually configure if DHCP fails
sudo ip addr add 192.168.137.100/24 dev eth0
sudo ip link set eth0 up
```

**Issue: DNS not working**
```bash
# Check DNS configuration
cat /etc/resolv.conf

# Manually set DNS if needed
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
echo "nameserver 192.168.137.1" | sudo tee -a /etc/resolv.conf
```

**Issue: Connection works but packages won't download**
```bash
# Check if apt can reach repositories
sudo apt update

# If it fails, try different mirrors or check proxy settings
sudo nano /etc/apt/apt.conf.d/90curtin-aptproxy
# Remove any proxy settings if present
```

### Network Sharing Verification

**On Windows (verify sharing is working):**
```cmd
# Check network configuration
ipconfig /all

# Look for Ethernet adapter with IP 192.168.137.1
# Check internet connection sharing is enabled

# Test connectivity to Pi
ping 192.168.137.100
```

**On Pi (verify internet access):**
```bash
# Check IP configuration
ip addr show eth0

# Should show: 192.168.137.100/24

# Check routing
ip route list

# Should show: default via 192.168.137.1 dev eth0

# Test connectivity
ping -c 3 192.168.137.1  # Gateway (Windows PC)
ping -c 3 8.8.8.8        # Internet
ping -c 3 google.com     # DNS resolution
```

### Automated Recovery Script

Create a recovery script for easy reconnection:

```bash
# Save as ~/reconnect_shared_internet.sh
#!/bin/bash
echo "Reconnecting to shared internet..."

# Configure interface
sudo ip addr flush dev eth0
sudo ip addr add 192.168.137.100/24 dev eth0
sudo ip link set eth0 up

# Set default route
sudo ip route del default 2>/dev/null
sudo ip route add default via 192.168.137.1 dev eth0

# Configure DNS
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
echo "nameserver 1.1.1.1" | sudo tee -a /etc/resolv.conf

# Test connectivity
if ping -c 1 google.com >/dev/null 2>&1; then
    echo "✅ Internet connectivity restored!"
else
    echo "❌ Internet connectivity failed"
fi

# Make executable: chmod +x ~/reconnect_shared_internet.sh
```

### Performance Considerations

**Network Speed:**
- Ethernet sharing typically provides better performance than WiFi hotspots
- Expected speeds: 100Mbps (Fast Ethernet) or 1Gbps (Gigabit Ethernet)
- Actual speed limited by Windows computer's internet connection

**Latency:**
- Adds minimal latency (usually <1ms) compared to direct connection
- Much better than WiFi hotspot solutions

**Reliability:**
- Very stable connection method
- Less prone to interference than wireless solutions
- Good for extended package downloads and system updates

### When to Use Internet Sharing

**Ideal Scenarios:**
- Initial Pi setup without WiFi configured
- Downloading large package updates
- Installing development tools and dependencies
- Systems in areas with poor WiFi coverage
- Laboratory or workshop environments

**After Setup:**
Once your Pi has proper network configuration, you can disconnect the shared connection and use the configured Ethernet/WiFi setup for normal operation.

---

## Quick Setup

### 1. Make Scripts Executable (Required First Step)

```bash
# Navigate to the BathyImager directory
cd /opt/bathyimager

# Make all network scripts executable
sudo chmod +x scripts/network_setup.sh
sudo chmod +x scripts/wifi_config.sh
sudo chmod +x scripts/network_status.sh
sudo chmod +x scripts/network_test.sh
```

### 2. Configure Network (Offline Method)

Since you need network connectivity to get online, use offline mode to skip package downloads:

```bash
# Configure network without downloading packages (offline mode)
sudo ./scripts/network_setup.sh --offline

# This will:
# - Copy configuration templates to system locations
# - Skip all package installations
# - Set up dual network configuration
# - Leave you ready to connect and install packages later

# OR configure completely manually (see Manual Configuration section below)
```

### 3. Configure WiFi Credentials

```bash
# Interactive WiFi configuration
sudo ./scripts/wifi_config.sh
```

### 4. Get Online and Install Missing Packages

You have multiple options to get the required packages:

#### Option A: Use Automated Setup Script (Recommended)

The BathyCat system includes an automated internet sharing setup script:

**On Windows (your computer):**
```powershell
# The BathyCat system can guide you through this process
# See the Internet Sharing section below for complete automation
```

**On Raspberry Pi:**
```bash
# Use the automated setup script for internet sharing
sudo chmod +x scripts/setup_shared_internet.sh
sudo ./scripts/setup_shared_internet.sh

# This script will:
# - Configure Pi to use Windows computer as gateway (192.168.137.1)
# - Set appropriate DNS servers
# - Test connectivity
# - Install required packages automatically
# - Verify network functionality
```

#### Option B: Manual Internet Sharing Setup

**On Windows (your computer):**
```cmd
# Enable internet connection sharing on your main internet adapter
# Go to: Network Connections → Right-click your WiFi/Internet adapter → Properties
# → Sharing tab → Check "Allow other network users to connect"
# → Select the Ethernet adapter connected to Pi

# Set static IP on Ethernet adapter to Pi:
netsh interface ip set address "Ethernet" static 192.168.137.1 255.255.255.0
```

**On Raspberry Pi:**
```bash
# Set temporary network config to use your computer as gateway
sudo ip addr add 192.168.137.100/24 dev eth0
sudo ip route add default via 192.168.137.1 dev eth0
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf

# Test connectivity
ping -c 3 google.com

# Install packages
sudo apt update
sudo apt install -y dhcpcd5 wpasupplicant wireless-tools net-tools iproute2 dnsutils

# Enable services
sudo systemctl enable dhcpcd
sudo systemctl enable wpa_supplicant@wlan0

# Test network setup
python3 tests/network_test.sh
```

#### Option B: Include Packages in Offline Transfer

Download packages on a computer with internet and transfer them:

**On computer with internet:**
```bash
# Create package directory
mkdir bathyimager-packages
cd bathyimager-packages

# Download packages (adjust for your Pi's architecture)
apt download dhcpcd5 wpasupplicant wireless-tools net-tools iproute2 dnsutils

# Transfer to Pi along with your project files
```

**On Raspberry Pi:**
```bash
# Install downloaded packages
cd /path/to/bathyimager-packages
sudo dpkg -i *.deb

# Fix any dependency issues
sudo apt --fix-broken install
```

### 5. Restart Network Services

```bash
# Apply network configuration
sudo systemctl restart dhcpcd
sudo systemctl restart wpa_supplicant@wlan0
```

### 6. Check Status

```bash
# View current network status
./scripts/network_status.sh
```

### 7. Test Connectivity

```bash
# Test both interfaces
./scripts/network_test.sh
```

## Manual Configuration

> **Note**: Use this method when setting up without internet connectivity or when the automated scripts are not available.

### dhcpcd Configuration

Edit `/etc/dhcpcd.conf`:

```bash
sudo nano /etc/dhcpcd.conf
```

Add BathyImager dual network configuration:

```conf
# Ethernet Interface (Primary - Lower metric = higher priority)
interface eth0
metric 100
# Optional: Static IP fallback
#static ip_address=192.168.1.100/24
#static routers=192.168.1.1
#static domain_name_servers=8.8.8.8 1.1.1.1

# WiFi Interface (Secondary - Higher metric = lower priority) 
interface wlan0
metric 300
```

### WiFi Configuration

Edit `/etc/wpa_supplicant/wpa_supplicant.conf`:

```bash
sudo nano /etc/wpa_supplicant/wpa_supplicant.conf
```

Add your WiFi networks:

```conf
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=US

# Primary WiFi Network
network={
    ssid="YOUR_WIFI_SSID"
    psk="YOUR_WIFI_PASSWORD"
    priority=5
    proto=RSN WPA
    key_mgmt=WPA-PSK
    pairwise=CCMP TKIP
    group=CCMP TKIP
}
```

### Restart Services

```bash
sudo systemctl restart dhcpcd
sudo systemctl restart wpa_supplicant@wlan0
```

## Network Priority Explanation

### Metric Values
- **Lower metric = Higher priority**
- **dhcpcd default**: 200 + interface_index + 100 (for wireless)
- **Our configuration**:
  - Ethernet: metric 100 (highest priority)
  - WiFi: metric 300 (lower priority)

### Routing Behavior
1. **Both Connected**: Traffic routes through Ethernet
2. **Ethernet Only**: Traffic routes through Ethernet
3. **WiFi Only**: Traffic routes through WiFi
4. **Ethernet Fails**: Traffic automatically switches to WiFi
5. **Ethernet Returns**: Traffic switches back to Ethernet

## Verification Commands

### Check Interface Status
```bash
# Show interface states
ip link show

# Show IP addresses
ip addr show

# Show routing table
ip route list
```

### Test Specific Interface
```bash
# Test Ethernet connectivity
ping -I eth0 -c 3 8.8.8.8

# Test WiFi connectivity  
ping -I wlan0 -c 3 8.8.8.8
```

### Monitor Route Selection
```bash
# See which interface is used for internet
ip route get 8.8.8.8

# Trace route to see path
traceroute 8.8.8.8
```

### WiFi Status
```bash
# Check WiFi connection
wpa_cli -i wlan0 status

# Scan for networks
wpa_cli -i wlan0 scan
wpa_cli -i wlan0 scan_results
```

## Network Scenarios

### Scenario 1: Ethernet + WiFi Both Connected

**Expected Behavior:**
- Both interfaces have IP addresses
- Default route through Ethernet (lower metric)
- WiFi ready as backup

**Verification:**
```bash
# Should show eth0 with lower metric as default
ip route list | grep default

# Both should work, but eth0 preferred for internet
ping -I eth0 -c 3 8.8.8.8
ping -I wlan0 -c 3 8.8.8.8
```

### Scenario 2: Ethernet Disconnected

**Expected Behavior:**
- WiFi becomes primary route
- Internet connectivity maintained through WiFi
- Automatic failover

**Verification:**
```bash
# Should show only wlan0 default route
ip route list | grep default

# Internet should work via WiFi
ping -c 3 8.8.8.8
```

### Scenario 3: Ethernet Reconnected

**Expected Behavior:**
- Ethernet route restored as primary
- WiFi remains connected as backup
- Traffic switches back to Ethernet

**Verification:**
```bash
# Should show eth0 as primary default route again
ip route list | grep default
```

## Network Diagnostics and Testing

### Automated Network Diagnostics
```bash
# Comprehensive network testing and analysis
python3 tests/troubleshoot.py --network

# Dedicated network connectivity testing
./tests/network_test.sh

# Continuous network monitoring
./tests/network_test.sh --continuous

# Network performance analysis
python3 tests/performance_analyzer.py --network-analysis
```

### Network Status and Health Checks
```bash
# Quick network configuration overview
./scripts/network_status.sh

# Full network connectivity testing
./tests/network_test.sh --full

# System health with network focus
python3 tests/system_health_check.py --network-focus

# Test network interface performance
python3 tests/performance_analyzer.py --network-benchmark
```

### Network Failover Testing
```bash
# Test automatic failover behavior
python3 tests/network_test.sh --failover-test

# Monitor network stability during failover
python3 tests/performance_analyzer.py --monitor --network

# Validate dual network configuration
python3 tests/troubleshoot.py --component network
```

## Troubleshooting

### Automated Troubleshooting (Start Here)
```bash
# First step: Run automated network diagnostics
python3 tests/troubleshoot.py --network

# This will automatically:
# ✅ Check interface status and configuration
# ✅ Test connectivity on both Ethernet and WiFi
# ✅ Verify routing and DNS configuration
# ✅ Test failover behavior
# ✅ Provide specific recommendations for any issues found
```

### Common Issues

#### 1. Both Interfaces Down
```bash
# Use automated diagnostics first
python3 tests/troubleshoot.py --component network

# Manual checks
ip link show eth0
ip link show wlan0

# Bring up interfaces manually
sudo ip link set eth0 up
sudo ip link set wlan0 up

# Restart networking
sudo systemctl restart dhcpcd

# Verify with network test
./tests/network_test.sh
```

#### 2. WiFi Not Connecting
```bash
# Check wpa_supplicant status
sudo systemctl status wpa_supplicant@wlan0

# Check WiFi configuration
sudo wpa_cli -i wlan0 status

# Restart WiFi service
sudo systemctl restart wpa_supplicant@wlan0

# Interactive WiFi setup
sudo ./scripts/wifi_config.sh
```

#### 3. Wrong Interface Priority
```bash
# Check current metrics
ip route list | grep default

# Verify dhcpcd configuration
grep -A5 "interface eth0\|interface wlan0" /etc/dhcpcd.conf

# Restart dhcpcd to apply changes
sudo systemctl restart dhcpcd
```

#### 4. No Internet on Either Interface
```bash
# Check if DNS is working
nslookup google.com

# Check if routing is correct
ip route get 8.8.8.8

# Test direct IP (bypass DNS)
ping -c 3 8.8.8.8

# Check for conflicting network managers
sudo systemctl status NetworkManager
```

#### 5. Interface Getting Wrong IP
```bash
# Release and renew DHCP
sudo dhclient -r eth0
sudo dhclient eth0

# Or restart dhcpcd
sudo systemctl restart dhcpcd

# Check DHCP logs
journalctl -u dhcpcd -f
```

### Network Manager Conflicts

If NetworkManager is running, it may conflict with dhcpcd:

```bash
# Check if NetworkManager is active
systemctl is-active NetworkManager

# Disable NetworkManager (recommended for BathyImager)
sudo systemctl disable NetworkManager
sudo systemctl stop NetworkManager

# Ensure dhcpcd is enabled
sudo systemctl enable dhcpcd
sudo systemctl start dhcpcd
```

### Service Status Check

```bash
# Check all network services
sudo systemctl status dhcpcd
sudo systemctl status wpa_supplicant@wlan0

# View network logs
journalctl -u dhcpcd -n 20
journalctl -u wpa_supplicant@wlan0 -n 20
```

## Performance Optimization

### Interface-Specific Testing

Test bandwidth on each interface:

```bash
# Test Ethernet speed
iperf3 -c speedtest.server.com --bind 192.168.1.100  # eth0 IP

# Test WiFi speed  
iperf3 -c speedtest.server.com --bind 192.168.1.101  # wlan0 IP
```

### Connection Monitoring

Monitor connection health:

```bash
# Continuous monitoring
./scripts/network_test.sh --continuous

# Interface-specific monitoring
./scripts/network_test.sh --interface eth0
./scripts/network_test.sh --interface wlan0
```

## Security Considerations

### WiFi Security
- Use WPA2 or WPA3 when possible
- Avoid WEP networks (insecure)
- Use strong, unique passwords
- Regularly update network credentials

### Network Isolation
- Consider VLANs for network segmentation
- Use firewall rules if needed
- Monitor connection logs regularly

### Monitoring
```bash
# Monitor network activity
sudo iftop -i eth0
sudo iftop -i wlan0

# View connection logs
journalctl -u dhcpcd -f
journalctl -u wpa_supplicant@wlan0 -f
```

## Integration with BathyCat Service

The BathyImager imaging service automatically works with dual networking:

1. **Service Start**: Checks network connectivity before starting imaging
2. **Runtime**: Monitors network health for GPS sync and data transfer
3. **Failover**: Continues operation if primary interface fails
4. **Logging**: Records network events in service logs

### Service Integration

```bash
# Check BathyImager service network status
sudo systemctl status bathyimager

# View BathyImager logs with network events
journalctl -u bathyimager | grep -i network

# Test BathyImager with specific interface
# (modify service config if needed for testing)
```

## Configuration Files Reference

### dhcpcd.conf Location
- **File**: `/etc/dhcpcd.conf`
- **Backup**: Created automatically by setup script
- **Template**: `config/dhcpcd.conf`

### wpa_supplicant.conf Location  
- **File**: `/etc/wpa_supplicant/wpa_supplicant.conf`
- **Backup**: Created automatically by setup script
- **Template**: `config/wpa_supplicant.conf`

### Script Locations
- **Setup**: `scripts/network_setup.sh`
- **Status**: `scripts/network_status.sh`  
- **Testing**: `scripts/network_test.sh`
- **WiFi Config**: `scripts/wifi_config.sh`

## Advanced Configuration

### Static IP Configuration

For laboratory or fixed deployment scenarios:

```conf
# Static Ethernet configuration
interface eth0
static ip_address=192.168.1.50/24
static routers=192.168.1.1
static domain_name_servers=8.8.8.8 1.1.1.1
metric 100

# Static WiFi configuration  
interface wlan0
static ip_address=192.168.1.51/24
static routers=192.168.1.1
static domain_name_servers=8.8.8.8 1.1.1.1
metric 300
```

### Multiple WiFi Networks

Configure multiple WiFi networks with priorities:

```conf
# High priority network
network={
    ssid="Lab_WiFi"
    psk="lab_password"
    priority=10
}

# Medium priority network
network={
    ssid="Office_WiFi" 
    psk="office_password"
    priority=5
}

# Low priority backup
network={
    ssid="Mobile_Hotspot"
    psk="mobile_password"
    priority=1
}
```

### Enterprise WiFi

For corporate environments with WPA-Enterprise:

```conf
network={
    ssid="Corporate_WiFi"
    proto=RSN
    key_mgmt=WPA-EAP
    eap=PEAP
    identity="username"
    password="password"
    phase2="auth=MSCHAPV2"
    priority=8
}
```

## Troubleshooting Checklist

When network issues occur, follow this checklist:

### 1. Basic Connectivity
- [ ] Check cable connections (Ethernet)
- [ ] Verify WiFi signal strength
- [ ] Check interface link status (`ip link show`)
- [ ] Verify IP address assignment (`ip addr show`)

### 2. Service Status
- [ ] dhcpcd service running (`systemctl status dhcpcd`)
- [ ] wpa_supplicant service running (`systemctl status wpa_supplicant@wlan0`)
- [ ] No conflicting NetworkManager (`systemctl is-active NetworkManager`)

### 3. Configuration Files
- [ ] dhcpcd.conf has correct metrics
- [ ] wpa_supplicant.conf has correct credentials
- [ ] File permissions are correct (600 for wpa_supplicant.conf)

### 4. Routing
- [ ] Default routes exist (`ip route list`)
- [ ] Correct metric priorities (Ethernet < WiFi)
- [ ] Can ping gateway (`ping gateway_ip`)

### 5. DNS and Internet
- [ ] DNS resolution working (`nslookup google.com`)
- [ ] Internet connectivity (`ping 8.8.8.8`)
- [ ] Correct route selection (`ip route get 8.8.8.8`)

## Support and Diagnostics

### Automated Problem Resolution
```bash
# Start with comprehensive network diagnostics
python3 tests/troubleshoot.py --network

# For ongoing issues, run continuous monitoring
python3 tests/performance_analyzer.py --monitor --network --duration 300

# Generate detailed network report
python3 tests/system_health_check.py --network-report
```

### Manual Diagnostics
1. **System Logs**: `journalctl -u dhcpcd -u wpa_supplicant@wlan0 -f`
2. **Network Status**: `./scripts/network_status.sh`
3. **Connectivity Tests**: `./tests/network_test.sh --full`
4. **Configuration Review**: `./scripts/wifi_config.sh` (option 6)
5. **Performance Analysis**: `python3 tests/performance_analyzer.py --network-benchmark`

### Getting Help
- **Run diagnostics first**: Always run `python3 tests/troubleshoot.py --network` and include output with support requests
- **GitHub Issues**: https://github.com/Mike-Bollinger/BathyCat-Seabed-Imager/issues
- **Documentation**: Check main README.md and troubleshooting guide
- **Log Analysis**: Network logs are automatically included in date-stamped logs at `/media/usb/bathyimager/logs/YYYYMMDD/`

## Summary

The BathyCat dual networking setup provides:

- ✅ **Redundant Connectivity**: Ethernet + WiFi for maximum reliability
- ✅ **Intelligent Priority**: Ethernet preferred, WiFi as seamless backup  
- ✅ **Automatic Failover**: Maintains connectivity during cable disconnections
- ✅ **Comprehensive Testing**: Built-in diagnostic and performance tools
- ✅ **Easy Management**: Automated scripts for setup, monitoring, and troubleshooting
- ✅ **Flexible Configuration**: Supports DHCP, static IP, and enterprise WiFi setups
- ✅ **Production Ready**: Tested for marine deployment environments

This configuration ensures the BathyCat system maintains reliable network connectivity for:
- **GPS Time Synchronization**: Critical for accurate timestamping
- **Remote Monitoring**: SSH access and system status checking  
- **System Updates**: Automatic or manual software updates
- **Data Transfer**: Backup and analysis of captured imagery
- **Troubleshooting**: Remote diagnostics and support

The network system is designed to handle challenging marine environments where connectivity may be intermittent, ensuring continuous operation of the seabed imaging system.