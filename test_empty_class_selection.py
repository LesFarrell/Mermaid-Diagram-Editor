#!/usr/bin/env python3
"""
Test script to verify empty class selection works properly
"""

import tkinter as tk
from mermaid_diagram_tool import ClassBox, MermaidDiagramTool

def test_empty_class_selection():
    print("🧪 Testing Empty Class Selection")
    print("=" * 40)
    
    root = tk.Tk()
    root.title("Empty Class Selection Test")
    root.geometry("800x600")
    
    canvas = tk.Canvas(root, bg="white", width=800, height=600)
    canvas.pack(fill=tk.BOTH, expand=True)
    
    # Create mock tool
    class MockTool:
        def __init__(self):
            self.relationships = []
            self.classes = []
            
        def update_relationships(self):
            pass
                
        def update_status(self, message):
            print(f"📊 Status: {message}")
    
    tool = MockTool()
    
    print("📦 Creating different types of classes...")
    
    # Create completely empty class
    empty_class = ClassBox(canvas, 100, 100, "EmptyClass", tool)
    # No attributes, methods, notes, etc.
    
    # Create class with only name
    name_only_class = ClassBox(canvas, 300, 100, "NameOnly", tool)
    
    # Create class with stereotype but no content
    stereotype_class = ClassBox(canvas, 500, 100, "StereotypeOnly", tool)
    stereotype_class.stereotype = "interface"
    
    # Create class with annotation but no content
    annotation_class = ClassBox(canvas, 100, 300, "AnnotationOnly", tool)
    annotation_class.annotations = ["Override"]
    
    # Create normal class for comparison
    normal_class = ClassBox(canvas, 300, 300, "NormalClass", tool)
    normal_class.attributes = ["+id: int"]
    normal_class.methods = ["+getId(): int"]
    
    # Create all visuals
    classes = [empty_class, name_only_class, stereotype_class, annotation_class, normal_class]
    for cls in classes:
        cls.create_visual()
        tool.classes.append(cls)
    
    print("✅ Test classes created")
    print(f"   Empty class size: {empty_class.width}x{empty_class.height}")
    print(f"   Name-only class size: {name_only_class.width}x{name_only_class.height}")
    print(f"   Stereotype class size: {stereotype_class.width}x{stereotype_class.height}")
    print(f"   Normal class size: {normal_class.width}x{normal_class.height}")
    
    # Add click handler for testing
    def test_click(event):
        print(f"\n🖱️  Click at ({event.x}, {event.y})")
        
        # Check which class was clicked
        clicked_class = None
        for class_box in tool.classes:
            hit_margin = 2
            if (class_box.x - hit_margin <= event.x <= class_box.x + class_box.width + hit_margin and
                class_box.y - hit_margin <= event.y <= class_box.y + class_box.height + hit_margin):
                clicked_class = class_box
                break
        
        # Deselect all first
        for cls in tool.classes:
            cls.deselect()
        
        if clicked_class:
            clicked_class.select()
            print(f"   ✅ Selected: {clicked_class.name}")
        else:
            print("   ❌ No class selected")
    
    canvas.bind("<Button-1>", test_click)
    
    # Add instructions
    canvas.create_text(400, 50, text="Empty Class Selection Test", font=("Arial", 16, "bold"))
    canvas.create_text(400, 520, text="Click on each class to test selection", font=("Arial", 12))
    canvas.create_text(400, 540, text="Empty classes should be selectable and show '(empty)' text", font=("Arial", 10))
    canvas.create_text(400, 560, text="All classes should have minimum 80px height for good clickability", font=("Arial", 10))
    
    print("\n📋 Test Instructions:")
    print("   • Try clicking on each class, especially the empty ones")
    print("   • Empty classes should show '(empty)' text in gray")
    print("   • All classes should be easily selectable")
    print("   • Selected classes should show red border with corner indicators")
    print("   • Check console output for click detection results")
    print("   • Close window when done testing")
    
    root.mainloop()

if __name__ == "__main__":
    test_empty_class_selection()