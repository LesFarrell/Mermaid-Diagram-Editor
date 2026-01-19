#!/usr/bin/env python3
"""
Test script to verify text positioning and movement fixes
"""

import tkinter as tk
from mermaid_diagram_tool import ClassBox, Relationship, MermaidDiagramTool

def test_text_positioning():
    print("🧪 Testing Text Positioning and Movement Fixes")
    print("=" * 50)
    
    # Create test window
    root = tk.Tk()
    root.title("Text Positioning Fix Test")
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
    
    print("📦 Creating classes with long text content...")
    
    # Create class with very long content to test text wrapping
    long_class = ClassBox(canvas, 100, 100, "VeryLongClassNameThatShouldFitProperly", tool)
    long_class.stereotype = "VeryLongStereotypeName"
    long_class.annotations = ["VeryLongAnnotationName", "AnotherLongAnnotation"]
    long_class.attributes = [
        "+veryLongAttributeNameWithType: VeryLongTypeName",
        "-anotherVeryLongPrivateAttribute: AnotherLongType",
        "#protectedAttributeWithVeryLongName: String"
    ]
    long_class.methods = [
        "+veryLongMethodNameWithParameters(param1: VeryLongType, param2: AnotherType): ReturnType",
        "-privateLongMethodName(complexParam: ComplexType): ComplexReturnType",
        "*abstractMethodWithVeryLongName(): AbstractReturnType"
    ]
    long_class.notes = [
        "This is a very long note that should wrap properly within the class boundaries",
        "Another long note to test text positioning and wrapping behavior"
    ]
    
    # Create normal class for comparison
    normal_class = ClassBox(canvas, 500, 100, "NormalClass", tool)
    normal_class.stereotype = "interface"
    normal_class.attributes = ["+id: int", "+name: String"]
    normal_class.methods = ["+getId(): int", "+getName(): String"]
    normal_class.notes = ["Normal note"]
    
    # Create small class to test minimum sizing
    small_class = ClassBox(canvas, 100, 400, "Small", tool)
    small_class.attributes = ["+x: int"]
    small_class.methods = ["+get(): int"]
    
    # Recreate visuals for all classes
    for cls in [long_class, normal_class, small_class]:
        cls.canvas.delete(cls.rect) if hasattr(cls, 'rect') else None
        cls.canvas.delete(cls.name_text) if hasattr(cls, 'name_text') else None
        cls.canvas.delete(cls.sep_line) if hasattr(cls, 'sep_line') else None
        cls.create_visual()
        tool.classes.append(cls)
    
    print("🔗 Creating relationships with labels...")
    
    # Create relationship with labels
    rel1 = Relationship(canvas, normal_class, long_class, "association", tool)
    rel1.label = "uses with long label"
    rel1.from_multiplicity = "1..*"
    rel1.to_multiplicity = "0..1"
    
    rel2 = Relationship(canvas, small_class, normal_class, "inheritance", tool)
    rel2.label = "extends"
    
    tool.relationships.extend([rel1, rel2])
    
    print("✅ Text positioning test setup complete!")
    print("📋 Test Instructions:")
    print("   • Check that all text stays within class boundaries")
    print("   • Drag classes around - all text should move together")
    print("   • Long text should be truncated with '...' if needed")
    print("   • Class boxes should auto-resize to fit content")
    print("   • Relationship labels should move with the lines")
    print("   • No text should be left behind when moving")
    
    # Add instruction labels
    canvas.create_text(500, 50, text="Text Positioning and Movement Test", 
                      font=("Arial", 16, "bold"))
    canvas.create_text(500, 650, text="Drag classes to test text movement • Check text stays within boundaries", 
                      font=("Arial", 10))
    
    print("\n🎯 What to verify:")
    print("   • Text doesn't overflow class boundaries")
    print("   • All text elements move together when dragging")
    print("   • Long text is properly truncated")
    print("   • Class width adjusts to content")
    print("   • Relationship labels move with lines")
    print("   • Close window when done testing")
    
    root.mainloop()

if __name__ == "__main__":
    test_text_positioning()