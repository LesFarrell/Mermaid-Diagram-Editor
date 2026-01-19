#!/usr/bin/env python3
"""
Test script to verify canvas panning functionality
"""

import tkinter as tk
from mermaid_diagram_tool import MermaidDiagramTool

def test_panning():
    print("🧪 Testing Canvas Panning")
    print("=" * 40)
    
    app = MermaidDiagramTool()
    
    # Create several classes to test panning
    print("📦 Creating classes for panning test...")
    
    # Add classes in different positions
    for i in range(6):
        app.add_class()
    
    # Add some content to make them more visible
    if len(app.classes) >= 3:
        app.classes[0].attributes = ["+id: int", "+name: String"]
        app.classes[0].methods = ["+getId(): int"]
        
        app.classes[1].attributes = ["+value: double"]
        app.classes[1].methods = ["+getValue(): double"]
        
        app.classes[2].attributes = ["+data: Object"]
        
        # Recreate visuals with content
        for cls in app.classes[:3]:
            cls.create_visual()
    
    # Create some relationships
    print("🔗 Creating relationships...")
    if len(app.classes) >= 4:
        from mermaid_diagram_tool import Relationship
        
        rel1 = Relationship(app.canvas, app.classes[0], app.classes[1], "inheritance", app)
        rel2 = Relationship(app.canvas, app.classes[1], app.classes[2], "composition", app)
        rel3 = Relationship(app.canvas, app.classes[2], app.classes[3], "association", app)
        
        app.relationships.extend([rel1, rel2, rel3])
    
    # Update scroll region
    app.update_scroll_region()
    
    print("✅ Test setup complete!")
    print(f"   Created {len(app.classes)} classes")
    print(f"   Created {len(app.relationships)} relationships")
    
    # Add instructions to canvas
    instructions = app.canvas.create_text(
        600, 30,
        text="Canvas Panning Test",
        font=("Arial", 16, "bold"),
        fill="blue"
    )
    
    instructions2 = app.canvas.create_text(
        600, 55,
        text="Click and drag on empty space to pan the entire diagram",
        font=("Arial", 12),
        fill="darkblue"
    )
    
    print("\n📋 Testing checklist:")
    print("   ✓ Click on empty space (not on a class)")
    print("   ✓ Drag mouse while holding button")
    print("   ✓ All classes move together")
    print("   ✓ All relationships move with classes")
    print("   ✓ Release mouse to stop panning")
    print("   ✓ Status bar shows 'Pan mode' while dragging")
    print("   ✓ Can still select and drag individual classes")
    print("   ✓ Scroll region updates after panning")
    print("\n💡 Try:")
    print("   • Click and drag on empty space to pan")
    print("   • Pan the diagram to different positions")
    print("   • Click on a class to select it (stops panning)")
    print("   • Drag a single class (not panning)")
    print("   • Pan, then zoom, then pan again")
    print("   • Create new classes after panning")
    print("\n🎯 Expected behavior:")
    print("   • Empty space click = Pan entire diagram")
    print("   • Class click = Select and drag that class only")
    print("   • Smooth movement of all elements together")
    print("   • Relationships stay connected during pan")
    
    app.run()

if __name__ == "__main__":
    test_panning()
