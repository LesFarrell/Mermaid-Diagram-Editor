#!/usr/bin/env python3
"""
Test script to verify line selection works and right-click class creation
"""

import tkinter as tk
from mermaid_diagram_tool import ClassBox, Relationship, MermaidDiagramTool

def test_line_selection_and_right_click():
    print("🧪 Testing Line Selection Fix & Right-Click Creation")
    print("=" * 50)
    
    # Create a simple test window
    root = tk.Tk()
    root.title("Line Selection & Right-Click Test")
    root.geometry("800x600")
    
    canvas = tk.Canvas(root, bg="white", width=800, height=600)
    canvas.pack(fill=tk.BOTH, expand=True)
    
    # Create a mock tool for testing
    class MockTool:
        def __init__(self):
            self.relationships = []
            self.classes = []
            self.rel_type_var = tk.StringVar(value="association")
            self.relationship_mode = False
            
        def update_relationships(self):
            for rel in self.relationships:
                rel.update_position()
                
        def update_status(self, message):
            print(f"📊 Status: {message}")
            
        def add_class_at_position(self, x, y):
            class_box = ClassBox(canvas, x, y, f"RightClickClass{len(self.classes) + 1}", self)
            class_box.attributes = ["newAttr"]
            class_box.methods = ["newMethod"]
            
            # Recreate visual with content
            class_box.canvas.delete(class_box.rect)
            class_box.canvas.delete(class_box.name_text)
            class_box.canvas.delete(class_box.sep_line)
            class_box.create_visual()
            
            # Auto-select
            for cls in self.classes:
                cls.deselect()
            class_box.select()
            
            self.classes.append(class_box)
            self.update_status(f"Created new class: {class_box.name}")
    
    tool = MockTool()
    
    # Create test classes
    print("📦 Creating test classes...")
    class1 = ClassBox(canvas, 200, 150, "Class1", tool)
    class2 = ClassBox(canvas, 500, 150, "Class2", tool)
    
    for cls in [class1, class2]:
        cls.attributes = ["attr1"]
        cls.methods = ["method1"]
        cls.canvas.delete(cls.rect)
        cls.canvas.delete(cls.name_text)
        cls.canvas.delete(cls.sep_line)
        cls.create_visual()
        tool.classes.append(cls)
    
    # Create test relationship
    print("🔗 Creating test relationship...")
    rel1 = Relationship(canvas, class1, class2, "inheritance", tool)
    tool.relationships.append(rel1)
    
    print("✅ Test setup complete!")
    print("📋 Test Instructions:")
    print("   • Click on the relationship line - it should turn red (be selectable)")
    print("   • Click on a class - relationship should deselect, class should select")
    print("   • Right-click on empty canvas - should create new class")
    print("   • Right-click on existing class - should NOT create new class")
    print("   • Close window when done testing")
    
    # Add test labels
    canvas.create_text(400, 50, text="Line Selection & Right-Click Test", font=("Arial", 16, "bold"))
    canvas.create_text(400, 70, text="Click line to select • Right-click empty space to create class", font=("Arial", 12))
    canvas.create_text(400, 550, text="Line should be selectable now!", font=("Arial", 10, "bold"))
    
    # Bind canvas events for testing
    def canvas_click(event):
        # Check if we clicked on a class
        clicked_class = None
        for class_box in tool.classes:
            if (class_box.x <= event.x <= class_box.x + class_box.width and
                class_box.y <= event.y <= class_box.y + class_box.height):
                clicked_class = class_box
                break
        
        # Check if we clicked on a relationship line
        clicked_relationship = None
        canvas_item = canvas.find_closest(event.x, event.y)[0]
        for rel in tool.relationships:
            if canvas_item == rel.line or canvas_item == rel.arrow:
                clicked_relationship = rel
                break
        
        # Only deselect if we didn't click on a relationship
        if not clicked_relationship:
            # Deselect all classes
            for class_box in tool.classes:
                class_box.deselect()
            
            # Deselect all relationships
            for rel in tool.relationships:
                rel.deselect()
            
            # Select the clicked class if any
            if clicked_class:
                clicked_class.select()
                tool.update_status(f"Selected class: {clicked_class.name}")
            else:
                tool.update_status("Clicked empty canvas")
    
    def canvas_right_click(event):
        if not tool.relationship_mode:
            # Check if we right-clicked on a class first
            clicked_class = None
            for class_box in tool.classes:
                if (class_box.x <= event.x <= class_box.x + class_box.width and
                    class_box.y <= event.y <= class_box.y + class_box.height):
                    clicked_class = class_box
                    break
            
            # Only create new class if we didn't right-click on an existing one
            if not clicked_class:
                tool.add_class_at_position(event.x, event.y)
            else:
                tool.update_status(f"Right-clicked on existing class: {clicked_class.name}")
    
    canvas.bind("<Button-1>", canvas_click)
    canvas.bind("<Button-3>", canvas_right_click)
    
    root.mainloop()

if __name__ == "__main__":
    test_line_selection_and_right_click()