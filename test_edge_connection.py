#!/usr/bin/env python3
"""
Test script to verify lines connect properly to class edges
"""

import tkinter as tk
from mermaid_diagram_tool import ClassBox, Relationship, MermaidDiagramTool

def test_edge_connection():
    print("🧪 Testing Edge Connection")
    print("=" * 30)
    
    root = tk.Tk()
    root.title("Edge Connection Test")
    root.geometry("800x600")
    
    canvas = tk.Canvas(root, bg="white", width=800, height=600)
    canvas.pack(fill=tk.BOTH, expand=True)
    
    # Create mock tool
    class MockTool:
        def __init__(self):
            self.relationships = []
            self.classes = []
            
        def update_relationships(self):
            for rel in self.relationships:
                rel.update_position()
                
        def update_status(self, message):
            print(f"📊 Status: {message}")
    
    tool = MockTool()
    
    print("📦 Creating classes in different positions...")
    
    # Create classes in various positions to test edge connections
    center_class = ClassBox(canvas, 350, 250, "Center", tool)
    center_class.attributes = ["+id: int"]
    
    top_class = ClassBox(canvas, 350, 100, "Top", tool)
    top_class.attributes = ["+value: String"]
    
    bottom_class = ClassBox(canvas, 350, 400, "Bottom", tool)
    bottom_class.attributes = ["+data: Object"]
    
    left_class = ClassBox(canvas, 150, 250, "Left", tool)
    left_class.attributes = ["+count: int"]
    
    right_class = ClassBox(canvas, 550, 250, "Right", tool)
    right_class.attributes = ["+flag: boolean"]
    
    # Create all visuals
    classes = [center_class, top_class, bottom_class, left_class, right_class]
    for cls in classes:
        cls.create_visual()
        tool.classes.append(cls)
    
    print("🔗 Creating relationships to test edge connections...")
    
    # Create relationships in all directions
    rel1 = Relationship(canvas, center_class, top_class, "inheritance", tool)
    rel2 = Relationship(canvas, center_class, bottom_class, "composition", tool)
    rel3 = Relationship(canvas, center_class, left_class, "aggregation", tool)
    rel4 = Relationship(canvas, center_class, right_class, "association", tool)
    
    # Create diagonal relationships
    rel5 = Relationship(canvas, top_class, right_class, "dependency", tool)
    rel6 = Relationship(canvas, left_class, bottom_class, "realization", tool)
    
    tool.relationships.extend([rel1, rel2, rel3, rel4, rel5, rel6])
    
    print("✅ Edge connection test setup complete!")
    print(f"   Created {len(classes)} classes")
    print(f"   Created {len(tool.relationships)} relationships")
    
    # Add instructions
    canvas.create_text(400, 50, text="Edge Connection Test", font=("Arial", 16, "bold"))
    canvas.create_text(400, 550, text="Lines should connect to class edges, not centers", font=("Arial", 12))
    canvas.create_text(400, 570, text="Arrow heads should be visible at connection points", font=("Arial", 10))
    
    print("\n📋 What to verify:")
    print("   • Lines connect to the edges of class boxes (not centers)")
    print("   • Arrow heads are visible at the connection points")
    print("   • No lines pass through the middle of classes")
    print("   • Connections look clean and professional")
    print("   • Different directions (up, down, left, right, diagonal) all work")
    print("   • Drag classes around - connections should update properly")
    print("   • Close window when done testing")
    
    root.mainloop()

if __name__ == "__main__":
    test_edge_connection()