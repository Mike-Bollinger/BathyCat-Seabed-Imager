#!/usr/bin/env python3
"""
GPS Diagnostic Tool
===================

Real-time GPS status monitor with satellite visibility and signal quality.
Helps diagnose GPS fix acquisition issues.
"""

import serial
import pynmea2
import time
import sys
from datetime import datetime
from collections import defaultdict


def parse_gsa_sats(sentence):
    """Extract satellite IDs from GSA sentence."""
    sats = []
    for i in range(1, 13):  # GSA has up to 12 satellite slots
        sat_field = f'sv_id{i:02d}'
        if hasattr(sentence, sat_field):
            sat_id = getattr(sentence, sat_field)
            if sat_id:
                sats.append(sat_id)
    return sats


def parse_gsv_sats(sentence):
    """Extract satellite signal info from GSV sentence."""
    sats = []
    for i in range(1, 5):  # GSV has up to 4 satellites per sentence
        try:
            sat_num = getattr(sentence, f'sv_prn_num_{i}', None)
            elevation = getattr(sentence, f'elevation_deg_{i}', None)
            azimuth = getattr(sentence, f'azimuth_{i}', None)
            snr = getattr(sentence, f'snr_{i}', None)
            
            if sat_num:
                sats.append({
                    'prn': sat_num,
                    'elevation': int(elevation) if elevation else 0,
                    'azimuth': int(azimuth) if azimuth else 0,
                    'snr': int(snr) if snr else 0
                })
        except (AttributeError, ValueError):
            pass
    return sats


