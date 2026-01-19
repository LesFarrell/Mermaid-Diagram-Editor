#!/usr/bin/env python3
"""
Test script to verify:
1. Lines are drawn behind classes (not on top)
2. No duplicate classes when moving
3. All class elements move together properly
"""

import tkinter as tk
from mermaid_diagram_tool import ClassBox, Relationship, MermaidDiagramTool

def test_layering():
    print("🧪 Testing Layering and Movement")
    print("=" * 40)
    
    root = tk.Tk()
    root.title("Layering Fix Test")
    root.geometry("900x700")
    
    canvas = tk.Canvas(root, bg="white", width=900, height=700)
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
    
    print("📦 Creating overlapping classes to test layering...")
    
    # Create classes that will overlap with relationships
    class1 = ClassBox(canvas, 200, 200, "ClassA", tool)
    class1.attributes = ["+id: int", "+name: String"]
    class1.methods = ["+getId(): int", "+setName(name: String)"]
    
    class2 = ClassBox(canvas, 500, 200, "ClassB", tool)
    class2.attributes = ["+value: double"]
    class2.methods = ["+getValue(): double"]
    
    class3 = ClassBox(canvas, 350, 400, "ClassC", tool)
    class3.attributes = ["+data: Object"]
    
    # Create all visuals
    classes = [class1, class2, class3]
    for cls in classes:
        cls.create_visual()
        tool.classes.append(cls)
    
    print("🔗 Creating relationships that will pass through/near classes...")
    
    # Create relationships
    rel1 = Relationship(canvas, class1, class2, "inheritance", tool)
    rel2 = Relationship(canvas, class1, class3, "composition", tool)
    rel3 = Relationship(canvas, class2, class3, "association", tool)
    
    tool.relationships.extend([rel1, rel2, rel3])
    
    print("✅ Test setup complete!")
    print(f"   Created {len(classes)} classes")
    print(f"   Created {len(tool.relationships)} relationships")
    
    # Add instructions
    instructions = [
        "Layering and Movement Test",
        "",
        "What to verify:",
        "1. Lines should be BEHIND classes (not on top)",
        "2. Drag classes around - no duplicates should appear",
        "3. All class elements (text, borders) move together",
        "4. Arrow heads should still be visible",
        "5. No 'ghost' classes left behind when moving",
        "",
        "Try dragging ClassA over the line between ClassB and ClassC",
        "The line should disappear behind ClassA (not show through)",
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
    print("   ✓ Lines behind classes (not visible on top)")
    print("   ✓ No duplicate classes when dragging")
    print("   ✓ All elements move together")
    print("   ✓ Arrow heads still visible")
    print("   ✓ No ghost classes left behind")
    print("   ✓ Drag ClassA over other lines to verify layering")
    
    root.mainloop()

if __name__ == "__main__":
    test_layering()
