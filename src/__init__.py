"""
BathyCat Seabed Imager
=====================

A modular system for capturing and geotagging images from autonomous surface vessels.

Main components:
- Camera: USB camera interface with OpenCV
- GPS: NMEA GPS parsing and validation
- Image Processing: EXIF metadata embedding
- Storage: USB drive management and cleanup
- Service: Main application coordinator

Author: BathyCat Project
License: MIT
"""

__version__ = "1.0.0"
__author__ = "BathyCat Project"