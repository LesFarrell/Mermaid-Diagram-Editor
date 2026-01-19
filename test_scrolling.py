#!/usr/bin/env python3
"""
Test script to verify horizontal and vertical scrolling works properly
when classes are moved off screen
"""

import tkinter as tk
from mermaid_diagram_tool import MermaidDiagramTool

def test_scrolling():
    print("🧪 Testing Scrolling Functionality")
    print("=" * 40)
    
    app = MermaidDiagramTool()
    
    # Create several classes in different positions
    print("📦 Creating classes in various positions...")
    
    # Classes near edges
    class1 = app.classes[0] if app.classes else None
    
    # Add more classes
    for i in range(5):
        app.add_class()
    
    # Position some classes near the edges
    if len(app.classes) >= 4:
        app.classes[0].x = 50
        app.classes[0].y = 50
        
        app.classes[1].x = 1500
        app.classes[1].y = 50
        
        app.classes[2].x = 50
        app.classes[2].y = 1000
        
        app.classes[3].x = 1500
        app.classes[3].y = 1000
        
        # Recreate visuals at new positions
        for cls in app.classes[:4]:
            cls.create_visual()
    
    # Create some relationships
    print("🔗 Creating relationships...")
    if len(app.classes) >= 4:
        from mermaid_diagram_tool import Relationship
        
        rel1 = Relationship(app.canvas, app.classes[0], app.classes[1], "inheritance", app)
        rel2 = Relationship(app.canvas, app.classes[2], app.classes[3], "composition", app)
        rel3 = Relationship(app.canvas, app.classes[0], app.classes[2], "association", app)
        
        app.relationships.extend([rel1, rel2, rel3])
    
    # Update scroll region
    app.update_scroll_region()
    
    print("✅ Test setup complete!")
    print(f"   Created {len(app.classes)} classes")
    print(f"   Created {len(app.relationships)} relationships")
    
    # Add instructions to canvas
    instructions = app.canvas.create_text(
        400, 20,
        text="Scrolling Test - Drag classes off screen to test scrolling",
        font=("Arial", 14, "bold"),
        fill="blue"
    )
    
    instructions2 = app.canvas.create_text(
        400, 45,
        text="Classes are positioned at edges - use scrollbars to navigate",
        font=("Arial", 10),
        fill="darkblue"
    )
    
    print("\n📋 Testing checklist:")
    print("   ✓ Horizontal scrollbar appears and works")
    print("   ✓ Vertical scrollbar appears and works")
    print("   ✓ Drag classes beyond visible area - scrollbars update")
    print("   ✓ Scroll region expands automatically")
    print("   ✓ Can scroll to see all classes")
    print("   ✓ Relationships update when scrolling")
    print("\n💡 Try:")
    print("   • Drag a class far to the right")
    print("   • Drag a class far down")
    print("   • Use scrollbars to navigate to edge classes")
    print("   • Move classes back - scroll region should adjust")
    
    app.run()

if __name__ == "__main__":
    test_scrolling()
