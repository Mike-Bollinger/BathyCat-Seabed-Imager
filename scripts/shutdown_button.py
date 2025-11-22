#!/usr/bin/env python3
"""
Safe Shutdown Button Handler for BathyCat Seabed Imager
======================================================

Provides a two-stage shutdown process with LED feedback to prevent accidental shutdowns.

Hardware:
- Omron B3F-4055 pushbutton connected to GPIO 17
- LEDs on GPIO 18 (Green/Power), 23 (Blue/GPS), 24 (Yellow/Camera), 25 (Red/Error)

Shutdown Logic:
1. First button press: All LEDs blink, wait for second press (10s timeout)
2. Second button press within 10s: Stop service, shutdown system (Green LED only)
3. Timeout without second press: Return to normal operation

Usage:
    sudo python3 shutdown_button.py
    
Or install as systemd service for automatic startup.
"""

import RPi.GPIO as GPIO
import time
import subprocess
import sys
import signal
import logging
from datetime import datetime, timedelta
from typing import Optional
import threading

# GPIO Pin Configuration
SHUTDOWN_BUTTON_PIN = 17
LED_POWER_PIN = 18      # Green
LED_GPS_PIN = 23        # Blue  
LED_CAMERA_PIN = 24     # Yellow
LED_ERROR_PIN = 25      # Red

# Timing Configuration
CONFIRMATION_TIMEOUT = 10.0  # Seconds to wait for second button press
DEBOUNCE_TIME = 0.05        # Button debounce time
BLINK_INTERVAL = 0.5        # LED blink interval during confirmation

# Service Configuration
SERVICE_NAME = "bathyimager"

