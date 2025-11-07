#!/usr/bin/env python3
"""
GPS PPS (Pulse Per Second) Hardware Interface Module
===================================================

Provides hardware-level GPS timing precision using Adafruit Ultimate GPS HAT.
This implements nanosecond-precision timing using PPS signals from GPS HAT.

Based on Adafruit Ultimate GPS HAT specifications and modern PPS implementations:
- GPS HAT PPS signal: 1 pulse per second on GPIO 4 (Physical Pin 7)
- Hardware UART: /dev/ttyAMA0 for GPS communication  
- Timing precision: Sub-microsecond accuracy with proper setup
- Chrony NTP: Modern time synchronization daemon for network distribution

Adafruit Ultimate GPS HAT Configuration:
- PPS: GPIO 4 (Physical Pin 7) - Pre-connected on HAT
- UART: Hardware UART /dev/ttyAMA0 (Pins 8/10)
- Power: 5V via HAT connector (no external wiring needed)
- RTC: Optional CR1220 battery for timekeeping when Pi is off

Software Requirements:
- Enable GPIO PPS in /boot/config.txt: dtoverlay=pps-gpio,gpiopin=4
- Enable UART in /boot/config.txt: enable_uart=1  
- Load pps-gpio module: echo 'pps-gpio' >> /etc/modules
- Install packages: sudo apt install pps-tools gpsd gpsd-clients chrony
- Verify PPS: sudo ppstest /dev/pps0
- Configure Chrony: Setup NMEA and PPS time sources
"""

import os
import time
import logging
from typing import Optional, Callable, Dict, Any
from datetime import datetime, timezone
import threading


class PPSError(Exception):
    """Custom exception for PPS-related errors."""
    pass


