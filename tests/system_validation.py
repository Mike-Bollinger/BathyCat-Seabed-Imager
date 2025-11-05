#!/usr/bin/env python3
"""
Simple Test Runner for BathyCat Seabed Imager
===========================================

Basic test runner that works without external dependencies.
Tests core functionality with built-in unittest framework.
"""

import unittest
import sys
import os
import tempfile
import json
from unittest.mock import Mock, patch

# Add source directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from config import BathyCatConfig, ConfigManager, CameraConfig, GPSConfig
    from gps import GPS, GPSFix
    BATHYCAT_AVAILABLE = True
except ImportError as e:
    print(f"Warning: BathyCat modules not available: {e}")
    BATHYCAT_AVAILABLE = False


class TestBasicConfiguration(unittest.TestCase):
    """Basic configuration tests."""
    
    @unittest.skipUnless(BATHYCAT_AVAILABLE, "BathyCat modules not available")
    def test_config_creation(self):
        """Test basic configuration creation."""
        config = BathyCatConfig()
        self.assertIsNotNone(config)
        self.assertIsNotNone(config.camera)
        self.assertIsNotNone(config.gps)
        self.assertEqual(config.version, "1.0")
    
    @unittest.skipUnless(BATHYCAT_AVAILABLE, "BathyCat modules not available")
    def test_config_validation(self):
        """Test configuration validation."""
        config = CameraConfig()
        
        # Valid configuration
        self.assertEqual(config.width, 1920)
        self.assertEqual(config.height, 1080)
        self.assertGreater(config.fps, 0)
        
        # GPS configuration
        gps_config = GPSConfig()
        self.assertIn('/dev/tty', gps_config.port)
        self.assertGreater(gps_config.baudrate, 0)


class TestGPSBasic(unittest.TestCase):
    """Basic GPS functionality tests."""
    
    @unittest.skipUnless(BATHYCAT_AVAILABLE, "BathyCat modules not available")
    def test_gps_fix_creation(self):
        """Test GPS fix data structure."""
        from datetime import datetime
        
        fix = GPSFix(
            valid=True,
            latitude=40.7128,
            longitude=-74.0060,
            altitude=10.0,
            satellites=8,
            timestamp=datetime.now()
        )
        
        self.assertTrue(fix.valid)
        self.assertEqual(fix.latitude, 40.7128)
        self.assertEqual(fix.longitude, -74.0060)
        self.assertEqual(fix.satellites, 8)
    
    @unittest.skipUnless(BATHYCAT_AVAILABLE, "BathyCat modules not available")
    def test_gps_mock_mode(self):
        """Test GPS mock functionality."""
        config = GPSConfig()
        config.mock_enabled = True
        
        gps = GPS(config)
        
        # Should be able to create GPS instance
        self.assertIsNotNone(gps)
        self.assertEqual(gps.config.mock_latitude, config.mock_latitude)


class TestConfigFileOperations(unittest.TestCase):
    """Test configuration file operations."""
    
    def setUp(self):
        """Set up temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, 'test_config.json')
    
    def tearDown(self):
        """Clean up temporary directory."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    @unittest.skipUnless(BATHYCAT_AVAILABLE, "BathyCat modules not available")
    def test_config_save_load_cycle(self):
        """Test saving and loading configuration."""
        # Create configuration manager
        manager = ConfigManager(self.config_path)
        
        # Create test configuration
        config = BathyCatConfig()
        config.camera.width = 1280
        config.camera.height = 720
        config.gps.baudrate = 19200
        
        # Save configuration
        manager.save_config(config)
        
        # Verify file exists
        self.assertTrue(os.path.exists(self.config_path))
        
        # Load configuration
        loaded_config = manager.load_config()
        
        # Verify loaded values
        self.assertEqual(loaded_config.camera.width, 1280)
        self.assertEqual(loaded_config.camera.height, 720)
        self.assertEqual(loaded_config.gps.baudrate, 19200)
    
    def test_json_file_creation(self):
        """Test basic JSON file operations."""
        test_data = {
            'version': '1.0',
            'camera': {
                'width': 1920,
                'height': 1080
            },
            'gps': {
                'port': '/dev/ttyUSB0',
                'baudrate': 9600
            }
        }
        
        # Write JSON file
        with open(self.config_path, 'w') as f:
            json.dump(test_data, f, indent=2)
        
        # Read JSON file
        with open(self.config_path, 'r') as f:
            loaded_data = json.load(f)
        
        # Verify data
        self.assertEqual(loaded_data['version'], '1.0')
        self.assertEqual(loaded_data['camera']['width'], 1920)
        self.assertEqual(loaded_data['gps']['baudrate'], 9600)


