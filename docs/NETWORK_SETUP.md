# BathyCat Network Configuration Guide

This guide explains how to configure dual Ethernet + WiFi connectivity for the BathyCat Seabed Imager system running on Raspberry Pi.

## Overview

The BathyCat system supports simultaneous Ethernet and WiFi connections with automatic failover:

- **Ethernet (eth0)**: Primary connection with highest priority (metric 100)
- **WiFi (wlan0)**: Secondary/backup connection with lower priority (metric 300)
- **Automatic Routing**: Traffic prefers Ethernet when available, falls back to WiFi
- **Seamless Failover**: Maintains connectivity if one interface fails

## Quick Setup

### 1. Run the Network Setup Script

```bash
# Copy configuration files and setup dual networking
sudo ./scripts/network_setup.sh
```

### 2. Configure WiFi Credentials

```bash
# Interactive WiFi configuration
sudo ./scripts/wifi_config.sh
```

### 3. Check Status

```bash
# View current network status
./scripts/network_status.sh
```

### 4. Test Connectivity

```bash
# Test both interfaces
./scripts/network_test.sh
```

## Manual Configuration

### dhcpcd Configuration

Edit `/etc/dhcpcd.conf`:

```bash
sudo nano /etc/dhcpcd.conf
```

Add BathyCat dual network configuration:

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

## Troubleshooting

### Common Issues

#### 1. Both Interfaces Down
```bash
# Check if interfaces exist
ip link show eth0
ip link show wlan0

# Bring up interfaces manually
sudo ip link set eth0 up
sudo ip link set wlan0 up

# Restart networking
sudo systemctl restart dhcpcd
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

# Disable NetworkManager (recommended for BathyCat)
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

The BathyCat imaging service automatically works with dual networking:

1. **Service Start**: Checks network connectivity before starting imaging
2. **Runtime**: Monitors network health for GPS sync and data transfer
3. **Failover**: Continues operation if primary interface fails
4. **Logging**: Records network events in service logs

### Service Integration

```bash
# Check BathyCat service network status
sudo systemctl status bathyimager

# View BathyCat logs with network events
journalctl -u bathyimager | grep -i network

# Test BathyCat with specific interface
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

## Support

For additional help:

1. **Check Logs**: `journalctl -u dhcpcd -u wpa_supplicant@wlan0 -f`
2. **Run Diagnostics**: `./scripts/network_status.sh`
3. **Test Connectivity**: `./scripts/network_test.sh`
4. **View Configuration**: `./scripts/wifi_config.sh` (option 6)

## Summary

The BathyCat dual networking setup provides:

- ✅ **Redundant Connectivity**: Ethernet + WiFi for reliability
- ✅ **Automatic Priority**: Ethernet preferred, WiFi as backup  
- ✅ **Seamless Failover**: Maintains connectivity during transitions
- ✅ **Easy Management**: Scripts for setup, monitoring, and testing
- ✅ **Flexible Configuration**: Supports DHCP and static IP setups

This configuration ensures the BathyCat system maintains reliable network connectivity for GPS synchronization, data transfer, and remote management even in challenging marine environments.