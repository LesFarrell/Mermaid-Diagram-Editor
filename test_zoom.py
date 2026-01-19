#!/usr/bin/env python3
"""
Test script to verify zoom functionality with mouse wheel and buttons
"""

import tkinter as tk
from mermaid_diagram_tool import MermaidDiagramTool

def test_zoom():
    print("🧪 Testing Zoom Functionality")
    print("=" * 40)
    
    app = MermaidDiagramTool()
    
    # Create several classes to test zooming
    print("📦 Creating classes for zoom testing...")
    
    # Add classes
    for i in range(6):
        app.add_class()
    
    # Add some attributes and methods to make them more visible
    if len(app.classes) >= 3:
        app.classes[0].attributes = ["+id: int", "+name: String"]
        app.classes[0].methods = ["+getId(): int", "+getName(): String"]
        
        app.classes[1].attributes = ["+value: double", "+count: int"]
        app.classes[1].methods = ["+getValue(): double"]
        
        app.classes[2].attributes = ["+data: Object"]
        app.classes[2].methods = ["+getData(): Object", "+setData(obj: Object)"]
        
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
    print(f"   Initial zoom: {int(app.zoom_level * 100)}%")
    
    # Add instructions to canvas
    instructions = app.canvas.create_text(
        600, 30,
        text="Zoom Test - Use mouse wheel or toolbar buttons",
        font=("Arial", 14, "bold"),
        fill="blue"
    )
    
    print("\n📋 Testing checklist:")
    print("   ✓ Mouse wheel up zooms in")
    print("   ✓ Mouse wheel down zooms out")
    print("   ✓ + button zooms in")
    print("   ✓ - button zooms out")
    print("   ✓ Reset button returns to 100%")
    print("   ✓ Zoom level displayed in toolbar")
    print("   ✓ Zoom range limited (10% to 500%)")
    print("   ✓ All elements scale together")
    print("   ✓ Relationships scale with classes")
    print("   ✓ Scroll region updates after zoom")
    print("\n💡 Try:")
    print("   • Scroll mouse wheel to zoom in/out")
    print("   • Click + and - buttons in toolbar")
    print("   • Zoom in very close (500% max)")
    print("   • Zoom out very far (10% min)")
    print("   • Click Reset to return to 100%")
    print("   • Drag classes while zoomed")
    print("   • Create new classes while zoomed")
    
    app.run()

if __name__ == "__main__":
    test_zoom()