class TestDirectoryOperations(unittest.TestCase):
    """Test directory and file operations."""
    
    def setUp(self):
        """Set up temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up temporary directory."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_directory_creation(self):
        """Test creating nested directories."""
        from datetime import datetime
        
        # Create date-based directory structure
        now = datetime.now()
        date_path = os.path.join(
            self.temp_dir,
            str(now.year),
            f"{now.month:02d}",
            f"{now.day:02d}"
        )
        
        os.makedirs(date_path, exist_ok=True)
        
        self.assertTrue(os.path.exists(date_path))
        self.assertTrue(os.path.isdir(date_path))
    
    def test_file_operations(self):
        """Test basic file operations."""
        test_file = os.path.join(self.temp_dir, 'test_image.jpg')
        test_data = b"fake image data"
        
        # Write file
        with open(test_file, 'wb') as f:
            f.write(test_data)
        
        # Verify file exists
        self.assertTrue(os.path.exists(test_file))
        
        # Read file
        with open(test_file, 'rb') as f:
            read_data = f.read()
        
        self.assertEqual(read_data, test_data)


class TestSystemCompatibility(unittest.TestCase):
    """Test system compatibility and requirements."""
    
    def test_python_version(self):
        """Test Python version compatibility."""
        version = sys.version_info
        self.assertGreaterEqual(version.major, 3)
        self.assertGreaterEqual(version.minor, 7)
    
    def test_basic_imports(self):
        """Test that basic required modules can be imported."""
        try:
            import json
            import os
            import sys
            import threading
            import time
            import tempfile
            import subprocess
            import logging
        except ImportError as e:
            self.fail(f"Failed to import required module: {e}")
    
    def test_optional_imports(self):
        """Test optional imports with graceful degradation."""
        optional_modules = [
            ('cv2', 'OpenCV'),
            ('serial', 'PySerial'),
            ('PIL', 'Pillow'),
            ('pynmea2', 'PyNMEA2'),
            ('RPi.GPIO', 'RPi.GPIO')
        ]
        
        results = {}
        for module_name, description in optional_modules:
            try:
                __import__(module_name)
                results[description] = True
            except ImportError:
                results[description] = False
        
        print("\nOptional module availability:")
        for description, available in results.items():
            status = "✓" if available else "✗"
            print(f"  {status} {description}")


def run_basic_tests():
    """Run basic tests with simple output."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestBasicConfiguration,
        TestGPSBasic,
        TestConfigFileOperations,
        TestDirectoryOperations,
        TestSystemCompatibility
    ]
    
    for test_class in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(test_class))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print(f"\n{'='*50}")
    print(f"Basic Tests Summary")
    print(f"{'='*50}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.testsRun > 0:
        success_rate = (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100
        print(f"Success rate: {success_rate:.1f}%")
    
    if result.failures:
        print(f"\nFailures ({len(result.failures)}):")
        for test, traceback in result.failures:
            print(f"  • {test}")
    
    if result.errors:
        print(f"\nErrors ({len(result.errors)}):")
        for test, traceback in result.errors:
            print(f"  • {test}")
    
    return result.wasSuccessful()


def check_installation():
    """Check if BathyCat is properly installed."""
    print("BathyCat Installation Check")
    print("="*30)
    
    # Check if source code is available
    src_dir = os.path.join(os.path.dirname(__file__), '..', 'src')
    if os.path.exists(src_dir):
        print("✓ Source code directory found")
        
        # Check for required files
        required_files = [
            '__init__.py',
            'main.py',
            'camera.py',
            'gps.py',
            'config.py'
        ]
        
        for file in required_files:
            file_path = os.path.join(src_dir, file)
            if os.path.exists(file_path):
                print(f"✓ {file}")
            else:
                print(f"✗ {file} (missing)")
    else:
        print("✗ Source code directory not found")
    
    # Check configuration directory
    config_dirs = ['/etc/bathycat', '/opt/bathycat']
    for config_dir in config_dirs:
        if os.path.exists(config_dir):
            print(f"✓ Configuration directory: {config_dir}")
            break
    else:
        print("! No configuration directory found (normal for development)")
    
    print()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='BathyCat Basic Test Runner')
    parser.add_argument('--check', action='store_true', help='Check installation only')
    parser.add_argument('--quick', action='store_true', help='Run quick tests only')
    
    args = parser.parse_args()
    
    if args.check:
        check_installation()
    else:
        check_installation()
        print("Running basic tests...\n")
        success = run_basic_tests()
        
        if success:
            print("\n✓ All basic tests passed!")
            sys.exit(0)
        else:
            print("\n✗ Some tests failed.")
            sys.exit(1)