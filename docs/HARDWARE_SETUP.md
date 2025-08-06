# BathyCat Seabed Imager - Hardware Setup Guide

This guide covers the physical assembly and configuration of the BathyCat Seabed Imager hardware components.

## Table of Contents

1. [Component Overview](#component-overview)
2. [Assembly Instructions](#assembly-instructions)
3. [Marine Integration](#marine-integration)
4. [Power System Design](#power-system-design)
5. [Camera Deployment](#camera-deployment)
6. [GPS Configuration](#gps-configuration)
7. [Storage Setup](#storage-setup)
8. [Enclosure and Weatherproofing](#enclosure-and-weatherproofing)

---

## Component Overview

### Primary Components

| Component | Specifications | Purpose |
|-----------|---------------|---------|
| **Raspberry Pi 4 Model B (4GB)** | ARM Cortex-A72, 4GB RAM, USB 3.0 | Main processing unit |
| **StellarHD USB Camera** | 1080p@30fps, USB 3.0, IP67 rated | Underwater imaging |
| **512GB SSD Kit** | USB 3.0 SATA adapter, 512GB capacity | High-speed storage |
| **Adafruit Ultimate GPS HAT** | GPS/GLONASS, PPS output, battery backup | Position and time sync |

### Supporting Hardware

- **Heat Sinks**: For Raspberry Pi CPU cooling
- **MicroSD Card**: 32GB Class 10 for OS
- **USB Cables**: Marine-grade extensions
- **Power Supply**: 12V to 5V marine converter
- **Enclosure**: IP67+ rated waterproof case

---

## Assembly Instructions

### Step 1: Raspberry Pi Preparation

1. **Install Heat Sinks**
   ```
   - Clean CPU and RAM chips with isopropyl alcohol
   - Apply thermal compound if not pre-applied on heat sinks
   - Attach heat sinks to CPU, GPU, and RAM chips
   - Press firmly and ensure good contact
   ```

2. **Install MicroSD Card**
   ```
   - Insert pre-flashed Raspberry Pi OS card
   - Ensure card is fully seated
   - Note: Card will extend slightly from slot
   ```

### Step 2: GPS HAT Installation

1. **Pre-Installation Check**
   ```
   - Verify GPIO pins are straight and undamaged
   - Check GPS HAT for any shipping damage
   - Ensure antenna connector is secure
   ```

2. **Installation Process**
   ```
   - Power down Raspberry Pi completely
   - Align GPS HAT with GPIO header (pin 1 to pin 1)
   - Press down evenly until fully seated
   - Do not force - should slide on easily
   - Verify no pins are bent or missed
   ```

3. **GPS Antenna Connection**
   ```
   - Connect active GPS antenna to uFL connector
   - Ensure connector is firmly seated (you should feel/hear click)
   - Route antenna cable to prevent stress on connector
   ```

### Step 3: Storage Connection

1. **SSD Preparation**
   ```
   - Remove SSD from packaging
   - Connect to USB 3.0 SATA adapter
   - Ensure SATA connections are secure
   ```

2. **USB Connection**
   ```
   - Connect SSD adapter to USB 3.0 port (blue port)
   - Use shorter USB cable to minimize power loss
   - Secure cable to prevent disconnection during operation
   ```

### Step 4: Camera Connection

1. **Camera Inspection**
   ```
   - Check camera housing for damage
   - Verify lens is clean and unscratched
   - Test USB connector for secure fit
   ```

2. **USB Connection**
   ```
   - Connect camera to remaining USB 3.0 port
   - If using extension cable, use marine-grade rated cable
   - Test connection security with gentle tugging
   ```

---

## Marine Integration

### Vessel Installation Considerations

1. **Location Selection**
   ```
   Criteria for installation location:
   - Protected from spray and boarding seas
   - Good ventilation for heat dissipation
   - Access to vessel's 12V power system
   - Close to camera deployment point
   - Accessible for maintenance
   ```

2. **Mounting Strategy**
   ```
   - Use marine-grade stainless steel hardware
   - Provide shock mounting for rough seas
   - Ensure enclosure can drain condensation
   - Allow for thermal expansion
   ```

### Hull Penetration (Camera Deployment)

1. **Through-Hull Fitting**
   ```
   - Use marine-grade through-hull fitting
   - Apply marine sealant generously
   - Install backing plate for structural integrity
   - Consider ball valve for service access
   ```

2. **Camera Positioning**
   ```
   - Mount camera to view seabed perpendicular to vessel motion
   - Typical depth: 2-5 feet below hull
   - Ensure camera faces down at 90° angle
   - Provide strain relief for cable
   ```

---

## Power System Design

### 12V to 5V Conversion

1. **Converter Selection**
   ```
   Specifications:
   - Input: 9-30V DC (accommodates voltage variation)
   - Output: 5V DC, 4A minimum
   - Efficiency: >85%
   - Protection: Over-current, over-voltage, reverse polarity
   - Marine grade: Conformal coating, sealed housing
   ```

2. **Installation**
   ```
   - Mount converter near power source
   - Use marine-grade wire (tinned copper)
   - Install inline fuse (5A) at source
   - Provide strain relief at all connections
   - Use waterproof connectors
   ```

### Power Consumption

| Component | Typical Draw | Peak Draw |
|-----------|-------------|-----------|
| Raspberry Pi 4 | 2.5A @ 5V | 3.0A @ 5V |
| GPS HAT | 0.1A @ 5V | 0.2A @ 5V |
| StellarHD Camera | 0.5A @ 5V | 0.8A @ 5V |
| SSD Storage | 0.3A @ 5V | 0.5A @ 5V |
| **Total System** | **3.4A @ 5V** | **4.5A @ 5V** |

### Backup Power (Optional)

1. **UPS Integration**
   ```
   - Marine-grade UPS with 12V input
   - Minimum 30-minute runtime at full load
   - Automatic switchover capability
   - Low-battery shutdown signal
   ```

2. **Implementation**
   ```python
   # Add to config.json
   {
     "power_monitoring": {
       "enabled": true,
       "low_battery_action": "safe_shutdown",
       "shutdown_voltage": 11.5
     }
   }
   ```

---

## Camera Deployment

### Underwater Housing

1. **Housing Inspection**
   ```
   Pre-deployment checklist:
   - O-ring condition and lubrication
   - Housing integrity (no cracks)
   - Lens clarity
   - Cable seal integrity
   - Pressure test (if possible)
   ```

2. **Installation**
   ```
   - Apply thin layer of silicone grease to O-rings
   - Ensure no debris on sealing surfaces
   - Tighten housing evenly (don't over-tighten)
   - Perform final inspection of all seals
   ```

### Mounting Configuration

1. **Standard Configuration**
   ```
   Mounting Details:
   - Height above seabed: 1-3 meters (adjustable)
   - Viewing angle: 90° downward
   - Field of view: Adjust based on altitude and requirements
   - Stabilization: Consider gimbal for rough conditions
   ```

2. **Cable Management**
   ```
   - Use marine-grade cable glands
   - Provide drip loops at all penetrations
   - Secure cable every 12 inches
   - Avoid sharp bends (min 6x cable diameter)
   - Include service loop at camera end
   ```

### Focus and Calibration

1. **Underwater Focus**
   ```
   - Focus should be set for underwater use
   - Water magnifies by ~25% (objects appear closer)
   - Test focus at operational depth
   - Consider adjustable focus mechanism
   ```

2. **Image Quality Optimization**
   ```python
   # Camera settings for underwater use
   {
     "camera_contrast": 60,        # Increased for murky water
     "camera_saturation": 70,      # Enhance color definition
     "camera_auto_white_balance": false,
     "camera_white_balance": 4000, # Adjust for water color
     "camera_auto_exposure": true  # Handle changing light
   }
   ```

---

## GPS Configuration

### Antenna Placement

1. **Optimal Positioning**
   ```
   Location requirements:
   - Clear view of sky (minimal obstructions)
   - Away from metal structures when possible
   - Protected from physical damage
   - Accessible for maintenance
   - Minimum 3 feet from electronics
   ```

2. **Mounting Options**
   ```
   - Magnetic mount (removable)
   - Through-deck mount (permanent)
   - Rail mount (adjustable)
   - Mast mount (highest position)
   ```

### PPS (Pulse Per Second) Setup

1. **Hardware Connection**
   ```
   - PPS signal available on GPIO pin
   - Used for precise time synchronization
   - Critical for correlating with other data streams
   - Requires kernel PPS support
   ```

2. **Software Configuration**
   ```bash
   # Enable PPS in device tree
   echo "dtoverlay=pps-gpio,gpiopin=4" >> /boot/config.txt
   
   # Test PPS signal
   sudo ppstest /dev/pps0
   ```

---

## Storage Setup

### SSD Configuration

1. **Filesystem Selection**
   ```
   Recommended: ext4
   - Good performance for sequential writes
   - Reliable journaling
   - Wide compatibility
   - Good for image file storage
   ```

2. **Mount Options**
   ```bash
   # Optimal mount options for imaging
   UUID=your-ssd-uuid /media/ssd ext4 defaults,noatime,commit=60 0 2
   
   # noatime: Improves write performance
   # commit=60: Reduces sync frequency
   ```

### Directory Structure

```
/media/ssd/bathycat/
├── images/          # Main image storage
│   ├── 20250805_08/ # Session directories (YYYYMMDD_HH)
│   ├── 20250805_09/
│   └── 20250805_10/
├── metadata/        # JSON metadata files
├── previews/        # Small preview images
├── logs/           # Application logs
└── exports/        # Compressed data for transfer
```

### Performance Optimization

1. **Write Performance**
   ```bash
   # Check SSD performance
   sudo hdparm -t /dev/sda1
   
   # Optimize for sequential writes
   echo deadline > /sys/block/sda/queue/scheduler
   ```

2. **Monitoring**
   ```python
   # Storage monitoring in application
   def monitor_storage_health():
       # Check free space
       # Monitor write speeds
       # Track I/O errors
       # Alert on threshold breach
   ```

---

## Enclosure and Weatherproofing

### Enclosure Selection

1. **Requirements**
   ```
   Specifications:
   - IP67 minimum (IP68 preferred)
   - Operating temperature: -10°C to +60°C
   - UV resistant materials
   - Corrosion resistant hardware
   - Adequate internal volume
   - Mounting provisions
   ```

2. **Recommended Features**
   ```
   - Clear lid for status LED visibility
   - Multiple cable entry points
   - Internal mounting posts
   - Pressure equalization valve
   - Removable internal tray
   ```

### Waterproofing Strategy

1. **Cable Penetrations**
   ```
   Best practices:
   - Use marine-grade cable glands
   - Apply thread sealant on threaded connections
   - Install from inside enclosure when possible
   - Create drip loops outside enclosure
   - Use strain relief on all cables
   ```

2. **Seal Maintenance**
   ```
   Regular maintenance:
   - Inspect O-rings every 6 months
   - Replace O-rings annually
   - Clean and lubricate sealing surfaces
   - Check for UV degradation
   - Test seal integrity periodically
   ```

### Thermal Management

1. **Heat Dissipation**
   ```
   - Install heat sinks on all major chips
   - Consider small fan for active cooling
   - Use thermal interface material
   - Ensure air circulation paths
   - Monitor CPU temperature
   ```

2. **Condensation Prevention**
   ```
   - Include desiccant packs
   - Ensure vapor barriers on penetrations
   - Use breathable but waterproof membranes
   - Monitor internal humidity
   - Provide drainage for any intrusion
   ```

### Installation Testing

1. **Pressure Testing**
   ```
   - Seal enclosure completely
   - Submerge to operational depth + safety margin
   - Check for bubbles or water intrusion
   - Test for specified duration
   - Inspect all seals after test
   ```

2. **Operational Testing**
   ```
   - Power system under load
   - GPS acquisition test
   - Camera operation test
   - Storage write test
   - Temperature monitoring
   - Vibration resistance test
   ```

---

## Integration Checklist

### Pre-Deployment Verification

- [ ] All connections secure and waterproofed
- [ ] GPS acquiring satellites within 5 minutes
- [ ] Camera producing clear images at target resolution
- [ ] Storage accessible with adequate free space
- [ ] Power system providing stable 5V under load
- [ ] Enclosure properly sealed and tested
- [ ] All cables secured with appropriate strain relief
- [ ] System boots and starts service automatically

### Post-Installation Testing

- [ ] 24-hour continuous operation test
- [ ] Power cycle recovery test
- [ ] GPS time synchronization verification
- [ ] Image capture rate verification
- [ ] Storage performance test
- [ ] Temperature monitoring under load
- [ ] Waterproof integrity verification

### Maintenance Schedule

| Interval | Tasks |
|----------|-------|
| Daily | Check system status, verify operation |
| Weekly | Download data, check storage space |
| Monthly | Clean camera lens, check connections |
| Quarterly | Inspect seals, test GPS accuracy |
| Annually | Replace O-rings, full system test |

---

For technical support or questions about hardware setup, refer to the troubleshooting guide or create an issue in the project repository.
