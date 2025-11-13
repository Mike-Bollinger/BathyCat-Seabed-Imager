#!/usr/bin/env python3
"""
Sequence Counter Diagnostic Script
Tests the exact sequence counter logic that's failing
"""

import json
import os
from datetime import datetime

# Test with the actual config file
config_path = '/home/bathyimager/BathyCat-Seabed-Imager/config/bathyimager_config.json'

print("=== SEQUENCE COUNTER DIAGNOSTIC ===")
print()

# 1. Test config loading
print("1. Testing config loading:")
try:
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    use_seq = config.get('use_sequence_counter', False)
    print(f"   use_sequence_counter from config: {use_seq} (type: {type(use_seq)})")
    
    if use_seq is True:
        print("   ✅ Config value is correct Python True")
    else:
        print(f"   ❌ Config value is wrong: {use_seq}")
        
except Exception as e:
    print(f"   ❌ Config loading failed: {e}")

print()

# 2. Test the actual storage condition logic
print("2. Testing storage condition logic:")
use_sequence_counter = config.get('use_sequence_counter', False)
sequence_counter = 162  # Example from logs

condition_result = use_sequence_counter and sequence_counter is not None
print(f"   use_sequence_counter: {use_sequence_counter}")
print(f"   sequence_counter: {sequence_counter}")
print(f"   sequence_counter is not None: {sequence_counter is not None}")
print(f"   Final condition: {use_sequence_counter} and {sequence_counter is not None} = {condition_result}")

if condition_result:
    print("   ✅ Should use provided sequence counter")
else:
    print("   ❌ Will use auto-generated counter")

print()

# 3. Test filename generation
print("3. Testing filename generation:")
timestamp = datetime.now()
date_part = timestamp.strftime('%Y%m%d')
time_part = timestamp.strftime('%H%M%S')
milliseconds = int(timestamp.microsecond / 1000)
filename_prefix = config.get('filename_prefix', 'bathyimager')

if condition_result:
    filename = f"{filename_prefix}_{date_part}-{time_part}-{milliseconds:03d}_{sequence_counter:05d}.jpg"
    print(f"   Using sequence counter: {filename}")
else:
    # Simulate auto counter (would normally be 1 for new timestamp)
    auto_counter = 1
    filename = f"{filename_prefix}_{date_part}-{time_part}-{milliseconds:03d}_{auto_counter:05d}.jpg"
    print(f"   Using auto counter: {filename}")

print()
print("=== DIAGNOSTIC COMPLETE ===")