#!/usr/bin/env python3
"""
Simple test to verify the visual positioning fixes
"""

import tkinter as tk
from mermaid_diagram_tool import ClassBox, Relationship, MermaidDiagramTool

def test_positioning():
    print("🧪 Testing Visual Positioning Fixes")
    print("=" * 50)
    
    # Create a simple test window
    root = tk.Tk()
    root.title("Visual Test")
    root.geometry("800x600")
    
    canvas = tk.Canvas(root, bg="white", width=800, height=600)
    canvas.pack(fill=tk.BOTH, expand=True)
    
    # Create a mock tool for testing
    class MockTool:
        def __init__(self):
            self.relationships = []
            
        def update_relationships(self):
            print("📍 Updating relationship positions...")
            for rel in self.relationships:
                rel.update_position()
    
    tool = MockTool()
    
    # Create test classes
    print("📦 Creating test classes...")
    class1 = ClassBox(canvas, 100, 100, "TestClass1", tool)
    class1.attributes = ["attr1", "attr2"]
    class1.methods = ["method1", "method2"]
    
    class2 = ClassBox(canvas, 300, 200, "TestClass2", tool)
    class2.attributes = ["attr3"]
    class2.methods = ["method3"]
    
    # Recreate visuals with content
    for cls in [class1, class2]:
        cls.canvas.delete(cls.rect)
        cls.canvas.delete(cls.name_text)
        cls.canvas.delete(cls.sep_line)
        cls.create_visual()
    
    # Create test relationship
    print("🔗 Creating test relationship...")
    rel = Relationship(canvas, class1, class2, "inheritance")
    tool.relationships.append(rel)
    
    print("✅ Visual test setup complete!")
    print("📋 Instructions:")
    print("   • Text should be positioned correctly within class boxes")
    print("   • Relationship line should connect to class edges, not centers")
    print("   • Try dragging classes - relationships should move with them")
    print("   • Close window when done testing")
    
    # Add some test labels
    canvas.create_text(400, 50, text="Visual Positioning Test", font=("Arial", 16, "bold"))
    canvas.create_text(400, 70, text="Drag classes to test relationship updates", font=("Arial", 12))
    
    root.mainloop()

if __name__ == "__main__":
    test_positioning()