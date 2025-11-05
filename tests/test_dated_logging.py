#!/usr/bin/env python3
"""
Test Date-Stamped Logging System
===============================

Tests the new date-stamped logging functionality that mirrors the image directory structure.
"""

import os
import sys
import tempfile
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_dated_logging_structure():
    """Test that logging creates date-stamped directory structure like images."""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test config with USB storage path
        config = {
            'log_to_file': True,
            'log_file_path': os.path.join(temp_dir, 'logs', 'bathyimager.log'),
            'log_level': 'INFO'
        }
        
        # Import after path setup
        from main import BathyCatService
        
        # Create service instance
        service = BathyCatService(config)
        
        # Test date-stamped path generation
        test_date = datetime(2025, 11, 4, 10, 30, 0)  # November 4, 2025
        dated_path = service._get_dated_log_path(config['log_file_path'], test_date)
        
        print(f"📅 Test date: {test_date.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📁 Base log path: {config['log_file_path']}")
        print(f"📂 Dated log path: {dated_path}")
        
        # Verify directory structure
        expected_date_dir = "20251104"
        assert expected_date_dir in dated_path, f"Expected {expected_date_dir} in path {dated_path}"
        
        # Verify the path exists after calling the method
        assert os.path.exists(os.path.dirname(dated_path)), "Log directory should be created"
        
        # Test different dates create different directories
        next_day = test_date + timedelta(days=1)
        next_day_path = service._get_dated_log_path(config['log_file_path'], next_day)
        
        print(f"📅 Next day: {next_day.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📂 Next day log path: {next_day_path}")
        
        expected_next_dir = "20251105"
        assert expected_next_dir in next_day_path, f"Expected {expected_next_dir} in path {next_day_path}"
        assert dated_path != next_day_path, "Different dates should create different log paths"
        
        print("✅ Date-stamped logging structure test passed!")

def test_log_structure_matches_images():
    """Test that log structure matches image directory structure."""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test config
        config = {
            'log_to_file': True,
            'log_file_path': os.path.join(temp_dir, 'logs', 'bathyimager.log'),
            'storage_base_path': temp_dir,
            'filename_prefix': 'bathyimgtest'
        }
        
        # Import modules
        from main import BathyCatService
        from storage import StorageManager
        
        # Create service and storage instances
        service = BathyCatService(config)
        storage = StorageManager(config)
        
        # Test same date
        test_date = datetime(2025, 11, 4, 14, 25, 30)
        
        # Get log path and image path for same date
        log_path = service._get_dated_log_path(config['log_file_path'], test_date)
        image_path = storage.get_image_path(test_date)
        
        print(f"📅 Test date: {test_date.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📂 Log path: {log_path}")
        print(f"🖼️  Image path: {image_path}")
        
        # Extract date directory from both paths
        log_date_dir = os.path.basename(os.path.dirname(log_path))
        image_date_dir = os.path.basename(os.path.dirname(image_path))
        
        print(f"📁 Log date dir: {log_date_dir}")
        print(f"📁 Image date dir: {image_date_dir}")
        
        assert log_date_dir == image_date_dir, f"Log and image date directories should match: {log_date_dir} != {image_date_dir}"
        assert log_date_dir == "20251104", f"Expected 20251104, got {log_date_dir}"
        
        print("✅ Log and image directory structure matching test passed!")

def demonstrate_log_rotation():
    """Demonstrate daily log rotation behavior."""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config = {
            'log_to_file': True,
            'log_file_path': os.path.join(temp_dir, 'logs', 'bathyimager.log'),
            'log_level': 'INFO'
        }
        
        from main import BathyCatService
        
        service = BathyCatService(config)
        
        print("📝 Demonstrating daily log rotation:")
        
        # Simulate multiple days
        base_date = datetime(2025, 11, 1)
        for day_offset in range(5):
            current_date = base_date + timedelta(days=day_offset)
            log_path = service._get_dated_log_path(config['log_file_path'], current_date)
            
            # Write a test log entry
            with open(log_path, 'a') as f:
                timestamp = current_date.strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"{timestamp} - BathyCat - INFO - Daily log entry for {current_date.strftime('%Y-%m-%d')}\n")
            
            print(f"  📅 Day {day_offset + 1}: {current_date.strftime('%Y-%m-%d')} -> {os.path.relpath(log_path, temp_dir)}")
        
        # Show directory structure
        logs_root = os.path.join(temp_dir, 'logs')
        if os.path.exists(logs_root):
            print(f"\n📁 Final log directory structure in {logs_root}:")
            for root, dirs, files in os.walk(logs_root):
                level = root.replace(logs_root, '').count(os.sep)
                indent = '  ' * level
                print(f"{indent}📂 {os.path.basename(root)}/")
                subindent = '  ' * (level + 1)
                for file in files:
                    file_path = os.path.join(root, file)
                    size = os.path.getsize(file_path)
                    print(f"{subindent}📄 {file} ({size} bytes)")
        
        print("✅ Daily log rotation demonstration completed!")

if __name__ == "__main__":
    print("🧪 Testing Date-Stamped Logging System")
    print("=" * 50)
    
    try:
        test_dated_logging_structure()
        print()
        test_log_structure_matches_images()
        print()
        demonstrate_log_rotation()
        
        print("\n🎉 All tests passed! Date-stamped logging system is working correctly.")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)