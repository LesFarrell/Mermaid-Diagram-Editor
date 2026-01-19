#!/usr/bin/env python3
"""Test zoom level restoration"""

import os
import json

# Set encoding for output
import sys
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

from mermaid_diagram_tool import MermaidDiagramTool

def test_zoom_restore():
    """Test that zoom level is correctly restored when loading"""
    
    test_file = "test.md"
    position_file = test_file + ".positions.json"
    
    if not os.path.exists(test_file):
        print(f"Test file not found: {test_file}")
        return False
    
    if not os.path.exists(position_file):
        print(f"Position file not found: {position_file}")
        return False
    
    # Read saved zoom level
    with open(position_file, 'r') as f:
        positions = json.load(f)
    
    saved_zoom = positions.get('zoom_level', 1.0)
    print(f"Saved zoom level: {saved_zoom} ({int(saved_zoom * 100)}%)")
    
    # Create app and load diagram
    print("\nLoading diagram...")
    app = MermaidDiagramTool()
    
    # Read file
    with open(test_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    mermaid_code = app.extract_mermaid_code(content)
    
    # Load positions
    positions = app.load_positions(test_file)
    
    # Set zoom level
    if positions and "zoom_level" in positions:
        app.set_zoom_level(positions["zoom_level"])
    
    # Parse diagram
    app.parse_mermaid(mermaid_code, apply_auto_layout=(positions is None))
    
    # Apply positions
    if positions:
        app.apply_positions(positions, skip_zoom=True)
    
    # Check if zoom level matches
    actual_zoom = app.zoom_level
    print(f"Loaded zoom level: {actual_zoom} ({int(actual_zoom * 100)}%)")
    
    if abs(actual_zoom - saved_zoom) < 0.001:
        print("\n✓ Zoom level restored correctly!")
        
        # Check if classes were created at correct zoom
        if app.classes:
            first_class = app.classes[0]
            print(f"\nFirst class dimensions:")
            print(f"  Width: {first_class.width:.1f}")
            print(f"  Height: {first_class.height:.1f}")
            print(f"  Position: ({first_class.x:.1f}, {first_class.y:.1f})")
        
        return True
    else:
        print(f"\n✗ Zoom level mismatch!")
        print(f"  Expected: {saved_zoom}")
        print(f"  Got: {actual_zoom}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Zoom Level Restoration")
    print("=" * 60)
    test_zoom_restore()
