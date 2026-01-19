#!/usr/bin/env python3
"""
Test script to verify arrow heads are visible above classes
"""

import tkinter as tk
from mermaid_diagram_tool import ClassBox, Relationship, MermaidDiagramTool

def test_arrow_visibility():
    print("🧪 Testing Arrow Head Visibility")
    print("=" * 40)
    
    root = tk.Tk()
    root.title("Arrow Visibility Test")
    root.geometry("1000x700")
    
    canvas = tk.Canvas(root, bg="white", width=1000, height=600)
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
    
    print("📦 Creating overlapping classes to test arrow visibility...")
    
    # Create classes positioned to test arrow visibility
    class1 = ClassBox(canvas, 100, 150, "BaseClass", tool)
    class1.attributes = ["+id: int", "+name: String"]
    class1.methods = ["+getId(): int", "+getName(): String"]
    
    class2 = ClassBox(canvas, 400, 150, "DerivedClass", tool)
    class2.attributes = ["+value: double"]
    class2.methods = ["+getValue(): double"]
    
    class3 = ClassBox(canvas, 700, 150, "Interface", tool)
    class3.stereotype = "interface"
    class3.methods = ["+process(): void"]
    
    class4 = ClassBox(canvas, 250, 350, "Component", tool)
    class4.attributes = ["+parts: List"]
    class4.methods = ["+addPart(): void"]
    
    class5 = ClassBox(canvas, 550, 350, "Utility", tool)
    class5.stereotype = "utility"
    class5.methods = ["+calculate(): double"]
    
    # Create all visuals
    classes = [class1, class2, class3, class4, class5]
    for cls in classes:
        cls.create_visual()
        tool.classes.append(cls)
    
    print("🔗 Creating relationships with different arrow types...")
    
    # Create relationships that will test arrow visibility
    rel1 = Relationship(canvas, class2, class1, "inheritance", tool)  # Triangle arrow
    rel1.label = "extends"
    
    rel2 = Relationship(canvas, class2, class3, "realization", tool)  # Dashed triangle
    rel2.label = "implements"
    
    rel3 = Relationship(canvas, class4, class1, "composition", tool)  # Filled diamond
    rel3.from_multiplicity = "1"
    rel3.to_multiplicity = "0..*"
    rel3.label = "contains"
    
    rel4 = Relationship(canvas, class4, class5, "aggregation", tool)  # Empty diamond
    rel4.label = "uses"
    
    rel5 = Relationship(canvas, class5, class1, "dependency", tool)  # Dashed arrow
    rel5.label = "depends on"
    
    rel6 = Relationship(canvas, class1, class3, "association", tool)  # Simple arrow
    rel6.label = "knows about"
    
    tool.relationships.extend([rel1, rel2, rel3, rel4, rel5, rel6])
    
    print("✅ Arrow visibility test setup complete!")
    print(f"   Created {len(classes)} classes")
    print(f"   Created {len(tool.relationships)} relationships")
    
    # Add instructions
    canvas.create_text(500, 50, text="Arrow Head Visibility Test", font=("Arial", 16, "bold"))
    canvas.create_text(500, 600, text="All arrow heads should be visible above class boxes", font=("Arial", 12))
    canvas.create_text(500, 620, text="Click relationships to select them (should turn red)", font=("Arial", 10))
    canvas.create_text(500, 640, text="Double-click relationships to change their type", font=("Arial", 10))
    
    print("\n📋 What to verify:")
    print("   • All arrow heads are clearly visible")
    print("   • Arrows appear above (not behind) class boxes")
    print("   • Different arrow types are distinguishable:")
    print("     - Inheritance: White triangle")
    print("     - Realization: White triangle (dashed line)")
    print("     - Composition: Black diamond")
    print("     - Aggregation: White diamond")
    print("     - Dependency: Open arrow (dashed line)")
    print("     - Association: Simple arrow")
    print("   • Relationship labels and multiplicities are visible")
    print("   • Selected relationships turn red (line and arrow)")
    print("   • Close window when done testing")
    
    root.mainloop()

if __name__ == "__main__":
    test_arrow_visibility()