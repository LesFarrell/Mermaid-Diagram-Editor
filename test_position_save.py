#!/usr/bin/env python3
"""Test position saving functionality"""

import os
import json
import time

def test_position_file():
    """Check if position file exists and is being updated"""
    position_file = "test.md.positions.json"
    
    if not os.path.exists(position_file):
        print("❌ Position file does not exist")
        return False
    
    # Get file modification time
    mod_time = os.path.getmtime(position_file)
    mod_time_str = time.ctime(mod_time)
    
    print(f"✅ Position file exists: {position_file}")
    print(f"📅 Last modified: {mod_time_str}")
    
    # Read and validate content
    try:
        with open(position_file, 'r') as f:
            data = json.load(f)
        
        print(f"✅ Valid JSON format")
        print(f"📊 Zoom level: {data.get('zoom_level', 'N/A')}")
        print(f"📦 Number of classes: {len(data.get('classes', {}))}")
        
        if 'canvas_viewport' in data:
            print(f"🖼️  Canvas viewport saved: Yes")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Position Save Functionality")
    print("=" * 50)
    test_position_file()
    print("\n💡 To test auto-save:")
    print("   1. Open test.md in the application")
    print("   2. Move a class")
    print("   3. Run this test again to see updated timestamp")
