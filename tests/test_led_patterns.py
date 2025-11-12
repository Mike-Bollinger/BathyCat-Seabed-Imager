#!/usr/bin/env python3
"""
LED Pattern Test Script for BathyCat Imager
Tests all status LEDs with various patterns to verify GPIO connections.

LED Assignments (as documented in GPS HAT wiring):
- Power LED: GPIO 18 (Physical Pin 12) - Green
- GPS LED: GPIO 23 (Physical Pin 16) - Blue  
- Camera LED: GPIO 24 (Physical Pin 18) - Yellow
- Error LED: GPIO 25 (Physical Pin 22) - Red

Test Modes:
1) Pattern Tests - Automated sequence of LED patterns
2) Manual Control - Interactive LED control until user exits
3) Both - Run patterns first, then manual control

Usage: sudo python3 test_led_patterns.py
"""

import time
import sys
try:
    import RPi.GPIO as GPIO
except ImportError:
    print("ERROR: RPi.GPIO not available. This script must run on a Raspberry Pi.")
    sys.exit(1)

# LED GPIO pin assignments
LED_PINS = {
    'power': 18,    # Green - Power status
    'gps': 23,      # Blue - GPS status  
    'camera': 24,   # Yellow - Camera status
    'error': 25     # Red - Error status
}

def setup_leds():
    """Initialize GPIO pins for LED control."""
    print("Setting up GPIO pins for LED control...")
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    for name, pin in LED_PINS.items():
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)  # Start with all LEDs off
    
    print(f"Configured LEDs: {', '.join(LED_PINS.keys())}")

def all_leds_on(duration=5):
    """Turn all LEDs on for specified duration."""
    print(f"\n🔆 Testing: All LEDs ON for {duration} seconds...")
    
    for name, pin in LED_PINS.items():
        GPIO.output(pin, GPIO.HIGH)
        print(f"  ✓ {name.upper()} LED (GPIO {pin}) - ON")
    
    print(f"Keeping all LEDs on for {duration} seconds...")
    time.sleep(duration)
    
    # Turn all off
    for pin in LED_PINS.values():
        GPIO.output(pin, GPIO.LOW)
    print("  All LEDs turned OFF")

def individual_led_test():
    """Test each LED individually."""
    print(f"\n🔍 Testing: Individual LED verification...")
    
    for name, pin in LED_PINS.items():
        print(f"  Testing {name.upper()} LED (GPIO {pin})...")
        GPIO.output(pin, GPIO.HIGH)
        time.sleep(1)
        GPIO.output(pin, GPIO.LOW)
        time.sleep(0.5)

def blink_pattern_all(cycles=5, on_time=0.5, off_time=0.5):
    """Blink all LEDs together in unison."""
    print(f"\n💫 Testing: Synchronized blink pattern ({cycles} cycles)...")
    
    for cycle in range(cycles):
        print(f"  Blink cycle {cycle + 1}/{cycles}")
        
        # All on
        for pin in LED_PINS.values():
            GPIO.output(pin, GPIO.HIGH)
        time.sleep(on_time)
        
        # All off
        for pin in LED_PINS.values():
            GPIO.output(pin, GPIO.LOW)
        time.sleep(off_time)

def chase_pattern(cycles=3):
    """Chase pattern - LEDs light up in sequence."""
    print(f"\n🏃 Testing: LED chase pattern ({cycles} cycles)...")
    
    led_sequence = list(LED_PINS.items())
    
    for cycle in range(cycles):
        print(f"  Chase cycle {cycle + 1}/{cycles}")
        
        for name, pin in led_sequence:
            GPIO.output(pin, GPIO.HIGH)
            print(f"    {name.upper()} LED on")
            time.sleep(0.3)
            GPIO.output(pin, GPIO.LOW)
            time.sleep(0.1)

def rapid_blink_test():
    """Fast blink test to check response time."""
    print(f"\n⚡ Testing: Rapid blink test (10 Hz for 3 seconds)...")
    
    start_time = time.time()
    while time.time() - start_time < 3:
        # All on
        for pin in LED_PINS.values():
            GPIO.output(pin, GPIO.HIGH)
        time.sleep(0.05)  # 50ms on
        
        # All off  
        for pin in LED_PINS.values():
            GPIO.output(pin, GPIO.LOW)
        time.sleep(0.05)  # 50ms off

def status_simulation():
    """Simulate real BathyCat status patterns."""
    print(f"\n🚢 Testing: BathyCat status simulation...")
    
    # Boot sequence
    print("  Simulating boot sequence...")
    GPIO.output(LED_PINS['power'], GPIO.HIGH)  # Power on
    time.sleep(1)
    
    print("  GPS acquiring fix...")
    for i in range(5):
        GPIO.output(LED_PINS['gps'], GPIO.HIGH)
        time.sleep(0.2)
        GPIO.output(LED_PINS['gps'], GPIO.LOW)
        time.sleep(0.2)
    GPIO.output(LED_PINS['gps'], GPIO.HIGH)  # GPS locked
    time.sleep(1)
    
    print("  Camera initializing...")
    GPIO.output(LED_PINS['camera'], GPIO.HIGH)
    time.sleep(2)
    
    print("  Normal operation - all systems OK")
    time.sleep(2)
    
    print("  Simulating error condition...")
    GPIO.output(LED_PINS['error'], GPIO.HIGH)
    # Blink power LED to show error state  
    for i in range(3):
        GPIO.output(LED_PINS['power'], GPIO.LOW)
        time.sleep(0.3)
        GPIO.output(LED_PINS['power'], GPIO.HIGH)
        time.sleep(0.3)
    
    # Clear error
    GPIO.output(LED_PINS['error'], GPIO.LOW)
    print("  Error cleared")
    time.sleep(1)

