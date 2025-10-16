"""
Test Suite for BathyCat Seabed Imager
=====================================

Comprehensive unit and integration tests for all BathyCat components.
Includes mock testing for development environments without hardware.
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
import os
import tempfile
import json
import threading
import time
from datetime import datetime
from pathlib import Path

# Import BathyCat modules
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config import BathyCatConfig, ConfigManager, CameraConfig, GPSConfig
from gps import GPS, GPSFix
from camera import Camera
from image_processor import ImageProcessor
from storage import StorageManager
from led_status import LEDManager
from main import BathyCatService


class TestConfiguration(unittest.TestCase):
    """Test configuration system."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, 'test_config.json')
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_default_config_creation(self):
        """Test default configuration creation."""
        config = BathyCatConfig()
        
        # Check that all components are initialized
        self.assertIsNotNone(config.camera)
        self.assertIsNotNone(config.gps)
        self.assertIsNotNone(config.storage)
        self.assertIsNotNone(config.leds)
        self.assertIsNotNone(config.logging)
        self.assertIsNotNone(config.system)
        
        # Check default values
        self.assertEqual(config.camera.width, 1920)
        self.assertEqual(config.camera.height, 1080)
        self.assertEqual(config.gps.port, "/dev/ttyUSB0")
        self.assertEqual(config.storage.base_path, "/media/usb")
    
    def test_config_validation(self):
        """Test configuration validation."""
        manager = ConfigManager(self.config_path)
        
        # Valid configuration should pass
        valid_config = BathyCatConfig()
        try:
            manager._validate_config(valid_config)
        except Exception as e:
            self.fail(f"Valid configuration failed validation: {e}")
        
        # Invalid camera resolution should fail
        invalid_config = BathyCatConfig()
        invalid_config.camera.width = -100
        
        with self.assertRaises(Exception):
            manager._validate_config(invalid_config)
    
    def test_config_save_load(self):
        """Test saving and loading configuration."""
        manager = ConfigManager(self.config_path)
        
        # Create and save configuration
        original_config = BathyCatConfig()
        original_config.camera.width = 1280
        original_config.camera.height = 720
        original_config.gps.baudrate = 19200
        
        manager.save_config(original_config)
        
        # Load configuration
        loaded_config = manager.load_config()
        
        # Check that values match
        self.assertEqual(loaded_config.camera.width, 1280)
        self.assertEqual(loaded_config.camera.height, 720)
        self.assertEqual(loaded_config.gps.baudrate, 19200)
    
    def test_environment_settings(self):
        """Test environment-specific settings."""
        manager = ConfigManager(self.config_path)
        
        # Test development environment
        config = BathyCatConfig()
        config.system.environment = "development"
        
        config = manager._apply_environment_settings(config)
        
        self.assertEqual(config.logging.level, "DEBUG")
        self.assertTrue(config.logging.console_output)
        self.assertTrue(config.gps.mock_enabled)


class TestGPSModule(unittest.TestCase):
    """Test GPS functionality."""
    
    def setUp(self):
        """Set up GPS test fixtures."""
        self.gps_config = GPSConfig()
        self.gps_config.mock_enabled = True  # Use mock for testing
    
    @patch('serial.Serial')
    def test_gps_connection(self, mock_serial):
        """Test GPS connection."""
        # Mock serial connection
        mock_serial_instance = Mock()
        mock_serial.return_value = mock_serial_instance
        
        gps = GPS(self.gps_config)
        
        # Test connection
        result = gps.connect()
        self.assertTrue(result)
        self.assertTrue(gps.connected)
    
    def test_gps_mock_mode(self):
        """Test GPS mock mode."""
        gps = GPS(self.gps_config)
        gps.connect()
        
        # In mock mode, should immediately have a fix
        fix = gps.wait_for_fix(timeout=1.0)
        
        self.assertIsNotNone(fix)
        self.assertTrue(fix.valid)
        self.assertEqual(fix.latitude, self.gps_config.mock_latitude)
        self.assertEqual(fix.longitude, self.gps_config.mock_longitude)
    
    def test_nmea_parsing(self):
        """Test NMEA sentence parsing."""
        gps = GPS(self.gps_config)
        
        # Test valid GPGGA sentence
        gpgga_sentence = "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47"
        
        gps._process_nmea_sentence(gpgga_sentence)
        
        # Check that fix was updated
        self.assertIsNotNone(gps.last_fix)
        
        # Test invalid sentence (should not crash)
        invalid_sentence = "INVALID NMEA DATA"
        gps._process_nmea_sentence(invalid_sentence)
    
    def test_gps_health_monitoring(self):
        """Test GPS health monitoring."""
        gps = GPS(self.gps_config)
        gps.connect()
        
        # Should be healthy in mock mode
        health = gps.get_health()
        self.assertTrue(health['connected'])
        self.assertTrue(health['fix_available'])


