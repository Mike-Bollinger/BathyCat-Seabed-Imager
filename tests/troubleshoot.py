#!/usr/bin/env python3
"""
BathyCat Master Troubleshooting Tool
====================================

This script provides a unified interface to all BathyCat troubleshooting tools.
It can run comprehensive system analysis or specific component tests.

Features:
- System health overview
- Component-specific diagnostics
- Performance analysis
- Configuration validation
- Automated fix recommendations
- Detailed reporting

Usage:
    python3 troubleshoot.py                    # Full system check
    python3 troubleshoot.py --component gps    # GPS-specific tests
    python3 troubleshoot.py --component camera # Camera-specific tests
    python3 troubleshoot.py --performance      # Performance analysis only
    python3 troubleshoot.py --quick            # Quick health check
"""

import argparse
import sys
import os
import subprocess
from datetime import datetime
from pathlib import Path

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def print_header(title):
    """Print formatted header."""
    print(f"\n🔧 {title}")
    print("=" * (len(title) + 3))

def run_system_health():
    """Run comprehensive system health check."""
    print_header("BATHYCAT SYSTEM HEALTH CHECK")
    try:
        result = subprocess.run([sys.executable, "system_health_check.py"], 
                              cwd=os.path.dirname(__file__), capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(f"Warnings: {result.stderr}")
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Failed to run system health check: {e}")
        return False

def run_camera_troubleshoot():
    """Run camera troubleshooting."""
    print_header("CAMERA TROUBLESHOOTING")
    try:
        result = subprocess.run([sys.executable, "camera_troubleshoot.py"], 
                              cwd=os.path.dirname(__file__), capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(f"Warnings: {result.stderr}")
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Failed to run camera troubleshooting: {e}")
        return False

def run_gps_troubleshoot():
    """Run GPS troubleshooting."""
    print_header("GPS TROUBLESHOOTING")
    try:
        result = subprocess.run([sys.executable, "gps_troubleshoot.py"], 
                              cwd=os.path.dirname(__file__), capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(f"Warnings: {result.stderr}")
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Failed to run GPS troubleshooting: {e}")
        return False

def run_performance_analysis():
    """Run performance analysis."""
    print_header("PERFORMANCE ANALYSIS")
    try:
        result = subprocess.run([sys.executable, "performance_analyzer.py"], 
                              cwd=os.path.dirname(__file__), capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(f"Warnings: {result.stderr}")
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Failed to run performance analysis: {e}")
        return False

def run_system_validation():
    """Run basic system validation tests."""
    print_header("SYSTEM VALIDATION TESTS")
    try:
        result = subprocess.run([sys.executable, "system_validation.py"], 
                              cwd=os.path.dirname(__file__), capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(f"Warnings: {result.stderr}")
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Failed to run system validation: {e}")
        return False

def run_network_test():
    """Run network connectivity tests."""
    print_header("NETWORK CONNECTIVITY TEST")
    try:
        result = subprocess.run(["bash", "network_test.sh"], 
                              cwd=os.path.dirname(__file__), capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(f"Warnings: {result.stderr}")
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Failed to run network test: {e}")
        return False

def check_prerequisites():
    """Check if BathyCat system is properly installed."""
    print_header("PREREQUISITE CHECK")
    
    issues = []
    
    # Check if we're in the right directory
    if not os.path.exists("../src/main.py"):
        issues.append("Not in BathyCat project directory")
    
    # Check if configuration exists
    config_paths = [
        "../config/bathyimager_config.json",
        "/home/bathyimager/BathyCat-Seabed-Imager/config/bathyimager_config.json"
    ]
    config_found = False
    for path in config_paths:
        if os.path.exists(path):
            config_found = True
            print(f"✅ Configuration found: {path}")
            break
    
    if not config_found:
        issues.append("Configuration file not found")
    
    # Check Python dependencies
    try:
        import cv2
        print("✅ OpenCV available")
    except ImportError:
        issues.append("OpenCV not available")
    
    try:
        import serial
        print("✅ PySerial available")
    except ImportError:
        issues.append("PySerial not available")
    
    # Check system tools
    for tool in ['systemctl', 'journalctl', 'lsusb']:
        try:
            subprocess.run([tool, '--version'], capture_output=True, check=True)
            print(f"✅ {tool} available")
        except (subprocess.CalledProcessError, FileNotFoundError):
            issues.append(f"{tool} not available")
    
    if issues:
        print(f"\n❌ Issues found:")
        for issue in issues:
            print(f"   • {issue}")
        return False
    else:
        print(f"\n✅ All prerequisites met")
        return True

def main():
    parser = argparse.ArgumentParser(description='BathyCat Master Troubleshooting Tool')
    parser.add_argument('--component', choices=['camera', 'gps', 'storage'], 
                       help='Run specific component test')
    parser.add_argument('--performance', action='store_true', 
                       help='Run performance analysis only')
    parser.add_argument('--network', action='store_true',
                       help='Run network tests only')
    parser.add_argument('--quick', action='store_true',
                       help='Quick health check only')
    parser.add_argument('--skip-prereq', action='store_true',
                       help='Skip prerequisite check')
    
    args = parser.parse_args()
    
    print("🛠️  BathyCat Master Troubleshooting Tool")
    print("=" * 40)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check prerequisites unless skipped
    if not args.skip_prereq:
        if not check_prerequisites():
            print("\n⚠️  Some prerequisites are missing. Continuing with limited functionality...")
    
    success_count = 0
    total_tests = 0
    
    # Run requested tests
    if args.component == 'camera':
        total_tests = 1
        if run_camera_troubleshoot():
            success_count += 1
    elif args.component == 'gps':
        total_tests = 1
        if run_gps_troubleshoot():
            success_count += 1
    elif args.performance:
        total_tests = 1
        if run_performance_analysis():
            success_count += 1
    elif args.network:
        total_tests = 1
        if run_network_test():
            success_count += 1
    elif args.quick:
        total_tests = 1
        if run_system_health():
            success_count += 1
    else:
        # Full system check
        tests = [
            ("System Health", run_system_health),
            ("System Validation", run_system_validation),
            ("Camera", run_camera_troubleshoot),
            ("GPS", run_gps_troubleshoot),
            ("Performance", run_performance_analysis),
            ("Network", run_network_test)
        ]
        
        total_tests = len(tests)
        for name, test_func in tests:
            print(f"\n📋 Running {name} test...")
            if test_func():
                success_count += 1
                print(f"✅ {name} test completed")
            else:
                print(f"❌ {name} test failed")
    
    # Final summary
    print_header("TROUBLESHOOTING SUMMARY")
    print(f"Tests completed: {success_count}/{total_tests}")
    print(f"Success rate: {(success_count/total_tests)*100:.1f}%")
    
    if success_count == total_tests:
        print("🎉 All tests passed! System appears healthy.")
    else:
        print("⚠️  Some tests failed. Check output above for details.")
        print("\n📚 Common Solutions:")
        print("   • Run: sudo systemctl restart bathyimager")
        print("   • Check: sudo journalctl -u bathyimager -f")
        print("   • Update: ./update --skip-deps")
        print("   • Reinstall: sudo ./scripts/install.sh --update")
    
    return success_count == total_tests

if __name__ == "__main__":
    sys.exit(0 if main() else 1)