def cleanup():
    """Turn off all LEDs and cleanup GPIO."""
    print("\n🧹 Cleaning up...")
    for name, pin in LED_PINS.items():
        GPIO.output(pin, GPIO.LOW)
    GPIO.cleanup()
    print("All LEDs turned off, GPIO cleaned up.")

def manual_led_control():
    """Manual LED control - turn on LEDs until user signals to turn off."""
    print(f"\n🔧 Manual LED Control Mode")
    print("=" * 40)
    print("Available commands:")
    print("  'all' - Turn all LEDs on")
    print("  'off' - Turn all LEDs off") 
    print("  'power', 'gps', 'camera', 'error' - Toggle individual LED")
    print("  'status' - Show current LED states")
    print("  'quit' or 'exit' - Exit manual mode")
    print("=" * 40)
    
    led_states = {name: False for name in LED_PINS.keys()}
    
    while True:
        try:
            command = input("\nLED Command (type 'help' for options): ").strip().lower()
            
            if command in ['quit', 'exit', 'q']:
                print("Exiting manual LED control...")
                break
                
            elif command == 'help':
                print("\nCommands: all, off, power, gps, camera, error, status, quit")
                
            elif command == 'all':
                print("🔆 Turning ALL LEDs ON")
                for name, pin in LED_PINS.items():
                    GPIO.output(pin, GPIO.HIGH)
                    led_states[name] = True
                    print(f"  ✓ {name.upper()} LED ON")
                    
            elif command == 'off':
                print("⚫ Turning ALL LEDs OFF")
                for name, pin in LED_PINS.items():
                    GPIO.output(pin, GPIO.LOW)
                    led_states[name] = False
                    print(f"  ○ {name.upper()} LED OFF")
                    
            elif command in LED_PINS:
                pin = LED_PINS[command]
                current_state = led_states[command]
                new_state = not current_state
                
                GPIO.output(pin, GPIO.HIGH if new_state else GPIO.LOW)
                led_states[command] = new_state
                status = "ON" if new_state else "OFF"
                symbol = "✓" if new_state else "○"
                print(f"  {symbol} {command.upper()} LED (GPIO {pin}) - {status}")
                
            elif command == 'status':
                print("\n📊 Current LED States:")
                for name, pin in LED_PINS.items():
                    state = led_states[name]
                    symbol = "🟢" if state else "⚫"
                    status = "ON" if state else "OFF"
                    print(f"  {symbol} {name.upper()} LED (GPIO {pin}): {status}")
                    
            else:
                print(f"❌ Unknown command: '{command}'. Type 'help' for options.")
                
        except KeyboardInterrupt:
            print("\n\n⚠️ Manual control interrupted")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Turn off all LEDs before exiting
    print("\nTurning off all LEDs before exit...")
    for pin in LED_PINS.values():
        GPIO.output(pin, GPIO.LOW)

def run_pattern_tests():
    """Run the full pattern test sequence."""
    print("\n🎭 Running Pattern Test Sequence...")
    print("=" * 40)
    
    # Test sequence
    all_leds_on(5)
    individual_led_test()
    blink_pattern_all(5)
    chase_pattern(3)
    rapid_blink_test()
    status_simulation()
    
    print("\n" + "=" * 50) 
    print("✅ LED Pattern Test Complete!")
    print("If all LEDs responded correctly, your wiring is good.")
    print("=" * 50)

def main():
    """Main test sequence with user options."""
    print("=" * 60)
    print("BathyCat Imager LED Pattern Test")
    print("=" * 60)
    print("Testing LED connections for GPS HAT setup:")
    for name, pin in LED_PINS.items():
        print(f"  {name.upper()} LED: GPIO {pin}")
    print("=" * 60)
    
    print("\nSelect test mode:")
    print("1) Pattern Tests - Automated LED pattern sequence")
    print("2) Manual Control - Control LEDs interactively")
    print("3) Both - Run patterns first, then manual control")
    
    try:
        setup_leds()
        
        while True:
            try:
                choice = input("\nEnter your choice (1, 2, 3, or 'q' to quit): ").strip()
                
                if choice.lower() in ['q', 'quit', 'exit']:
                    print("Exiting LED test...")
                    break
                    
                elif choice == '1':
                    run_pattern_tests()
                    break
                    
                elif choice == '2':
                    manual_led_control()
                    break
                    
                elif choice == '3':
                    run_pattern_tests()
                    print("\n" + "=" * 60)
                    print("Now switching to Manual Control Mode...")
                    manual_led_control()
                    break
                    
                else:
                    print("❌ Invalid choice. Please enter 1, 2, 3, or 'q'.")
                    
            except KeyboardInterrupt:
                print("\n\n⚠️ Test interrupted by user")
                break
        
    except Exception as e:
        print(f"\n❌ Error during LED test: {e}")
    finally:
        cleanup()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print(__doc__)
        sys.exit(0)
        
    print("Starting LED test in 3 seconds...")
    print("Press Ctrl+C to stop at any time")
    time.sleep(3)
    main()