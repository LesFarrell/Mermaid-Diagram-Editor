#!/usr/bin/env python3
"""
Test script for enhanced Mermaid UML features
"""

import tkinter as tk
from mermaid_diagram_tool import ClassBox, Relationship, MermaidDiagramTool

def test_enhanced_features():
    print("🧪 Testing Enhanced Mermaid UML Features")
    print("=" * 50)
    
    # Create test window
    root = tk.Tk()
    root.title("Enhanced Features Test")
    root.geometry("1200x800")
    
    canvas = tk.Canvas(root, bg="white", width=1200, height=700)
    canvas.pack(fill=tk.BOTH, expand=True)
    
    # Create mock tool
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
    
    print("📦 Creating enhanced classes...")
    
    # Create interface class
    interface_class = ClassBox(canvas, 100, 100, "Drawable", tool)
    interface_class.stereotype = "interface"
    interface_class.annotations = ["FunctionalInterface"]
    interface_class.attributes = []
    interface_class.methods = ["+draw(): void", "+getArea(): double"]
    interface_class.notes = ["All shapes must implement this interface"]
    
    # Create abstract class
    abstract_class = ClassBox(canvas, 400, 100, "Shape", tool)
    abstract_class.stereotype = "abstract"
    abstract_class.annotations = ["Entity"]
    abstract_class.attributes = ["-color: String", "#id: int"]
    abstract_class.methods = ["+getColor(): String", "*calculateArea(): double"]
    abstract_class.notes = ["Base class for all geometric shapes"]
    
    # Create concrete class
    concrete_class = ClassBox(canvas, 700, 100, "Circle", tool)
    concrete_class.attributes = ["-radius: double", "+center: Point"]
    concrete_class.methods = ["+Circle(radius: double)", "+calculateArea(): double", "+draw(): void"]
    concrete_class.notes = ["Represents a circular shape"]
    
    # Create utility class
    utility_class = ClassBox(canvas, 400, 400, "MathUtils", tool)
    utility_class.stereotype = "utility"
    utility_class.annotations = ["Utility", "StaticOnly"]
    utility_class.attributes = ["+PI: double", "+E: double"]
    utility_class.methods = ["+sqrt(x: double): double", "+pow(base: double, exp: double): double"]
    
    # Recreate visuals for all classes
    for cls in [interface_class, abstract_class, concrete_class, utility_class]:
        cls.canvas.delete(cls.rect)
        cls.canvas.delete(cls.name_text)
        cls.canvas.delete(cls.sep_line)
        cls.create_visual()
        tool.classes.append(cls)
    
    print("🔗 Creating enhanced relationships...")
    
    # Realization relationship (Circle implements Drawable)
    rel1 = Relationship(canvas, concrete_class, interface_class, "realization", tool)
    rel1.label = "implements"
    
    # Inheritance relationship (Circle extends Shape)
    rel2 = Relationship(canvas, concrete_class, abstract_class, "inheritance", tool)
    
    # Dependency relationship (Circle uses MathUtils)
    rel3 = Relationship(canvas, concrete_class, utility_class, "dependency", tool)
    rel3.label = "uses"
    
    # Composition relationship (with multiplicities)
    rel4 = Relationship(canvas, abstract_class, interface_class, "composition", tool)
    rel4.from_multiplicity = "1"
    rel4.to_multiplicity = "0..*"
    rel4.label = "contains"
    
    tool.relationships.extend([rel1, rel2, rel3, rel4])
    
    print("✅ Enhanced features test setup complete!")
    print("📋 Features demonstrated:")
    print("   • Stereotypes: <<interface>>, <<abstract>>, <<utility>>")
    print("   • Annotations: @FunctionalInterface, @Entity, @Utility, @StaticOnly")
    print("   • Visibility modifiers: +public, -private, #protected")
    print("   • Method parameters and return types")
    print("   • Class notes (orange text at bottom)")
    print("   • Enhanced relationships: realization (dashed), dependency (dashed)")
    print("   • Relationship labels and multiplicities")
    print("   • Different class colors based on type")
    print("   • Abstract methods in italics")
    
    # Add instruction labels
    canvas.create_text(600, 50, text="Enhanced Mermaid UML Features Demo", 
                      font=("Arial", 16, "bold"))
    canvas.create_text(600, 650, text="Interface (green) • Abstract (yellow) • Concrete (blue) • Utility (blue)", 
                      font=("Arial", 10))
    canvas.create_text(600, 670, text="Double-click classes to edit • Click relationships to select", 
                      font=("Arial", 10))
    
    print("\n🎯 Try these interactions:")
    print("   • Double-click any class to see the enhanced edit dialog")
    print("   • Click relationships to see selection and labels")
    print("   • Notice different visual styles for different class types")
    print("   • Close window when done testing")
    
    root.mainloop()

if __name__ == "__main__":
    test_enhanced_features()