#!/usr/bin/env python3
"""
Test script to verify new features: spacing, auto-selection, and selectable relationships
"""

import tkinter as tk
from mermaid_diagram_tool import ClassBox, Relationship, MermaidDiagramTool

def test_new_features():
    print("🧪 Testing New Features")
    print("=" * 50)
    
    # Create a simple test window
    root = tk.Tk()
    root.title("New Features Test")
    root.geometry("1000x700")
    
    canvas = tk.Canvas(root, bg="white", width=1000, height=600)
    canvas.pack(fill=tk.BOTH, expand=True)
    
    # Create a mock tool for testing
    class MockTool:
        def __init__(self):
            self.relationships = []
            self.classes = []
            self.rel_type_var = tk.StringVar(value="association")
            
        def update_relationships(self):
            for rel in self.relationships:
                rel.update_position()
                
        def update_status(self, message):
            print(f"📊 Status: {message}")
    
    tool = MockTool()
    
    # Test improved spacing - create multiple classes
    print("📦 Creating test classes with improved spacing...")
    positions = [(150, 150), (450, 150), (750, 150), (150, 400), (450, 400)]
    
    for i, (x, y) in enumerate(positions):
        class_box = ClassBox(canvas, x, y, f"TestClass{i+1}", tool)
        class_box.attributes = [f"attr{i+1}"]
        class_box.methods = [f"method{i+1}"]
        
        # Recreate visual with content
        class_box.canvas.delete(class_box.rect)
        class_box.canvas.delete(class_box.name_text)
        class_box.canvas.delete(class_box.sep_line)
        class_box.create_visual()
        
        tool.classes.append(class_box)
    
    # Test selectable relationships
    print("🔗 Creating selectable relationships...")
    rel1 = Relationship(canvas, tool.classes[0], tool.classes[1], "inheritance", tool)
    rel2 = Relationship(canvas, tool.classes[1], tool.classes[2], "composition", tool)
    rel3 = Relationship(canvas, tool.classes[3], tool.classes[4], "aggregation", tool)
    
    tool.relationships.extend([rel1, rel2, rel3])
    
    # Auto-select the first class to demonstrate
    tool.classes[0].select()
    
    print("✅ Test setup complete!")
    print("📋 Test Instructions:")
    print("   • Classes are spaced better apart")
    print("   • First class is auto-selected (red border + corners)")
    print("   • Click on relationship lines to select them (they turn red)")
    print("   • Double-click relationships to change their type")
    print("   • Try clicking different elements to see selection behavior")
    print("   • Close window when done testing")
    
    # Add test labels
    canvas.create_text(500, 50, text="New Features Test", font=("Arial", 16, "bold"))
    canvas.create_text(500, 70, text="Better spacing • Auto-selection • Selectable relationships", font=("Arial", 12))
    canvas.create_text(500, 650, text="Click lines to select • Double-click lines to change type", font=("Arial", 10))
    
    root.mainloop()

if __name__ == "__main__":
    test_new_features()