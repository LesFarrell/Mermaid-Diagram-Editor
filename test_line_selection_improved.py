#!/usr/bin/env python3
"""
Test script to verify improved line selection with larger hit area
"""

import tkinter as tk
from mermaid_diagram_tool import MermaidDiagramTool

def test_line_selection():
    print("🧪 Testing Improved Line Selection")
    print("=" * 40)
    
    app = MermaidDiagramTool()
    
    # Create classes
    print("📦 Creating classes...")
    for i in range(4):
        app.add_class()
    
    # Add some content
    if len(app.classes) >= 3:
        app.classes[0].attributes = ["+id: int"]
        app.classes[1].attributes = ["+value: double"]
        app.classes[2].attributes = ["+data: Object"]
        
        for cls in app.classes[:3]:
            cls.create_visual()
    
    # Create relationships
    print("🔗 Creating relationships...")
    if len(app.classes) >= 4:
        from mermaid_diagram_tool import Relationship
        
        rel1 = Relationship(app.canvas, app.classes[0], app.classes[1], "inheritance", app)
        rel2 = Relationship(app.canvas, app.classes[1], app.classes[2], "composition", app)
        rel3 = Relationship(app.canvas, app.classes[2], app.classes[3], "association", app)
        rel4 = Relationship(app.canvas, app.classes[0], app.classes[3], "dependency", app)
        
        app.relationships.extend([rel1, rel2, rel3, rel4])
    
    app.update_scroll_region()
    
    print("✅ Test setup complete!")
    print(f"   Created {len(app.classes)} classes")
    print(f"   Created {len(app.relationships)} relationships")
    
    # Add instructions
    instructions = app.canvas.create_text(
        600, 30,
        text="Improved Line Selection Test",
        font=("Arial", 16, "bold"),
        fill="blue"
    )
    
    instructions2 = app.canvas.create_text(
        600, 55,
        text="Lines now have a 10-pixel selection tolerance",
        font=("Arial", 12),
        fill="darkblue"
    )
    
    print("\n📋 Testing checklist:")
    print("   ✓ Click near a line (not exactly on it)")
    print("   ✓ Line should be selected (turns red)")
    print("   ✓ Selection works within 10 pixels of line")
    print("   ✓ Double-click line to change type")
    print("   ✓ Delete key removes selected line")
    print("   ✓ Much easier to select lines now")
    print("\n💡 Try:")
    print("   • Click slightly off to the side of a line")
    print("   • Click near thin lines - should still select")
    print("   • Select different relationship types")
    print("   • Double-click to cycle through types")
    print("   • Delete selected relationships")
    print("\n🎯 Expected behavior:")
    print("   • Lines are easy to select")
    print("   • Don't need to click exactly on the line")
    print("   • 10-pixel tolerance makes selection forgiving")
    print("   • Selected line turns red")
    
    app.run()

if __name__ == "__main__":
    test_line_selection()
