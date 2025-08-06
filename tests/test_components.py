#!/usr/bin/env python3
"""
Test Suite for BathyCat Seabed Imager
====================================

Comprehensive test suite for validating system components.

Author: BathyCat Systems
Date: August 2025
"""

import asyncio
import json
import logging
import os
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from config import Config
from camera_controller import CameraController
from gps_controller import GPSController
from image_processor import ImageProcessor
from storage_manager import StorageManager


class TestConfig(unittest.TestCase):
    """Test configuration management."""
    
    def setUp(self):
        """Set up test configuration."""
        self.test_config_path = '/tmp/test_bathycat_config.json'
        
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.test_config_path):
            os.remove(self.test_config_path)
    
    def test_default_config_creation(self):
        """Test default configuration creation."""
        config = Config(self.test_config_path)
        
        # Check essential properties
        self.assertEqual(config.capture_fps, 4.0)
        self.assertEqual(config.camera_width, 1920)
        self.assertEqual(config.camera_height, 1080)
        self.assertTrue(config.enable_metadata)
        
        # Check that config file was created
        self.assertTrue(os.path.exists(self.test_config_path))
    
    def test_config_validation(self):
        """Test configuration validation."""
        # Test invalid capture_fps
        with self.assertRaises(ValueError):
            config = Config()
            config.update_config({'capture_fps': -1})
        
        # Test invalid image format
        with self.assertRaises(ValueError):
            config = Config()
            config.update_config({'image_format': 'INVALID'})
    
    def test_config_update(self):
        """Test configuration updates."""
        config = Config(self.test_config_path)
        
        # Update configuration
        updates = {
            'capture_fps': 2.0,
            'jpeg_quality': 90
        }
        config.update_config(updates)
        
        self.assertEqual(config.capture_fps, 2.0)
        self.assertEqual(config.jpeg_quality, 90)


class TestCameraController(unittest.TestCase):
    """Test camera controller functionality."""
    
    def setUp(self):
        """Set up test camera controller."""
        self.config = Config()
        self.camera = CameraController(self.config)
    
    def test_camera_info(self):
        """Test camera information retrieval."""
        info = self.camera.get_camera_info()
        
        # Should return dict even when not initialized
        self.assertIsInstance(info, dict)
        self.assertIn('device_id', info)
    
    @patch('cv2.VideoCapture')
    def test_camera_initialization(self, mock_capture):
        """Test camera initialization with mocked hardware."""
        # Mock successful camera
        mock_cam = Mock()
        mock_cam.isOpened.return_value = True
        mock_cam.read.return_value = (True, Mock())
        mock_capture.return_value = mock_cam
        
        # Test initialization
        result = asyncio.run(self.camera.initialize())
        self.assertTrue(result)
        self.assertTrue(self.camera.is_initialized)
    
    @patch('cv2.VideoCapture')
    def test_camera_capture(self, mock_capture):
        """Test image capture functionality."""
        # Mock camera and successful capture
        mock_cam = Mock()
        mock_cam.isOpened.return_value = True
        mock_cam.read.return_value = (True, Mock())
        mock_capture.return_value = mock_cam
        
        # Initialize and test capture
        asyncio.run(self.camera.initialize())
        image = asyncio.run(self.camera.capture_image())
        
        self.assertIsNotNone(image)


class TestGPSController(unittest.TestCase):
    """Test GPS controller functionality."""
    
    def setUp(self):
        """Set up test GPS controller."""
        self.config = Config()
        self.gps = GPSController(self.config)
    
    def test_gps_info(self):
        """Test GPS information retrieval."""
        stats = self.gps.get_gps_stats()
        
        self.assertIsInstance(stats, dict)
        self.assertIn('has_fix', stats)
        self.assertIn('message_count', stats)
    
    def test_position_string(self):
        """Test position string formatting."""
        # Test without fix
        pos_str = self.gps.get_position_string()
        self.assertEqual(pos_str, "No GPS Fix")
        
        # Test with simulated fix
        self.gps.current_position.update({
            'latitude': 40.7128,
            'longitude': -74.0060,
            'altitude': 10.0,
            'satellites': 8
        })
        self.gps.has_fix_flag = True
        self.gps.last_update_time = time.time()
        
        pos_str = self.gps.get_position_string()
        self.assertIn("40.7128", pos_str)
        self.assertIn("74.0060", pos_str)
        self.assertIn("8 sats", pos_str)
    
    @patch('serial.Serial')
    def test_gps_initialization(self, mock_serial):
        """Test GPS initialization with mocked hardware."""
        # Mock serial port
        mock_port = Mock()
        mock_port.is_open = True
        mock_port.in_waiting = 0
        mock_serial.return_value = mock_port
        
        # Test initialization
        result = asyncio.run(self.gps.initialize())
        # May fail due to no test data, but should not crash
        self.assertIsInstance(result, bool)