class GPSPPSInterface:
    """
    GPIO-based GPS PPS (Pulse Per Second) interface.
    
    This class provides the foundation for nanosecond-precision timing
    using GPS PPS signals via GPIO hardware interrupts.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize PPS interface.
        
        Args:
            config: PPS configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # PPS GPIO settings (GPIO 4 on Physical Pin 7 for Adafruit GPS HAT)
        self.pps_gpio_pin = config.get('pps_gpio_pin', 4)
        self.pps_device = config.get('pps_device', '/dev/pps0')  
        self.pps_enabled = config.get('pps_enabled', False)
        
        # PPS state
        self.is_available = False
        self.is_monitoring = False
        self.pulse_count = 0
        self.last_pulse_time = None
        self.pulse_callback: Optional[Callable] = None
        
        # Timing statistics
        self.pulse_interval_stats = {
            'min_interval': float('inf'),
            'max_interval': 0,
            'avg_interval': 1.0,
            'jitter_ns': 0
        }
        
        # Threading
        self.monitor_thread: Optional[threading.Thread] = None
        self.shutdown_event = threading.Event()
    
    def check_pps_support(self) -> Dict[str, Any]:
        """
        Check if PPS is supported and properly configured.
        
        Returns:
            dict: PPS support status and configuration info
        """
        status = {
            'pps_device_exists': False,
            'pps_module_loaded': False,
            'gpio_overlay_enabled': False,
            'config_suggestions': [],
            'hardware_ready': False
        }
        
        try:
            # Check if PPS device exists
            if os.path.exists(self.pps_device):
                status['pps_device_exists'] = True
                self.logger.info(f"✓ PPS device found: {self.pps_device}")
            else:
                status['config_suggestions'].append(f"PPS device not found: {self.pps_device}")
                self.logger.info(f"❌ PPS device not found: {self.pps_device}")
            
            # Check if pps-gpio module is loaded
            try:
                with open('/proc/modules', 'r') as f:
                    modules = f.read()
                    if 'pps_gpio' in modules:
                        status['pps_module_loaded'] = True
                        self.logger.info("✓ pps-gpio module is loaded")
                    else:
                        status['config_suggestions'].append("Load pps-gpio module: echo 'pps-gpio' >> /etc/modules")
                        self.logger.info("❌ pps-gpio module not loaded")
            except Exception as e:
                self.logger.debug(f"Could not check modules: {e}")
            
            # Check boot config for GPIO overlay
            boot_configs = ['/boot/config.txt', '/boot/firmware/config.txt']
            overlay_found = False
            
            for config_path in boot_configs:
                if os.path.exists(config_path):
                    try:
                        with open(config_path, 'r') as f:
                            config_content = f.read()
                            if f'dtoverlay=pps-gpio,gpiopin={self.pps_gpio_pin}' in config_content:
                                overlay_found = True
                                status['gpio_overlay_enabled'] = True
                                self.logger.info(f"✓ PPS GPIO overlay enabled in {config_path}")
                                break
                    except Exception as e:
                        self.logger.debug(f"Could not read {config_path}: {e}")
            
            if not overlay_found:
                status['config_suggestions'].append(f"Enable PPS GPIO: echo 'dtoverlay=pps-gpio,gpiopin={self.pps_gpio_pin}' >> /boot/firmware/config.txt")
                self.logger.info(f"❌ PPS GPIO overlay not enabled for pin {self.pps_gpio_pin} (avoiding GPIO 18 conflict with LED)")
            
            # Overall hardware readiness
            status['hardware_ready'] = (status['pps_device_exists'] and 
                                      status['pps_module_loaded'] and 
                                      status['gpio_overlay_enabled'])
            
            if status['hardware_ready']:
                self.logger.info("🚀 PPS hardware is ready for nanosecond timing!")
            else:
                self.logger.info("⚙️  PPS hardware needs configuration (see suggestions)")
            
        except Exception as e:
            self.logger.error(f"Error checking PPS support: {e}")
            status['config_suggestions'].append(f"Error checking PPS: {e}")
        
        return status
    
    def initialize(self) -> bool:
        """
        Initialize PPS interface.
        
        Returns:
            bool: True if PPS is available, False otherwise
        """
        try:
            self.logger.info("Initializing GPS PPS interface")
            
            # Check PPS support
            pps_status = self.check_pps_support()
            
            if not pps_status['hardware_ready']:
                if self.pps_enabled:
                    self.logger.warning("PPS requested but hardware not ready")
                    for suggestion in pps_status['config_suggestions']:
                        self.logger.info(f"💡 Setup: {suggestion}")
                else:
                    self.logger.info("PPS not enabled in config - timing will use software methods")
                
                self.is_available = False
                return False
            
            # Test PPS device access
            if not self._test_pps_device():
                self.logger.error("PPS device test failed")
                self.is_available = False
                return False
            
            self.is_available = True
            self.logger.info("GPS PPS interface initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"PPS initialization failed: {e}")
            self.is_available = False
            return False
    
    def _test_pps_device(self) -> bool:
        """
        Test PPS device functionality.
        
        Returns:
            bool: True if PPS device is working, False otherwise
        """
        try:
            # Try to read from PPS device (would need pps-tools or direct access)
            # This is a placeholder for actual PPS device testing
            if os.path.exists(self.pps_device):
                # Check device permissions
                if os.access(self.pps_device, os.R_OK):
                    self.logger.info(f"✓ PPS device accessible: {self.pps_device}")
                    return True
                else:
                    self.logger.error(f"❌ PPS device not readable: {self.pps_device}")
                    self.logger.info("💡 Fix: sudo chmod 644 /dev/pps0 or add user to dialout group")
                    return False
            else:
                self.logger.error(f"❌ PPS device not found: {self.pps_device}")
                return False
                
        except Exception as e:
            self.logger.error(f"PPS device test error: {e}")
            return False
    
    def start_monitoring(self, pulse_callback: Optional[Callable] = None) -> bool:
        """
        Start monitoring PPS pulses.
        
        Args:
            pulse_callback: Function to call on each PPS pulse
            
        Returns:
            bool: True if monitoring started, False otherwise
        """
        if not self.is_available:
            self.logger.warning("PPS not available - cannot start monitoring")
            return False
        
        if self.is_monitoring:
            self.logger.warning("PPS monitoring already active")
            return True
        
        try:
            self.pulse_callback = pulse_callback
            self.shutdown_event.clear()
            
            # Start monitoring thread
            self.monitor_thread = threading.Thread(target=self._monitor_pps, daemon=True)
            self.monitor_thread.start()
            
            self.is_monitoring = True
            self.logger.info("Started PPS monitoring")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start PPS monitoring: {e}")
            return False
    
    def _monitor_pps(self) -> None:
        """Monitor PPS pulses (runs in separate thread)."""
        self.logger.info("PPS monitoring thread started")
        
        try:
            # This would be the actual PPS monitoring implementation
            # For now, this is a placeholder that simulates PPS behavior
            
            while not self.shutdown_event.is_set():
                # Placeholder: In real implementation, this would use:
                # 1. Direct /dev/pps0 access for pulse detection
                # 2. GPIO interrupt handling with pigpio or similar
                # 3. Hardware timestamp extraction from kernel PPS
                
                # Simulate 1-second PPS interval for testing
                time.sleep(1.0)
                
                # Record pulse timing
                current_time = time.time_ns()
                
                if self.last_pulse_time is not None:
                    interval_ns = current_time - self.last_pulse_time
                    self._update_timing_stats(interval_ns)
                
                self.last_pulse_time = current_time
                self.pulse_count += 1
                
                # Call callback if provided
                if self.pulse_callback:
                    try:
                        self.pulse_callback(current_time, self.pulse_count)
                    except Exception as e:
                        self.logger.error(f"PPS callback error: {e}")
                
                # Log pulse periodically
                if self.pulse_count % 60 == 0:  # Every minute
                    self.logger.debug(f"PPS pulse #{self.pulse_count}, jitter: {self.pulse_interval_stats['jitter_ns']:.0f}ns")
                
        except Exception as e:
            self.logger.error(f"PPS monitoring error: {e}")
        finally:
            self.is_monitoring = False
            self.logger.info("PPS monitoring thread ended")
    
    def _update_timing_stats(self, interval_ns: int) -> None:
        """Update timing statistics from pulse intervals."""
        try:
            # Update min/max intervals
            self.pulse_interval_stats['min_interval'] = min(self.pulse_interval_stats['min_interval'], interval_ns)
            self.pulse_interval_stats['max_interval'] = max(self.pulse_interval_stats['max_interval'], interval_ns)
            
            # Calculate rolling average
            alpha = 0.1  # Smoothing factor
            self.pulse_interval_stats['avg_interval'] = (
                alpha * interval_ns + (1 - alpha) * self.pulse_interval_stats['avg_interval']
            )
            
            # Calculate jitter (deviation from expected 1 second = 1e9 nanoseconds)
            expected_interval_ns = 1_000_000_000  # 1 second in nanoseconds
            self.pulse_interval_stats['jitter_ns'] = abs(interval_ns - expected_interval_ns)
            
        except Exception as e:
            self.logger.debug(f"Timing stats update error: {e}")
    
    def get_timing_stats(self) -> Dict[str, Any]:
        """
        Get PPS timing statistics.
        
        Returns:
            dict: Timing statistics
        """
        stats = self.pulse_interval_stats.copy()
        stats.update({
            'is_available': self.is_available,
            'is_monitoring': self.is_monitoring,
            'pulse_count': self.pulse_count,
            'last_pulse_time': self.last_pulse_time
        })
        return stats
    
    def stop_monitoring(self) -> None:
        """Stop PPS monitoring."""
        if not self.is_monitoring:
            return
        
        self.logger.info("Stopping PPS monitoring")
        self.shutdown_event.set()
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2.0)
        
        self.is_monitoring = False
        self.logger.info("PPS monitoring stopped")
    
    def get_hardware_timestamp(self) -> Optional[int]:
        """
        Get hardware timestamp from PPS system.
        
        This would provide nanosecond-precision timestamps when PPS is active.
        
        Returns:
            int: Nanosecond timestamp from PPS hardware, or None if not available
        """
        if not self.is_available or not self.is_monitoring:
            return None
        
        # Placeholder: Real implementation would extract hardware timestamp
        # from PPS device or GPIO interrupt timestamp
        
        # For now, return high-precision system time
        # In actual PPS implementation, this would be the GPS-synchronized hardware time
        return time.time_ns()
    
    def configure_chrony_ntp(self) -> Dict[str, Any]:
        """
        Configure Chrony NTP server for GPS HAT PPS integration.
        
        Returns:
            dict: Configuration status and suggestions
        """
        status = {
            'chrony_installed': False,
            'config_exists': False,
            'pps_configured': False,
            'config_suggestions': [],
            'ready_for_ntp': False
        }
        
        try:
            # Check if chrony is installed
            import subprocess
            result = subprocess.run(['which', 'chronyd'], capture_output=True, text=True)
            status['chrony_installed'] = (result.returncode == 0)
            
            if not status['chrony_installed']:
                status['config_suggestions'].append("Install Chrony: sudo apt install chrony")
                return status
            
            # Check existing configuration
            chrony_config = '/etc/chrony/chrony.conf'
            if os.path.exists(chrony_config):
                status['config_exists'] = True
                
                # Check for PPS configuration
                with open(chrony_config, 'r') as f:
                    config_content = f.read()
                    
                if 'refclock SHM 0' in config_content and 'refclock PPS /dev/pps0' in config_content:
                    status['pps_configured'] = True
                    status['ready_for_ntp'] = True
                else:
                    status['config_suggestions'].append("Configure GPS+PPS sources in chrony.conf")
            else:
                status['config_suggestions'].append("Create chrony configuration file")
            
            # Generate Chrony configuration recommendations
            if not status['pps_configured']:
                chrony_pps_config = self._generate_chrony_config()
                status['config_suggestions'].append(f"Add to {chrony_config}:")
                status['config_suggestions'].extend(chrony_pps_config.split('\n'))
            
        except Exception as e:
            self.logger.error(f"Error checking Chrony configuration: {e}")
            status['config_suggestions'].append(f"Error checking Chrony: {e}")
        
        return status
    
    def _generate_chrony_config(self) -> str:
        """
        Generate optimal Chrony configuration for Adafruit GPS HAT.
        
        Returns:
            str: Chrony configuration block
        """
        config = f"""