def main():
    print("=" * 70)
    print("GPS DIAGNOSTIC TOOL")
    print("=" * 70)
    print("\nConnecting to GPS on /dev/ttyAMA0...")
    
    try:
        ser = serial.Serial('/dev/ttyAMA0', 9600, timeout=1.0)
        print("✓ GPS connected\n")
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        return 1
    
    satellites_in_view = {}
    satellites_used = []
    last_gga = None
    last_rmc = None
    sentence_count = 0
    start_time = time.time()
    
    print("Reading GPS data (Ctrl+C to stop)...\n")
    print("-" * 70)
    
    try:
        while True:
            try:
                line = ser.readline().decode('ascii', errors='ignore').strip()
                if not line:
                    continue
                
                sentence_count += 1
                parsed = pynmea2.parse(line)
                
                # Update satellite visibility from GSV
                if isinstance(parsed, pynmea2.GSV):
                    for sat in parse_gsv_sats(parsed):
                        satellites_in_view[sat['prn']] = sat
                
                # Update satellites in use from GSA
                elif isinstance(parsed, pynmea2.GSA):
                    satellites_used = parse_gsa_sats(parsed)
                
                # Track position fix status
                elif isinstance(parsed, pynmea2.GGA):
                    last_gga = parsed
                
                elif isinstance(parsed, pynmea2.RMC):
                    last_rmc = parsed
                
                # Print status every 2 seconds
                if sentence_count % 20 == 0:
                    elapsed = int(time.time() - start_time)
                    
                    print(f"\r{' ' * 70}\r", end='')  # Clear line
                    print(f"[{elapsed:03d}s] ", end='')
                    
                    # Position status
                    if last_gga:
                        qual = int(last_gga.gps_qual) if last_gga.gps_qual else 0
                        num_sats = int(last_gga.num_sats) if last_gga.num_sats else 0
                        
                        if qual > 0:
                            print(f"✓ FIX (Q:{qual}, Sats:{num_sats}) ", end='')
                            if last_gga.latitude and last_gga.longitude:
                                lat = float(last_gga.latitude)
                                lon = float(last_gga.longitude)
                                print(f"Pos:{lat:.4f},{lon:.4f}", end='')
                        else:
                            print(f"✗ NO FIX (Sats:{num_sats})", end='')
                    
                    # RMC status
                    if last_rmc:
                        status = last_rmc.status
                        if status == 'A':
                            print(f" RMC:ACTIVE", end='')
                        else:
                            print(f" RMC:VOID", end='')
                    
                    # Satellite summary
                    total_visible = len(satellites_in_view)
                    total_used = len([s for s in satellites_used if s])
                    print(f" | Visible:{total_visible} Used:{total_used}", end='')
                    
                    # Signal strength summary
                    if satellites_in_view:
                        avg_snr = sum(s['snr'] for s in satellites_in_view.values() if s['snr'] > 0)
                        if avg_snr > 0:
                            avg_snr = avg_snr / len([s for s in satellites_in_view.values() if s['snr'] > 0])
                            print(f" SNR:{avg_snr:.1f}", end='')
                    
                    sys.stdout.flush()
                
                # Detailed satellite report every 10 seconds
                if sentence_count % 100 == 0 and satellites_in_view:
                    print("\n\n" + "=" * 70)
                    print(f"SATELLITE DETAILS ({len(satellites_in_view)} visible)")
                    print("=" * 70)
                    print(f"{'PRN':<6} {'Elevation':<12} {'Azimuth':<10} {'SNR':<8} {'Status'}")
                    print("-" * 70)
                    
                    for prn, sat in sorted(satellites_in_view.items()):
                        used = '✓ USED' if prn in satellites_used else '  tracking'
                        snr_bar = '█' * (sat['snr'] // 5) if sat['snr'] > 0 else ''
                        print(f"{prn:<6} {sat['elevation']:>3}°{' '*8} {sat['azimuth']:>3}°{' '*6} "
                              f"{sat['snr']:>2} dB  {snr_bar:<10} {used}")
                    
                    print("=" * 70 + "\n")
            
            except pynmea2.ParseError:
                pass  # Ignore parse errors
            except UnicodeDecodeError:
                pass  # Ignore decode errors
            except Exception as e:
                print(f"\nError processing sentence: {e}")
    
    except KeyboardInterrupt:
        print("\n\n" + "=" * 70)
        print("FINAL SUMMARY")
        print("=" * 70)
        print(f"Runtime: {int(time.time() - start_time)}s")
        print(f"Sentences processed: {sentence_count}")
        print(f"Satellites visible: {len(satellites_in_view)}")
        print(f"Satellites used: {len([s for s in satellites_used if s])}")
        
        if last_gga:
            qual = int(last_gga.gps_qual) if last_gga.gps_qual else 0
            print(f"Final fix quality: {qual}")
        
        print("\nDIAGNOSTIC RECOMMENDATIONS:")
        print("-" * 70)
        
        if len(satellites_in_view) == 0:
            print("❌ NO SATELLITES VISIBLE")
            print("   - Check antenna connection to GPS HAT")
            print("   - Verify GPS HAT is properly seated on GPIO pins")
            print("   - Try moving to different outdoor location")
            print("   - Check for metal obstructions blocking sky view")
            print("   - Consider GPS HAT may be faulty")
        
        elif len(satellites_in_view) < 4:
            print(f"⚠️  INSUFFICIENT SATELLITES ({len(satellites_in_view)} visible, need 4+)")
            print("   - Move to location with clearer sky view")
            print("   - Avoid buildings, trees, and metal structures")
            print("   - Wait longer for satellites to be acquired")
        
        elif len([s for s in satellites_used if s]) == 0:
            print(f"⚠️  SATELLITES VISIBLE BUT NOT LOCKED ({len(satellites_in_view)} visible)")
            print("   - Signal strength may be too weak")
            print("   - Check SNR values (should be 20+ dB for good lock)")
            print("   - Battery in GPS HAT may help faster acquisition")
            print("   - Continue waiting - initial lock can take 5-15 minutes")
        
        else:
            print(f"✓ GPS appears to be working ({len([s for s in satellites_used if s])} sats locked)")
        
        print("=" * 70)
    
    finally:
        ser.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