class TestImageProcessor(unittest.TestCase):
    """Test image processor functionality."""
    
    def setUp(self):
        """Set up test image processor."""
        self.config = Config()
        self.config.storage_base_path = '/tmp/test_bathycat'
        self.processor = ImageProcessor(self.config)
    
    def tearDown(self):
        """Clean up test files."""
        import shutil
        if os.path.exists('/tmp/test_bathycat'):
            shutil.rmtree('/tmp/test_bathycat')
    
    def test_directory_creation(self):
        """Test directory structure creation."""
        base_path = Path(self.config.storage_base_path)
        
        self.assertTrue((base_path / 'images').exists())
        self.assertTrue((base_path / 'metadata').exists())
        self.assertTrue((base_path / 'previews').exists())
    
    def test_processing_stats(self):
        """Test processing statistics."""
        stats = self.processor.get_processing_stats()
        
        self.assertIsInstance(stats, dict)
        self.assertIn('processed_count', stats)
        self.assertIn('base_path', stats)
    
    def test_exif_data_creation(self):
        """Test EXIF data creation."""
        gps_data = {
            'latitude': 40.7128,
            'longitude': -74.0060,
            'altitude': 10.0
        }
        
        exif_dict = self.processor._create_exif_data(
            gps_data, time.time(), (1080, 1920, 3)
        )
        
        self.assertIn('GPS', exif_dict)
        self.assertIn('0th', exif_dict)
        self.assertIn('Exif', exif_dict)


class TestStorageManager(unittest.TestCase):
    """Test storage manager functionality."""
    
    def setUp(self):
        """Set up test storage manager."""
        self.config = Config()
        self.config.storage_base_path = '/tmp/test_bathycat_storage'
        self.storage = StorageManager(self.config)
    
    def tearDown(self):
        """Clean up test files."""
        import shutil
        if os.path.exists('/tmp/test_bathycat_storage'):
            shutil.rmtree('/tmp/test_bathycat_storage')
    
    def test_initialization(self):
        """Test storage initialization."""
        result = asyncio.run(self.storage.initialize())
        self.assertTrue(result)
        
        # Check directory creation
        base_path = Path(self.config.storage_base_path)
        self.assertTrue(base_path.exists())
        self.assertTrue((base_path / 'images').exists())
    
    def test_storage_stats(self):
        """Test storage statistics."""
        asyncio.run(self.storage.initialize())
        stats = self.storage.get_storage_stats()
        
        self.assertIsInstance(stats, dict)
        self.assertIn('base_path', stats)
        self.assertIn('free_space_gb', stats)
        self.assertIn('total_images', stats)
    
    def test_health_check(self):
        """Test storage health monitoring."""
        asyncio.run(self.storage.initialize())
        health = asyncio.run(self.storage.check_storage_health())
        
        self.assertIsInstance(health, dict)
        self.assertIn('status', health)
        self.assertIn('free_space_gb', health)


class TestSystemIntegration(unittest.TestCase):
    """Test system integration scenarios."""
    
    def setUp(self):
        """Set up integration test environment."""
        self.config = Config()
        self.config.storage_base_path = '/tmp/test_bathycat_integration'
        
    def tearDown(self):
        """Clean up integration test files."""
        import shutil
        if os.path.exists('/tmp/test_bathycat_integration'):
            shutil.rmtree('/tmp/test_bathycat_integration')
    
    def test_component_initialization_order(self):
        """Test proper component initialization order."""
        # Storage should initialize first
        storage = StorageManager(self.config)
        storage_result = asyncio.run(storage.initialize())
        self.assertTrue(storage_result)
        
        # Then other components
        processor = ImageProcessor(self.config)
        gps = GPSController(self.config)
        camera = CameraController(self.config)
        
        # All should be able to create their basic structures
        self.assertIsNotNone(processor)
        self.assertIsNotNone(gps)
        self.assertIsNotNone(camera)
    
    def test_error_handling(self):
        """Test error handling in various scenarios."""
        # Test with invalid storage path
        bad_config = Config()
        bad_config.storage_base_path = '/invalid/path/that/cannot/be/created'
        
        storage = StorageManager(bad_config)
        # Should handle gracefully
        result = asyncio.run(storage.initialize())
        self.assertFalse(result)


def run_hardware_tests():
    """Run tests that require actual hardware."""
    print("Running hardware-specific tests...")
    
    # GPS Hardware Test
    try:
        if os.path.exists('/dev/serial0'):
            print("✓ GPS serial port found")
        else:
            print("✗ GPS serial port not found")
    except Exception as e:
        print(f"✗ GPS test error: {e}")
    
    # Camera Hardware Test
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                print("✓ Camera capture successful")
            else:
                print("✗ Camera capture failed")
            cap.release()
        else:
            print("✗ Camera not accessible")
    except Exception as e:
        print(f"✗ Camera test error: {e}")
    
    # Storage Hardware Test
    try:
        if os.path.exists('/media/ssd'):
            import shutil
            total, used, free = shutil.disk_usage('/media/ssd')
            print(f"✓ Storage accessible: {free // (1024**3)}GB free")
        else:
            print("✗ Storage mount point not found")
    except Exception as e:
        print(f"✗ Storage test error: {e}")


def main():
    """Main test runner."""
    print("BathyCat Seabed Imager Test Suite")
    print("=" * 40)
    
    # Configure logging for tests
    logging.basicConfig(level=logging.WARNING)
    
    # Run unit tests
    print("\nRunning unit tests...")
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestCameraController))
    suite.addTests(loader.loadTestsFromTestCase(TestGPSController))
    suite.addTests(loader.loadTestsFromTestCase(TestImageProcessor))
    suite.addTests(loader.loadTestsFromTestCase(TestStorageManager))
    suite.addTests(loader.loadTestsFromTestCase(TestSystemIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Run hardware tests if requested
    if '--hardware' in sys.argv:
        print("\n" + "=" * 40)
        run_hardware_tests()
    
    # Summary
    print("\n" + "=" * 40)
    print("Test Summary:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures or result.errors:
        print("\nTest suite FAILED")
        return 1
    else:
        print("\nAll tests PASSED")
        return 0


if __name__ == '__main__':
    sys.exit(main())
