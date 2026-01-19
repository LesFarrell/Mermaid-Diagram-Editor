#!/usr/bin/env python3
"""
Test script to verify relationship deselection when clicking other elements
"""

import tkinter as tk
from mermaid_diagram_tool import ClassBox, Relationship, MermaidDiagramTool

def test_deselection():
    print("🧪 Testing Relationship Deselection")
    print("=" * 50)
    
    # Create a simple test window
    root = tk.Tk()
    root.title("Deselection Test")
    root.geometry("800x600")
    
    canvas = tk.Canvas(root, bg="white", width=800, height=600)
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
    
    # Create test classes
    print("📦 Creating test classes...")
    class1 = ClassBox(canvas, 200, 150, "Class1", tool)
    class2 = ClassBox(canvas, 500, 150, "Class2", tool)
    class3 = ClassBox(canvas, 350, 350, "Class3", tool)
    
    for cls in [class1, class2, class3]:
        cls.attributes = ["attr1"]
        cls.methods = ["method1"]
        cls.canvas.delete(cls.rect)
        cls.canvas.delete(cls.name_text)
        cls.canvas.delete(cls.sep_line)
        cls.create_visual()
        tool.classes.append(cls)
    
    # Create test relationships
    print("🔗 Creating test relationships...")
    rel1 = Relationship(canvas, class1, class2, "inheritance", tool)
    rel2 = Relationship(canvas, class2, class3, "composition", tool)
    
    tool.relationships.extend([rel1, rel2])
    
    # Pre-select a relationship to test deselection
    rel1.select()
    
    print("✅ Test setup complete!")
    print("📋 Test Instructions:")
    print("   • First relationship is pre-selected (red line)")
    print("   • Click on a class - relationship should deselect")
    print("   • Click on another relationship - first should deselect")
    print("   • Click on empty canvas - everything should deselect")
    print("   • Press Escape - everything should deselect")
    print("   • Close window when done testing")
    
    # Add test labels
    canvas.create_text(400, 50, text="Deselection Test", font=("Arial", 16, "bold"))
    canvas.create_text(400, 70, text="Click different elements to test deselection", font=("Arial", 12))
    canvas.create_text(400, 550, text="Red relationship is pre-selected - try clicking other elements", font=("Arial", 10))
    
    # Bind canvas click for testing
    def canvas_click(event):
        # Check if clicked on a class
        clicked_class = None
        for class_box in tool.classes:
            if (class_box.x <= event.x <= class_box.x + class_box.width and
                class_box.y <= event.y <= class_box.y + class_box.height):
                clicked_class = class_box
                break
        
        # Deselect all classes
        for class_box in tool.classes:
            class_box.deselect()
        
        # Deselect all relationships
        for rel in tool.relationships:
            rel.deselect()
        
        # Select clicked class if any
        if clicked_class:
            clicked_class.select()
            tool.update_status(f"Selected class: {clicked_class.name}")
        else:
            tool.update_status("Clicked empty canvas - all deselected")
    
    canvas.bind("<Button-1>", canvas_click)
    
    # Bind escape key
    def on_key(event):
        if event.keysym == "Escape":
            for class_box in tool.classes:
                class_box.deselect()
            for rel in tool.relationships:
                rel.deselect()
            tool.update_status("Escape pressed - all deselected")
    
    root.bind("<Key>", on_key)
    root.focus_set()
    
    root.mainloop()

if __name__ == "__main__":
    test_deselection()