class ShutdownHandler:
    """Handles safe shutdown process with two-button confirmation."""
    
    def __init__(self):
        """Initialize the shutdown handler."""
        self.logger = self._setup_logging()
        self.confirmation_active = False
        self.confirmation_thread: Optional[threading.Thread] = None
        self.shutdown_in_progress = False
        self.original_led_states = {}
        self.running = True
        
        # Setup GPIO
        self._setup_gpio()
        
        # Setup signal handlers for clean exit
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        self.logger.info("🔴 BathyCat Shutdown Button Handler started")
        self.logger.info(f"   Button: GPIO {SHUTDOWN_BUTTON_PIN}")
        self.logger.info(f"   LEDs: Power:{LED_POWER_PIN}, GPS:{LED_GPS_PIN}, Camera:{LED_CAMERA_PIN}, Error:{LED_ERROR_PIN}")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        logger = logging.getLogger('shutdown_button')
        logger.setLevel(logging.INFO)
        
        # Console handler
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def _setup_gpio(self) -> None:
        """Initialize GPIO pins for button and LEDs."""
        try:
            # Set GPIO mode
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            # Setup shutdown button with internal pull-up resistor
            GPIO.setup(SHUTDOWN_BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            
            # Setup LED pins as outputs
            for pin in [LED_POWER_PIN, LED_GPS_PIN, LED_CAMERA_PIN, LED_ERROR_PIN]:
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, GPIO.LOW)  # Start with LEDs off
            
            # Add button event detection with debouncing
            GPIO.add_event_detect(SHUTDOWN_BUTTON_PIN, GPIO.FALLING, 
                                callback=self._button_pressed, 
                                bouncetime=int(DEBOUNCE_TIME * 1000))
            
            self.logger.info("✅ GPIO initialized successfully")
            
        except Exception as e:
            self.logger.error(f"❌ GPIO setup failed: {e}")
            sys.exit(1)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals cleanly."""
        self.logger.info(f"🛑 Received signal {signum}, shutting down gracefully...")
        self.running = False
        self._cleanup()
        sys.exit(0)
    
    def _button_pressed(self, channel):
        """Handle button press events."""
        if not self.running or self.shutdown_in_progress:
            return
            
        # Small delay for additional debouncing
        time.sleep(DEBOUNCE_TIME)
        
        # Check if button is still pressed (active low)
        if GPIO.input(SHUTDOWN_BUTTON_PIN) != GPIO.LOW:
            return
            
        current_time = datetime.now()
        self.logger.info(f"🔘 Button pressed at {current_time.strftime('%H:%M:%S')}")
        
        if not self.confirmation_active:
            # First button press - start confirmation process
            self._start_confirmation()
        else:
            # Second button press - proceed with shutdown
            self._proceed_with_shutdown()
    
    def _start_confirmation(self) -> None:
        """Start the confirmation process with LED blinking."""
        self.logger.info("⚠️  First button press detected - starting confirmation process")
        self.logger.info(f"⏰ Press button again within {CONFIRMATION_TIMEOUT} seconds to shutdown")
        
        self.confirmation_active = True
        
        # Save current LED states (in case service is controlling them)
        self._save_led_states()
        
        # Start confirmation thread for LED blinking and timeout
        self.confirmation_thread = threading.Thread(target=self._confirmation_process)
        self.confirmation_thread.daemon = True
        self.confirmation_thread.start()
    
    def _save_led_states(self) -> None:
        """Save current LED states to restore later if needed."""
        try:
            for pin in [LED_POWER_PIN, LED_GPS_PIN, LED_CAMERA_PIN, LED_ERROR_PIN]:
                self.original_led_states[pin] = GPIO.input(pin)
        except Exception as e:
            self.logger.warning(f"Could not save LED states: {e}")
    
    def _restore_led_states(self) -> None:
        """Restore original LED states."""
        try:
            for pin, state in self.original_led_states.items():
                GPIO.output(pin, state)
            self.logger.info("🔄 LED states restored to normal operation")
        except Exception as e:
            self.logger.warning(f"Could not restore LED states: {e}")
    
    def _confirmation_process(self) -> None:
        """Handle the confirmation timeout and LED blinking."""
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=CONFIRMATION_TIMEOUT)
        
        try:
            # Blink all LEDs during confirmation period
            led_state = False
            while datetime.now() < end_time and self.confirmation_active and self.running:
                # Toggle all LEDs
                for pin in [LED_POWER_PIN, LED_GPS_PIN, LED_CAMERA_PIN, LED_ERROR_PIN]:
                    GPIO.output(pin, GPIO.HIGH if led_state else GPIO.LOW)
                
                led_state = not led_state
                time.sleep(BLINK_INTERVAL)
            
            # If we exit the loop due to timeout (not shutdown)
            if self.confirmation_active and self.running:
                self._cancel_confirmation()
                
        except Exception as e:
            self.logger.error(f"Error in confirmation process: {e}")
            self._cancel_confirmation()
    
    def _cancel_confirmation(self) -> None:
        """Cancel the confirmation process and return to normal operation."""
        self.logger.info("⏰ Confirmation timeout - returning to normal operation")
        self.confirmation_active = False
        
        # Restore original LED states
        self._restore_led_states()
    
    def _proceed_with_shutdown(self) -> None:
        """Proceed with the shutdown process."""
        if self.shutdown_in_progress:
            return
            
        self.logger.info("🚨 Second button press confirmed - initiating shutdown sequence")
        self.shutdown_in_progress = True
        self.confirmation_active = False
        
        # Start shutdown in separate thread to avoid blocking
        shutdown_thread = threading.Thread(target=self._shutdown_sequence)
        shutdown_thread.daemon = True
        shutdown_thread.start()
    
    def _shutdown_sequence(self) -> None:
        """Execute the complete shutdown sequence."""
        try:
            # Turn off all LEDs except power (green)
            GPIO.output(LED_GPS_PIN, GPIO.LOW)
            GPIO.output(LED_CAMERA_PIN, GPIO.LOW)
            GPIO.output(LED_ERROR_PIN, GPIO.LOW)
            
            # Blink green LED during shutdown
            self._start_power_led_blink()
            
            self.logger.info("🛑 Stopping BathyCat imaging service...")
            
            # Stop the bathyimager service
            try:
                result = subprocess.run(['systemctl', 'stop', SERVICE_NAME], 
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    self.logger.info("✅ BathyCat service stopped successfully")
                else:
                    self.logger.warning(f"⚠️  Service stop returned code {result.returncode}: {result.stderr}")
            except subprocess.TimeoutExpired:
                self.logger.error("❌ Service stop timed out")
            except Exception as e:
                self.logger.error(f"❌ Failed to stop service: {e}")
            
            # Wait a moment for service to fully stop
            self.logger.info("⏳ Waiting for service shutdown to complete...")
            time.sleep(5)
            
            # Sync filesystem
            self.logger.info("💾 Syncing filesystem...")
            try:
                subprocess.run(['sync'], timeout=10)
                self.logger.info("✅ Filesystem sync complete")
            except Exception as e:
                self.logger.warning(f"⚠️  Filesystem sync failed: {e}")
            
            # Final shutdown
            self.logger.info("🔌 Initiating system shutdown...")
            self.logger.info("💤 System will power off in 3 seconds...")
            
            time.sleep(3)
            
            # Turn off power LED before shutdown
            GPIO.output(LED_POWER_PIN, GPIO.LOW)
            
            # Execute shutdown
            subprocess.run(['shutdown', '-h', 'now'], timeout=5)
            
        except Exception as e:
            self.logger.error(f"❌ Shutdown sequence failed: {e}")
            # In case of error, try emergency shutdown
            subprocess.run(['shutdown', '-h', 'now'], timeout=5)
    
    def _start_power_led_blink(self) -> None:
        """Start blinking the power LED in a separate thread."""
        def blink_power_led():
            try:
                while self.shutdown_in_progress and self.running:
                    GPIO.output(LED_POWER_PIN, GPIO.HIGH)
                    time.sleep(0.3)
                    GPIO.output(LED_POWER_PIN, GPIO.LOW)
                    time.sleep(0.3)
            except Exception as e:
                self.logger.error(f"Power LED blink error: {e}")
        
        blink_thread = threading.Thread(target=blink_power_led)
        blink_thread.daemon = True
        blink_thread.start()
    
    def _cleanup(self) -> None:
        """Clean up GPIO and resources."""
        try:
            GPIO.cleanup()
            self.logger.info("🧹 GPIO cleanup completed")
        except Exception as e:
            self.logger.warning(f"GPIO cleanup error: {e}")
    
    def run(self) -> None:
        """Main run loop."""
        try:
            self.logger.info("🔄 Shutdown button handler running...")
            self.logger.info("   Press button once to start shutdown confirmation")
            self.logger.info("   Press button again within 10 seconds to shutdown")
            
            # Keep the main thread alive
            while self.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.logger.info("🛑 Keyboard interrupt received")
        except Exception as e:
            self.logger.error(f"❌ Unexpected error: {e}")
        finally:
            self._cleanup()


def main():
    """Main entry point."""
    try:
        handler = ShutdownHandler()
        handler.run()
    except Exception as e:
        print(f"Fatal error: {e}")
        GPIO.cleanup()
        sys.exit(1)


if __name__ == "__main__":
    main()