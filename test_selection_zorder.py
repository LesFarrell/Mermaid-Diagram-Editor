#!/usr/bin/env python3
"""
Test script to verify selected class appears on top of other elements
"""

import tkinter as tk
from mermaid_diagram_tool import ClassBox, Relationship, MermaidDiagramTool

def test_selection_zorder():
    print("🧪 Testing Selection Z-Order")
    print("=" * 40)
    
    root = tk.Tk()
    root.title("Selection Z-Order Test")
    root.geometry("900x700")
    
    canvas = tk.Canvas(root, bg="white", width=900, height=700)
    canvas.pack(fill=tk.BOTH, expand=True)
    
    # Create mock tool
    class MockTool:
        def __init__(self):
            self.relationships = []
            self.classes = []
            self.zoom_level = 1.0
            
        def update_relationships(self):
            for rel in self.relationships:
                rel.update_position()
                
        def update_status(self, message):
            print(f"📊 Status: {message}")
    
    tool = MockTool()
    
    print("📦 Creating overlapping classes to test z-order...")
    
    # Create overlapping classes
    class1 = ClassBox(canvas, 200, 200, "BackClass", tool)
    class1.attributes = ["+id: int", "+name: String"]
    class1.methods = ["+getId(): int"]
    
    class2 = ClassBox(canvas, 250, 250, "MiddleClass", tool)
    class2.attributes = ["+value: double"]
    class2.methods = ["+getValue(): double"]
    
    class3 = ClassBox(canvas, 300, 300, "FrontClass", tool)
    class3.attributes = ["+data: Object"]
    class3.methods = ["+getData(): Object"]
    
    # Create all visuals
    classes = [class1, class2, class3]
    for cls in classes:
        cls.create_visual()
        tool.classes.append(cls)
    
    print("🔗 Creating relationships...")
    
    # Create relationships
    rel1 = Relationship(canvas, class1, class2, "inheritance", tool)
    rel2 = Relationship(canvas, class2, class3, "composition", tool)
    
    tool.relationships.extend([rel1, rel2])
    
    print("✅ Test setup complete!")
    print(f"   Created {len(classes)} overlapping classes")
    print(f"   Created {len(tool.relationships)} relationships")
    
    # Add instructions
    instructions = [
        "Selection Z-Order Test",
        "",
        "Classes are intentionally overlapping",
        "",
        "What to verify:",
        "1. Click on BackClass - it should appear on top",
        "2. Click on MiddleClass - it should appear on top",
        "3. Click on FrontClass - it should appear on top",
        "4. Drag a class - it stays on top while dragging",
        "5. Selected class is always fully visible",
        "6. Red selection border is visible on top",
        "7. Corner indicators are visible on top",
        "",
        "Try clicking different classes and dragging them",
        "The selected class should always be fully visible",
        "",
        "Close window when done testing"
    ]
    
    y_pos = 30
    for line in instructions:
        if line == "":
            y_pos += 10
        elif line == instructions[0]:
            canvas.create_text(450, y_pos, text=line, font=("Arial", 16, "bold"))
            y_pos += 30
        else:
            canvas.create_text(450, y_pos, text=line, font=("Arial", 10))
            y_pos += 20
    
    print("\n📋 Testing checklist:")
    print("   ✓ Selected class appears on top of others")
    print("   ✓ Selection border visible on top")
    print("   ✓ Corner indicators visible on top")
    print("   ✓ Dragged class stays on top")
    print("   ✓ Can select any overlapping class")
    print("   ✓ Previously selected class goes back to normal layer")
    
    root.mainloop()

if __name__ == "__main__":
    test_selection_zorder()
