#!/usr/bin/env python3
"""
Camera LED Troubleshooting Script
Specifically tests GPIO 24 (Camera LED) for the BathyCat Imager

This script helps diagnose why the Camera LED (Yellow, GPIO 24) might not be lighting.
"""

import time
import sys
try:
    import RPi.GPIO as GPIO
except ImportError:
    print("ERROR: RPi.GPIO not available. This script must run on a Raspberry Pi.")
    sys.exit(1)

# Camera LED specific settings
CAMERA_LED_PIN = 24  # GPIO 24 (Physical Pin 18)

def setup_gpio():
    """Setup GPIO for camera LED testing."""
    print("Setting up GPIO for Camera LED troubleshooting...")
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(CAMERA_LED_PIN, GPIO.OUT)
    GPIO.output(CAMERA_LED_PIN, GPIO.LOW)  # Start OFF
    print(f"Camera LED configured on GPIO {CAMERA_LED_PIN} (Physical Pin 18)")

def test_camera_led():
    """Comprehensive Camera LED test."""
    print("=" * 50)
    print("🟡 CAMERA LED (GPIO 24) TROUBLESHOOTING")
    print("=" * 50)
    
    print(f"\n1. Testing basic ON/OFF...")
    
    # Test 1: Basic on/off
    print("   Turning Camera LED ON...")
    GPIO.output(CAMERA_LED_PIN, GPIO.HIGH)
    input("   Press ENTER if you see the Camera LED lit (or continue if not)")
    
    print("   Turning Camera LED OFF...")
    GPIO.output(CAMERA_LED_PIN, GPIO.LOW)
    input("   Press ENTER if the Camera LED turned off (or continue if not)")
    
    # Test 2: Slow blink
    print(f"\n2. Testing slow blink pattern (5 blinks)...")
    for i in range(5):
        print(f"   Blink {i+1}/5")
        GPIO.output(CAMERA_LED_PIN, GPIO.HIGH)
        time.sleep(1)
        GPIO.output(CAMERA_LED_PIN, GPIO.LOW)
        time.sleep(1)
    
    # Test 3: Fast blink
    print(f"\n3. Testing fast blink pattern (10 blinks)...")
    for i in range(10):
        GPIO.output(CAMERA_LED_PIN, GPIO.HIGH)
        time.sleep(0.2)
        GPIO.output(CAMERA_LED_PIN, GPIO.LOW)
        time.sleep(0.2)
    
    # Test 4: Extended on
    print(f"\n4. Testing extended ON (10 seconds)...")
    print("   Camera LED should be ON for 10 seconds...")
    GPIO.output(CAMERA_LED_PIN, GPIO.HIGH)
    time.sleep(10)
    GPIO.output(CAMERA_LED_PIN, GPIO.LOW)
    
    print(f"\n5. Final state test...")
    response = input("   Would you like to keep the LED ON for manual inspection? (y/n): ")
    if response.lower().startswith('y'):
        GPIO.output(CAMERA_LED_PIN, GPIO.HIGH)
        input("   Camera LED is ON. Check your wiring. Press ENTER to turn off and exit...")
        GPIO.output(CAMERA_LED_PIN, GPIO.LOW)

def diagnose_issues():
    """Provide diagnostic information."""
    print("\n" + "=" * 50)
    print("🔍 DIAGNOSTIC INFORMATION")
    print("=" * 50)
    print("Camera LED Expected Configuration:")
    print(f"  - GPIO Pin: {CAMERA_LED_PIN}")
    print("  - Physical Pin: 18")
    print("  - LED Color: Yellow")
    print("  - Current Limiting Resistor: 220Ω")
    print("  - Voltage: 3.3V from Pi")
    
    print("\nTroubleshooting Steps:")
    print("1. Check Physical Connections:")
    print("   - GPIO 24 → 220Ω resistor → LED positive (longer leg)")
    print("   - LED negative (shorter leg) → Ground (Pin 20, 25, 30, 34, or 39)")
    
    print("\n2. Check LED Polarity:")
    print("   - Longer leg = Positive (Anode) → connects to resistor from GPIO")
    print("   - Shorter leg = Negative (Cathode) → connects to Ground")
    
    print("\n3. Test LED with Battery:")
    print("   - Connect 3V battery: + to resistor → LED + → LED - to battery -")
    print("   - If LED doesn't light with battery, LED may be damaged")
    
    print("\n4. Check Resistor Value:")
    print("   - Use 220Ω resistor (Red-Red-Brown-Gold bands)")
    print("   - Too high resistance = dim/no light")
    print("   - No resistor = LED may burn out")
    
    print("\n5. Check GPIO Pin:")
    print("   - Verify Physical Pin 18 = GPIO 24")
    print("   - Check for loose connections")
    print("   - Try different jumper wires")
    
    print("\n6. Alternative Test:")
    print("   - Try connecting to a different GPIO pin temporarily")
    print("   - If works on other pin, GPIO 24 may have an issue")

def cleanup():
    """Cleanup GPIO."""
    GPIO.output(CAMERA_LED_PIN, GPIO.LOW)
    GPIO.cleanup()
    print("\nGPIO cleaned up. Camera LED turned off.")

def main():
    """Main troubleshooting sequence."""
    print("Camera LED (GPIO 24) Troubleshooting Tool")
    print("This will help diagnose your yellow Camera LED issue")
    
    try:
        setup_gpio()
        test_camera_led()
        diagnose_issues()
        
        print("\n" + "=" * 50)
        print("✅ Camera LED troubleshooting complete!")
        print("If the LED still doesn't work, check the diagnostic steps above.")
        print("=" * 50)
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Troubleshooting interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during troubleshooting: {e}")
    finally:
        cleanup()

if __name__ == "__main__":
    main()