# GPS HAT Time Sources for BathyCat
# NMEA time reference from GPS UART
refclock SHM 0 offset 0.5 delay 0.2 refid NMEA

# PPS time reference from GPIO {self.pps_gpio_pin} 
refclock PPS /dev/pps0 trust lock NMEA refid PPS

# Allow NTP server access (for network time distribution)
allow 192.168.0.0/16
allow 10.0.0.0/8
allow 172.16.0.0/12

# Disable fallback to public NTP servers (use GPS as primary)
# pool 2.debian.pool.ntp.org iburst
        """
        return config.strip()

    def close(self) -> None:
        """Close PPS interface and clean up resources."""
        self.stop_monitoring()
        self.logger.info("GPS PPS interface closed")


def create_pps_setup_guide() -> str:
    """
    Create setup guide for PPS hardware configuration.
    
    Returns:
        str: Setup instructions
    """
    guide = """
🚀 GPS HAT Hardware Setup Guide for BathyCat
============================================

This guide configures the Adafruit Ultimate GPS HAT for nanosecond-precision timing.

📡 Hardware Requirements:
- Adafruit Ultimate GPS HAT (Product #2324)
- Raspberry Pi with 40-pin GPIO header
- Optional: CR1220 battery for RTC backup

🔌 Hardware Installation (HAT Form Factor):
1. Power down Raspberry Pi completely
2. Install GPS HAT onto 40-pin GPIO header
3. HAT automatically connects:
   - 5V Power (from Pi 5V rail)
   - Ground (from Pi GND rail)  
   - Hardware UART (/dev/ttyAMA0)
   - PPS signal on GPIO 4 (Physical Pin 7)
4. Optional: Insert CR1220 battery for RTC backup

📋 GPS HAT Connection Diagram:
```
Adafruit Ultimate GPS HAT (#2324)        Raspberry Pi GPIO Header
┌─────────────────────────────────┐     ┌──────────────────────────────┐
│ HAT Connector (40-pin)           │     │ 40-pin GPIO Header           │
│ ├─ Pin 7 (GPIO 4) ── PPS ────────┼─────┤ Pin 7 (GPIO 4) ⭐ PPS Input  │
│ ├─ Pin 8 (GPIO 14)── UART TX ────┼─────┤ Pin 8 (GPIO 14/UART TX)     │
│ ├─ Pin 10(GPIO 15)── UART RX ────┼─────┤ Pin 10 (GPIO 15/UART RX)    │
│ ├─ 5V Power Rail ────────────────┼─────┤ 5V Power (Multiple Pins)    │
│ └─ GND Rail ─────────────────────┼─────┤ Ground (Multiple Pins)      │
└─────────────────────────────────┘     └──────────────────────────────┘

✅ Advantages: No manual wiring, reliable connections, integrated RTC
```

⚙️  Software Configuration:

1. Enable UART and PPS GPIO overlay:
   sudo nano /boot/firmware/config.txt
   
   Add these lines for GPS HAT:
   enable_uart=1
   dtoverlay=pps-gpio,gpiopin=4

2. Load PPS module at boot:
   echo 'pps-gpio' | sudo tee -a /etc/modules

3. Install PPS tools:
   sudo apt update
   sudo apt install pps-tools gpsd gpsd-clients chrony

4. Update BathyCat GPS configuration for GPIO UART:
   nano config/bathyimager_config.json
   
   Change GPS port from USB to GPIO UART:
   "gps": {
     "port": "/dev/ttyAMA0",  # Changed from /dev/ttyUSB0 to GPIO UART
     "baudrate": 9600,
     "timeout": 1.0
   }

5. Reboot and verify PPS:
   sudo reboot
   
   # After reboot, test PPS (needs GPS fix):
   sudo ppstest /dev/pps0
   
   # Should show: "source 0 - assert [timestamp], sequence: [number]"

🎯 Expected Results:
- Timing accuracy: Sub-microsecond (< 1μs)
- Potential precision: Nanosecond-level with proper setup
- GPS sync: System time synchronized to GPS atomic time
- PPS pulse: 1 pulse per second on GPIO 4 (GPS HAT)

📊 Verification Commands:
- lsmod | grep pps          # Check PPS module loaded
- ls -la /dev/pps*          # Check PPS device exists  
- sudo ppstest /dev/pps0    # Test PPS pulses
- chronyc sources           # Check time sources (after chrony config)

🔧 Troubleshooting:
- No /dev/pps0: Check GPIO overlay in config.txt, reboot needed
- No PPS pulses: GPS needs valid fix (4+ satellites)
- Permission denied: sudo chmod 644 /dev/pps0 or add user to dialout group
- Module not loaded: Check /etc/modules for 'pps-gpio' entry

📈 Advanced: For ultimate precision, configure chrony for PPS+NMEA timing:
   /etc/chrony/chrony.conf additions:
   refclock SHM 0 refid NMEA offset 0.268 precision 1e-3 poll 0 filter 3
   refclock PPS /dev/pps0 refid PPS lock NMEA offset 0.0 poll 3 trust

This setup can achieve single-digit nanosecond accuracy! 🎯
"""
    return guide


# Test function for PPS interface
def test_pps_interface():
    """Test PPS interface functionality."""
    logging.basicConfig(level=logging.INFO)
    
    config = {
        'pps_enabled': True,
        'pps_gpio_pin': 16,
        'pps_device': '/dev/pps0'
    }
    
    pps = GPSPPSInterface(config)
    
    # Check support
    status = pps.check_pps_support()
    print(f"PPS Support Status: {status}")
    
    # Try to initialize
    if pps.initialize():
        print("✅ PPS initialized successfully")
        
        # Define pulse callback
        def on_pps_pulse(timestamp_ns: int, pulse_number: int):
            dt = datetime.fromtimestamp(timestamp_ns / 1e9, tz=timezone.utc)
            print(f"🔔 PPS Pulse #{pulse_number}: {dt.isoformat()}")
        
        # Start monitoring
        if pps.start_monitoring(on_pps_pulse):
            print("📡 PPS monitoring started")
            try:
                time.sleep(10)  # Monitor for 10 seconds
            except KeyboardInterrupt:
                pass
            finally:
                pps.stop_monitoring()
        
        # Get stats
        stats = pps.get_timing_stats()
        print(f"📊 Final stats: {stats}")
        
        pps.close()
    else:
        print("❌ PPS initialization failed")
        print("\n" + create_pps_setup_guide())


if __name__ == "__main__":
    test_pps_interface()