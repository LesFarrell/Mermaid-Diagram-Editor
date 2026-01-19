#!/usr/bin/env python3
"""Test zoom level saving and loading"""

import json
import os

def test_zoom_in_position_file():
    """Check if zoom level is saved in position file"""
    position_file = "test.md.positions.json"
    
    if not os.path.exists(position_file):
        print("Position file does not exist")
        return False
    
    try:
        with open(position_file, 'r') as f:
            data = json.load(f)
        
        if "zoom_level" in data:
            zoom = data["zoom_level"]
            print(f"Zoom level saved: {zoom}")
            print(f"Zoom percentage: {int(zoom * 100)}%")
            return True
        else:
            print("No zoom_level found in position file")
            return False
            
    except Exception as e:
        print(f"Error reading position file: {e}")
        return False

if __name__ == "__main__":
    print("Testing Zoom Level Save/Load")
    print("=" * 50)
    
    if test_zoom_in_position_file():
        print("\nZoom level IS being saved!")
        print("\nTo verify it's restored:")
        print("1. Note the current zoom level")
        print("2. Close the application")
        print("3. Reopen test.md")
        print("4. Check if zoom level matches")
    else:
        print("\nZoom level is NOT being saved")
