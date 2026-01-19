#!/usr/bin/env python3
"""Test loading positions from file"""

import sys
import os

# Redirect to see debug output
print("🧪 Testing Position Loading")
print("=" * 50)

# Import the tool
from mermaid_diagram_tool import MermaidDiagramTool

# Create app instance
app = MermaidDiagramTool()

# Try to load test.md
test_file = "test.md"
if os.path.exists(test_file):
    print(f"\n📂 Loading {test_file}...")
    print("-" * 50)
    
    # Read the file
    with open(test_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract mermaid code
    mermaid_code = app.extract_mermaid_code(content)
    
    if mermaid_code:
        # Load positions
        positions = app.load_positions(test_file)
        
        # Parse diagram
        app.parse_mermaid(mermaid_code, apply_auto_layout=(positions is None))
        
        # Apply positions
        if positions:
            print("\n📍 Applying positions...")
            print("-" * 50)
            app.apply_positions(positions)
        else:
            print("\n⚠️  No positions to apply")
        
        print("\n✅ Test complete")
        print(f"📊 Loaded {len(app.classes)} classes")
    else:
        print("❌ No mermaid code found")
else:
    print(f"❌ File not found: {test_file}")

# Don't start the GUI
print("\n💡 Check the debug output above to see what happened")