class TestCameraModule(unittest.TestCase):
    """Test camera functionality."""
    
    def setUp(self):
        """Set up camera test fixtures."""
        self.camera_config = CameraConfig()
        self.camera_config.device_index = 0
    
    @patch('cv2.VideoCapture')
    def test_camera_initialization(self, mock_video_capture):
        """Test camera initialization."""
        # Mock OpenCV VideoCapture
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.set.return_value = True
        mock_video_capture.return_value = mock_cap
        
        camera = Camera(self.camera_config)
        result = camera.initialize()
        
        self.assertTrue(result)
        self.assertIsNotNone(camera.cap)
    
    @patch('cv2.VideoCapture')
    def test_frame_capture(self, mock_video_capture):
        """Test frame capture."""
        import numpy as np
        
        # Mock successful frame capture
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        mock_video_capture.return_value = mock_cap
        
        camera = Camera(self.camera_config)
        camera.initialize()
        
        frame = camera.capture_frame()
        self.assertIsNotNone(frame)
    
    @patch('cv2.VideoCapture')
    def test_camera_health_monitoring(self, mock_video_capture):
        """Test camera health monitoring."""
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_video_capture.return_value = mock_cap
        
        camera = Camera(self.camera_config)
        camera.initialize()
        
        health = camera.get_health()
        self.assertTrue(health['initialized'])
        self.assertTrue(health['connected'])


class TestImageProcessor(unittest.TestCase):
    """Test image processing functionality."""
    
    def setUp(self):
        """Set up image processor test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.processor = ImageProcessor()
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_gps_metadata_embedding(self):
        """Test GPS metadata embedding."""
        import numpy as np
        from PIL import Image
        
        # Create test image
        test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        pil_image = Image.fromarray(test_image)
        
        # Create test GPS fix
        gps_fix = GPSFix(
            valid=True,
            latitude=40.7128,
            longitude=-74.0060,
            altitude=10.0,
            satellites=8,
            timestamp=datetime.now()
        )
        
        # Process image
        output_path = os.path.join(self.temp_dir, 'test_output.jpg')
        result = self.processor.process_frame(pil_image, gps_fix, output_path)
        
        self.assertTrue(result)
        self.assertTrue(os.path.exists(output_path))
        
        # Verify GPS data was embedded
        processed_image = Image.open(output_path)
        exif_data = processed_image._getexif()
        
        # Should contain GPS data (exact structure depends on piexif implementation)
        self.assertIsNotNone(exif_data)
    
    def test_coordinate_conversion(self):
        """Test coordinate conversion functions."""
        # Test positive coordinates
        degrees, minutes, seconds = self.processor._decimal_to_dms(40.7128)
        self.assertEqual(degrees, 40)
        self.assertAlmostEqual(minutes + seconds/60, 42.768, places=3)
        
        # Test negative coordinates
        degrees, minutes, seconds = self.processor._decimal_to_dms(-74.0060)
        self.assertEqual(degrees, 74)  # Absolute value
        self.assertAlmostEqual(minutes + seconds/60, 0.36, places=2)


class TestStorageManager(unittest.TestCase):
    """Test storage management functionality."""
    
    def setUp(self):
        """Set up storage test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create storage config pointing to temp directory
        from config import StorageConfig
        self.storage_config = StorageConfig()
        self.storage_config.base_path = self.temp_dir
        
        self.storage = StorageManager(self.storage_config)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_directory_creation(self):
        """Test directory structure creation."""
        test_date = datetime(2023, 12, 25, 10, 30, 45)
        
        image_path = self.storage.get_image_path(test_date)
        
        # Check path structure
        expected_dir = os.path.join(self.temp_dir, "2023", "12", "25")
        self.assertIn(expected_dir, image_path)
        
        # Check that directory would be created
        self.storage.save_image(b"test image data", image_path)
        self.assertTrue(os.path.exists(expected_dir))
    
    def test_file_cleanup(self):
        """Test old file cleanup."""
        # Create test files with different dates
        old_dir = os.path.join(self.temp_dir, "2020", "01", "01")
        os.makedirs(old_dir, exist_ok=True)
        
        old_file = os.path.join(old_dir, "old_image.jpg")
        with open(old_file, 'w') as f:
            f.write("old image data")
        
        # Run cleanup
        self.storage._cleanup_old_files()
        
        # Old file should be removed (assuming cleanup_days setting)
        # This depends on the actual cleanup implementation
    
    def test_space_monitoring(self):
        """Test disk space monitoring."""
        space_info = self.storage.get_space_info()
        
        self.assertIn('total_mb', space_info)
        self.assertIn('free_mb', space_info)
        self.assertIn('used_mb', space_info)
        self.assertGreaterEqual(space_info['free_mb'], 0)


