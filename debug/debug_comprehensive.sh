#!/bin/bash
#
# Comprehensive NumPy Boolean Debug Script
# =======================================
#
# This script ensures all debugging is in place and provides
# detailed error tracking to identify the exact source of the
# "truth value of an array is ambiguous" error.
#

set -e

echo "========================================="
echo "Comprehensive NumPy Boolean Debug Setup"
echo "========================================="
echo ""

# Check if we're in the correct directory
if [[ ! -f "src/bathycat_imager.py" ]]; then
    echo "Error: Please run this script from the BathyCat-Seabed-Imager directory"
    exit 1
fi

# Create backup
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)_comprehensive_debug"
mkdir -p "$BACKUP_DIR"

echo "[INFO] Creating backup in $BACKUP_DIR..."
cp -r src/ "$BACKUP_DIR/"
echo "[SUCCESS] Backup created"

echo ""
echo "[INFO] Verifying comprehensive debugging is in place..."

# Check for debug markers in each file
echo ""
echo "Checking bathycat_imager.py:"
if grep -q "🚨 CAPTURE_LOOP_ERROR" src/bathycat_imager.py; then
    echo "  ✅ Main capture loop error tracking"
else
    echo "  ❌ Missing main capture loop error tracking"
    exit 1
fi

if grep -q "📷 STEP_" src/bathycat_imager.py; then
    echo "  ✅ Step-by-step capture debugging"
else
    echo "  ❌ Missing step-by-step debugging"
    exit 1
fi

echo ""
echo "Checking camera_controller.py:"
if grep -q "🚨 CAM_CAPTURE_ERROR" src/camera_controller.py; then
    echo "  ✅ Camera capture error tracking"
else
    echo "  ❌ Missing camera capture error tracking"
    exit 1
fi

if grep -q "📷 CAM_CAPTURE_" src/camera_controller.py; then
    echo "  ✅ Camera operation debugging"
else
    echo "  ❌ Missing camera operation debugging"
    exit 1
fi

echo ""
echo "Checking gps_controller.py:"
if grep -q "🚨 GGA_PROCESSING_ERROR" src/gps_controller.py; then
    echo "  ✅ GPS GGA processing error tracking"
else
    echo "  ❌ Missing GPS GGA error tracking"
    exit 1
fi

if grep -q "🚨 RMC_PROCESSING_ERROR" src/gps_controller.py; then
    echo "  ✅ GPS RMC processing error tracking"
else
    echo "  ❌ Missing GPS RMC error tracking"
    exit 1
fi

if grep -q "🛰️ GGA_PROCESS" src/gps_controller.py; then
    echo "  ✅ GPS message debugging"
else
    echo "  ❌ Missing GPS message debugging"
    exit 1
fi

echo ""
echo "Checking image_processor.py:"
if grep -q "🚨 IMG_PROCESSING_ERROR" src/image_processor.py; then
    echo "  ✅ Image processing error tracking"
else
    echo "  ❌ Missing image processing error tracking"
    exit 1
fi

if grep -q "💾 IMG_PROC_" src/image_processor.py; then
    echo "  ✅ Image processing debugging"
else
    echo "  ❌ Missing image processing debugging"
    exit 1
fi

echo ""
echo "[INFO] Testing Python syntax..."
python3 -m py_compile src/bathycat_imager.py
python3 -m py_compile src/camera_controller.py  
python3 -m py_compile src/gps_controller.py
python3 -m py_compile src/image_processor.py
echo "[SUCCESS] All Python files compile successfully"

echo ""
echo "========================================="
echo "COMPREHENSIVE DEBUG SUMMARY"
echo "========================================="
echo ""
echo "🔍 UNIQUE ERROR IDENTIFIERS ADDED:"
echo ""
echo "   Main Capture Loop:"
echo "     🚨 CAPTURE_LOOP_ERROR - Main loop exceptions"
echo "     📷 STEP_1 through STEP_5 - Individual capture steps"
echo "     🎯 PROBLEM_FILE_LINE - Source file identification"
echo "     🔥 NUMPY_ERROR_LINE - NumPy error detection"
echo ""
echo "   Camera Controller:"
echo "     🚨 CAM_CAPTURE_ERROR - Camera operation errors"
echo "     📷 CAM_CAPTURE_1/2 - Camera read operations"
echo "     🚨 CAM_ERROR_1/2 - Specific camera failures"
echo ""
echo "   GPS Controller:"
echo "     🚨 GGA_PROCESSING_ERROR - GPS GGA message errors"
echo "     🚨 RMC_PROCESSING_ERROR - GPS RMC message errors"
echo "     🛰️ GGA_PROCESS/RMC_PROCESS - GPS message debugging"
echo ""
echo "   Image Processor:"
echo "     🚨 IMG_PROCESSING_ERROR - Image processing errors"
echo "     💾 IMG_PROC_1 - Image processing start"
echo ""
echo "📊 ERROR DETECTION STRATEGY:"
echo ""
echo "   1. Each component has unique emoji prefixes for easy identification"
echo "   2. Step-by-step execution tracking in main capture loop"
echo "   3. Enhanced traceback analysis with file/line detection"
echo "   4. Specific NumPy error pattern detection"
echo ""
echo "🚀 NEXT STEPS:"
echo ""
echo "   1. Push this debug version to your Pi"
echo "   2. Run: ./scripts/start_capture.sh"
echo "   3. Look for the emoji-prefixed error messages"
echo "   4. The exact error source will be clearly identified"
echo ""
echo "   The error will show patterns like:"
echo "     🚨 CAPTURE_LOOP_ERROR: The truth value..."
echo "     🔥 NUMPY_ERROR_LINE_5: ...ambiguous..."
echo "     🎯 PROBLEM_FILE_LINE_3: ...gps_controller.py..."
echo ""
echo "   This will pinpoint EXACTLY where the NumPy error occurs!"
echo ""
echo "Backup location: $BACKUP_DIR"
echo "========================================="
