#!/usr/bin/env python3
"""
LED Status Module for BathyCat Seabed Imager
===========================================

Provides visual feedback using LEDs for system status including GPS fix,
camera operation, error conditions, and general system health.

Features:
- Multiple LED indicators for different system states
- Configurable GPIO pin assignments
- Blinking patterns for different statuses
- Thread-safe LED control
- Error condition signaling
- Power-on self test
"""

import time
import threading
import logging
from typing import Dict, Any, Optional
from enum import Enum


# GPIO initialization - deferred to avoid import-time errors
GPIO = None
GPIO_AVAILABLE = False

def _init_gpio():
    """Initialize GPIO module with error handling."""
    global GPIO, GPIO_AVAILABLE
    
    if GPIO is not None:
        return GPIO_AVAILABLE
        
    try:
        import RPi.GPIO as _GPIO
        GPIO = _GPIO
        GPIO_AVAILABLE = True
    except (ImportError, RuntimeError, Exception) as e:
        GPIO_AVAILABLE = False
        # Mock GPIO for testing on non-Pi systems or when RPi.GPIO fails
        class MockGPIO:
            BCM = 'BCM'
            OUT = 'OUT'
            HIGH = 1
            LOW = 0
            
            @staticmethod
            def setmode(mode): pass
            @staticmethod
            def setup(pin, mode): pass
            @staticmethod
            def output(pin, state): pass
            @staticmethod
            def cleanup(): pass
        
        GPIO = MockGPIO()
    
    return GPIO_AVAILABLE


class LEDState(Enum):
    """LED state definitions."""
    OFF = 0
    ON = 1
    SLOW_BLINK = 2
    FAST_BLINK = 3
    HEARTBEAT = 4


class LEDIndicator:
    """Individual LED controller."""
    
    def __init__(self, pin: int, name: str):
        """
        Initialize LED indicator.
        
        Args:
            pin: GPIO pin number
            name: LED name for logging
        """
        self.pin = pin
        self.name = name
        self.logger = logging.getLogger(__name__)
        self.state = LEDState.OFF
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Initialize GPIO pin
        try:
            GPIO.setup(self.pin, GPIO.OUT)
            GPIO.output(self.pin, GPIO.LOW)
        except Exception as e:
            self.logger.warning(f"GPIO setup failed for {name} LED (pin {pin}): {e}")
    
    def set_state(self, state: LEDState) -> None:
        """
        Set LED state and pattern.
        
        Args:
            state: LED state to set
        """
        if self.state == state:
            return  # Already in this state
        
        self.logger.debug(f"LED {self.name}: {self.state.name} -> {state.name}")
        
        # Stop current pattern
        self._stop_pattern()
        
        self.state = state
        
        # Start new pattern
        if state == LEDState.OFF:
            self._set_led(False)
        elif state == LEDState.ON:
            self._set_led(True)
        else:
            self._start_pattern()
    
    def _start_pattern(self) -> None:
        """Start LED blinking pattern in background thread."""
        if self.is_running:
            return
        
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._pattern_loop, daemon=True)
        self.thread.start()
        self.is_running = True
    
    def _stop_pattern(self) -> None:
        """Stop LED blinking pattern."""
        if self.is_running:
            self.stop_event.set()
            if self.thread:
                self.thread.join(timeout=1.0)
            self.is_running = False
    
    def _pattern_loop(self) -> None:
        """Main pattern loop (runs in background thread)."""
        while not self.stop_event.is_set():
            if self.state == LEDState.SLOW_BLINK:
                self._set_led(True)
                if self.stop_event.wait(0.5):
                    break
                self._set_led(False)
                if self.stop_event.wait(0.5):
                    break
            
            elif self.state == LEDState.FAST_BLINK:
                self._set_led(True)
                if self.stop_event.wait(0.1):
                    break
                self._set_led(False)
                if self.stop_event.wait(0.1):
                    break
            
            elif self.state == LEDState.HEARTBEAT:
                # Double blink pattern
                self._set_led(True)
                if self.stop_event.wait(0.1):
                    break
                self._set_led(False)
                if self.stop_event.wait(0.1):
                    break
                self._set_led(True)
                if self.stop_event.wait(0.1):
                    break
                self._set_led(False)
                if self.stop_event.wait(0.7):
                    break
            
            else:
                break  # Unknown state
        
        # Ensure LED is off when pattern stops
        self._set_led(False)
    
    def _set_led(self, on: bool) -> None:
        """Set LED hardware state."""
        try:
            GPIO.output(self.pin, GPIO.HIGH if on else GPIO.LOW)
        except Exception as e:
            self.logger.debug(f"LED {self.name} output error: {e}")
    
    def cleanup(self) -> None:
        """Clean up LED resources."""
        self._stop_pattern()
        self._set_led(False)