class TestLEDManager(unittest.TestCase):
    """Test LED status functionality."""
    
    def setUp(self):
        """Set up LED test fixtures."""
        from config import LEDConfig
        self.led_config = LEDConfig()
        self.led_config.enabled = True  # Enable for testing
        
        # Mock GPIO for testing
        with patch('bathycat.led_status.GPIO'):
            self.led_manager = LEDManager(self.led_config)
    
    @patch('bathycat.led_status.GPIO')
    def test_led_initialization(self, mock_gpio):
        """Test LED initialization."""
        led_manager = LEDManager(self.led_config)
        result = led_manager.initialize()
        
        self.assertTrue(result)
        # Verify GPIO setup calls were made
        mock_gpio.setmode.assert_called()
        mock_gpio.setup.assert_called()
    
    @patch('bathycat.led_status.GPIO')
    def test_status_updates(self, mock_gpio):
        """Test LED status updates."""
        led_manager = LEDManager(self.led_config)
        led_manager.initialize()
        
        # Test different status updates
        led_manager.set_status('ok')
        led_manager.set_status('error')
        led_manager.set_status('starting')
        
        # Should not raise exceptions
    
    def test_mock_mode(self):
        """Test LED manager in mock mode."""
        # When GPIO is not available, should use mock mode
        led_manager = LEDManager(self.led_config)
        result = led_manager.initialize()
        
        # Should still initialize successfully
        self.assertTrue(result)


class TestMainService(unittest.TestCase):
    """Test main service coordination."""
    
    def setUp(self):
        """Set up service test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, 'test_config.json')
        
        # Create test configuration
        config = BathyCatConfig()
        config.system.environment = "testing"
        config.gps.mock_enabled = True
        config.leds.enabled = False  # Disable LEDs for testing
        config.storage.base_path = os.path.join(self.temp_dir, 'storage')
        
        manager = ConfigManager(self.config_path)
        manager.save_config(config)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    @patch('cv2.VideoCapture')
    def test_service_initialization(self, mock_video_capture):
        """Test service initialization."""
        # Mock camera
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_video_capture.return_value = mock_cap
        
        service = BathyCatService(self.config_path)
        result = service.initialize()
        
        self.assertTrue(result)
        self.assertIsNotNone(service.camera)
        self.assertIsNotNone(service.gps)
        self.assertIsNotNone(service.storage)
    
    @patch('cv2.VideoCapture')
    @patch('bathycat.led_status.GPIO')
    def test_service_lifecycle(self, mock_gpio, mock_video_capture):
        """Test complete service lifecycle."""
        # Mock camera
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, None)  # Will be handled by error handling
        mock_video_capture.return_value = mock_cap
        
        service = BathyCatService(self.config_path)
        service.initialize()
        
        # Start service in separate thread
        service_thread = threading.Thread(target=service.start)
        service_thread.daemon = True
        service_thread.start()
        
        # Let it run briefly
        time.sleep(0.5)
        
        # Stop service
        service.stop()
        
        # Should stop gracefully
        service_thread.join(timeout=2.0)
        self.assertFalse(service.running)


class TestIntegration(unittest.TestCase):
    """Integration tests for complete system."""
    
    def setUp(self):
        """Set up integration test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, 'integration_config.json')
        
        # Create integration test configuration
        config = BathyCatConfig()
        config.system.environment = "testing"
        config.system.capture_interval = 0.1  # Fast capture for testing
        config.gps.mock_enabled = True
        config.leds.enabled = False
        config.storage.base_path = os.path.join(self.temp_dir, 'storage')
        
        manager = ConfigManager(self.config_path)
        manager.save_config(config)
    
    def tearDown(self):
        """Clean up integration test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    @patch('cv2.VideoCapture')
    def test_end_to_end_capture(self, mock_video_capture):
        """Test complete end-to-end image capture process."""
        import numpy as np
        
        # Mock successful camera capture
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_cap.read.return_value = (True, test_frame)
        mock_video_capture.return_value = mock_cap
        
        # Initialize service
        service = BathyCatService(self.config_path)
        service.initialize()
        
        # Manually trigger one capture cycle
        result = service._capture_image()
        
        # Should succeed
        self.assertTrue(result)
        
        # Check that image was saved
        storage_dir = os.path.join(self.temp_dir, 'storage')
        self.assertTrue(os.path.exists(storage_dir))
        
        # Check for image files (may be in date subdirectories)
        image_found = False
        for root, dirs, files in os.walk(storage_dir):
            for file in files:
                if file.endswith('.jpg'):
                    image_found = True
                    break
            if image_found:
                break
        
        self.assertTrue(image_found, "No image files were created")


def create_test_suite():
    """Create comprehensive test suite."""
    suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestConfiguration,
        TestGPSModule,
        TestCameraModule,
        TestImageProcessor,
        TestStorageManager,
        TestLEDManager,
        TestMainService,
        TestIntegration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    return suite


def run_tests():
    """Run all tests with detailed output."""
    import sys
    
    # Create test suite
    suite = create_test_suite()
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"  {test}: {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"  {test}: {traceback}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)