class LEDManager:
    """
    LED status management for BathyCat system.
    
    Manages multiple LEDs for different system status indicators.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize LED manager with configuration.
        
        Args:
            config: LED configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.is_initialized = False
        
        # LED pin assignments from config
        self.led_pins = {
            'power': config.get('led_power_pin', 18),
            'gps': config.get('led_gps_pin', 23),
            'camera': config.get('led_camera_pin', 24),
            'error': config.get('led_error_pin', 25)
        }
        
        # LED instances
        self.leds: Dict[str, LEDIndicator] = {}
        
        # System state tracking
        self.system_states = {
            'power_on': False,
            'gps_fix': False,
            'camera_active': False,
            'error_condition': False,
            'capturing': False
        }
    
    def initialize(self) -> bool:
        """
        Initialize LED system.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            # Check if LEDs are disabled in config
            if self.config.get('leds_enabled', True) is False:
                self.logger.info("LEDs disabled by configuration")
                return True
                
            # Initialize GPIO with error handling
            gpio_available = _init_gpio()
            
            if not gpio_available:
                self.logger.warning("GPIO not available - LED functionality disabled")
                return True  # Don't fail completely
            
            self.logger.info("Initializing LED system")
            
            # Set GPIO mode
            GPIO.setmode(GPIO.BCM)
            
            # Initialize LED instances
            for led_name, pin in self.led_pins.items():
                self.leds[led_name] = LEDIndicator(pin, led_name)
            
            # Run power-on self test
            self._power_on_test()
            
            # Set initial states
            self.set_power_on(True)
            
            self.is_initialized = True
            self.logger.info("LED system initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"LED initialization failed: {e}")
            return False
    
    def _power_on_test(self) -> None:
        """Run power-on self test - briefly light all LEDs."""
        self.logger.info("Running LED self-test")
        
        try:
            # Turn on all LEDs
            for led in self.leds.values():
                led.set_state(LEDState.ON)
            
            time.sleep(1.0)
            
            # Turn off all LEDs
            for led in self.leds.values():
                led.set_state(LEDState.OFF)
            
            self.logger.info("LED self-test completed")
            
        except Exception as e:
            self.logger.warning(f"LED self-test error: {e}")
    
    def set_power_on(self, on: bool) -> None:
        """
        Set power indicator state.
        
        Args:
            on: True if system is powered on, False otherwise
        """
        self.system_states['power_on'] = on
        
        if 'power' in self.leds:
            if on:
                self.leds['power'].set_state(LEDState.HEARTBEAT)
            else:
                self.leds['power'].set_state(LEDState.OFF)
    
    def set_gps_status(self, has_fix: bool, acquiring: bool = False) -> None:
        """
        Set GPS status indicator.
        
        Args:
            has_fix: True if GPS has valid fix, False otherwise
            acquiring: True if currently acquiring fix, False otherwise
        """
        self.system_states['gps_fix'] = has_fix
        
        if 'gps' in self.leds:
            if has_fix:
                self.leds['gps'].set_state(LEDState.ON)
            elif acquiring:
                self.leds['gps'].set_state(LEDState.SLOW_BLINK)
            else:
                self.leds['gps'].set_state(LEDState.OFF)
    
    def set_camera_status(self, active: bool, capturing: bool = False) -> None:
        """
        Set camera status indicator.
        
        Args:
            active: True if camera is active, False otherwise
            capturing: True if currently capturing image, False otherwise
        """
        self.system_states['camera_active'] = active
        self.system_states['capturing'] = capturing
        
        if 'camera' in self.leds:
            if capturing:
                self.leds['camera'].set_state(LEDState.FAST_BLINK)
            elif active:
                self.leds['camera'].set_state(LEDState.ON)
            else:
                self.leds['camera'].set_state(LEDState.OFF)
    
    def set_error_condition(self, error: bool, critical: bool = False) -> None:
        """
        Set error condition indicator.
        
        Args:
            error: True if error condition exists, False otherwise
            critical: True if error is critical, False for warnings
        """
        self.system_states['error_condition'] = error
        
        if 'error' in self.leds:
            if error:
                if critical:
                    self.leds['error'].set_state(LEDState.FAST_BLINK)
                else:
                    self.leds['error'].set_state(LEDState.SLOW_BLINK)
            else:
                self.leds['error'].set_state(LEDState.OFF)
    
    def signal_capture(self) -> None:
        """Signal that an image capture occurred (brief flash)."""
        if 'camera' in self.leds:
            # Briefly flash camera LED
            threading.Thread(target=self._capture_flash, daemon=True).start()
    
    def _capture_flash(self) -> None:
        """Brief flash for image capture indication."""
        try:
            if 'camera' in self.leds:
                original_state = self.leds['camera'].state
                self.leds['camera'].set_state(LEDState.ON)
                time.sleep(0.05)  # 50ms flash
                self.leds['camera'].set_state(original_state)
        except Exception as e:
            self.logger.debug(f"Capture flash error: {e}")
    
    def update_status(self, camera_healthy: bool, gps_healthy: bool, 
                     storage_healthy: bool, has_gps_fix: bool = False) -> None:
        """
        Update all LED statuses based on system health.
        
        Args:
            camera_healthy: Camera system health
            gps_healthy: GPS system health
            storage_healthy: Storage system health
            has_gps_fix: Whether GPS has valid fix
        """
        # Update GPS status
        if gps_healthy:
            self.set_gps_status(has_gps_fix, acquiring=not has_gps_fix)
        else:
            self.set_gps_status(False, acquiring=False)
        
        # Update camera status
        self.set_camera_status(camera_healthy)
        
        # Update error status
        error_condition = not (camera_healthy and gps_healthy and storage_healthy)
        critical_error = not storage_healthy  # Storage failure is critical
        self.set_error_condition(error_condition, critical_error)
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get LED system status.
        
        Returns:
            dict: LED status information
        """
        return {
            'initialized': self.is_initialized,
            'gpio_available': GPIO_AVAILABLE,
            'led_pins': self.led_pins,
            'system_states': self.system_states.copy(),
            'led_states': {name: led.state.name for name, led in self.leds.items()}
        }
    
    def is_healthy(self) -> bool:
        """
        Check LED system health.
        
        Returns:
            bool: True if LED system is healthy, False otherwise
        """
        return self.is_initialized
    
    def all_off(self) -> None:
        """Turn off all LEDs."""
        for led in self.leds.values():
            led.set_state(LEDState.OFF)
    
    def cleanup(self) -> None:
        """Clean up LED system resources."""
        self.logger.info("Cleaning up LED system")
        
        # Turn off all LEDs
        self.all_off()
        
        # Clean up individual LEDs
        for led in self.leds.values():
            led.cleanup()
        
        # Clean up GPIO if available
        if GPIO_AVAILABLE:
            try:
                GPIO.cleanup()
            except Exception as e:
                self.logger.debug(f"GPIO cleanup error: {e}")


def test_leds(config: Dict[str, Any]) -> bool:
    """
    Test LED functionality with given configuration.
    
    Args:
        config: LED configuration dictionary
        
    Returns:
        bool: True if LED test passed, False otherwise
    """
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        led_manager = LEDManager(config)
        
        if not led_manager.initialize():
            logger.error("LED initialization failed")
            return False
        
        logger.info("Testing LED patterns...")
        
        # Test power LED
        led_manager.set_power_on(True)
        time.sleep(2)
        
        # Test GPS states
        led_manager.set_gps_status(False, acquiring=True)  # Acquiring
        time.sleep(2)
        led_manager.set_gps_status(True)  # Has fix
        time.sleep(2)
        
        # Test camera states
        led_manager.set_camera_status(True)  # Active
        time.sleep(1)
        led_manager.signal_capture()  # Capture flash
        time.sleep(1)
        led_manager.set_camera_status(True, capturing=True)  # Capturing
        time.sleep(2)
        
        # Test error states
        led_manager.set_error_condition(True, critical=False)  # Warning
        time.sleep(2)
        led_manager.set_error_condition(True, critical=True)  # Critical
        time.sleep(2)
        led_manager.set_error_condition(False)  # Clear error
        
        # Test status update
        led_manager.update_status(
            camera_healthy=True,
            gps_healthy=True,
            storage_healthy=True,
            has_gps_fix=True
        )
        time.sleep(2)
        
        # Get status info
        status = led_manager.get_status()
        logger.info(f"LED status: {status}")
        
        # Test health check
        health = led_manager.is_healthy()
        logger.info(f"LED health: {health}")
        
        # Clean up
        led_manager.cleanup()
        
        logger.info("LED test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"LED test failed: {e}")
        return False


if __name__ == "__main__":
    # Test configuration
    test_config = {
        'led_power_pin': 18,
        'led_gps_pin': 23,
        'led_camera_pin': 24,
        'led_error_pin': 25
    }
    
    success = test_leds(test_config)
    exit(0 if success else 1)