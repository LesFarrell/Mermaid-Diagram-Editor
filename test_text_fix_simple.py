#!/usr/bin/env python3
"""
Simple test to verify text positioning fix
"""

import tkinter as tk
from mermaid_diagram_tool import ClassBox

def test_text_fix():
    print("🧪 Testing Text Positioning Fix")
    print("=" * 40)
    
    root = tk.Tk()
    root.title("Text Fix Test")
    root.geometry("800x600")
    
    canvas = tk.Canvas(root, bg="white", width=800, height=600)
    canvas.pack(fill=tk.BOTH, expand=True)
    
    # Create class with problematic long text
    test_class = ClassBox(canvas, 100, 100, "VeryLongClassNameThatUsedToOverflow", None)
    test_class.attributes = [
        "+veryLongAttributeNameThatShouldWrapProperly: VeryLongTypeName",
        "+anotherLongAttribute: String",
        "+shortAttr: int"
    ]
    test_class.methods = [
        "+veryLongMethodNameWithManyParameters(param1: Type1, param2: Type2): ReturnType",
        "+shortMethod(): void"
    ]
    test_class.stereotype = "VeryLongStereotypeName"
    test_class.annotations = ["VeryLongAnnotationName"]
    test_class.notes = ["This is a very long note that should wrap properly within the class boundaries without overflowing"]
    
    # Create the visual
    test_class.create_visual()
    
    print("✅ Test class created")
    print(f"   Class width: {test_class.width}px")
    print(f"   Class height: {test_class.height}px")
    
    # Add instructions
    canvas.create_text(400, 50, text="Text Positioning Fix Test", font=("Arial", 16, "bold"))
    canvas.create_text(400, 550, text="Text should stay within class boundaries", font=("Arial", 12))
    canvas.create_text(400, 570, text="Drag the class to test movement", font=("Arial", 10))
    
    print("\n📋 Check that:")
    print("   • All text stays within the blue class box")
    print("   • Long text wraps to multiple lines")
    print("   • Class auto-resizes to fit content")
    print("   • Drag the class - all text should move together")
    
    root.mainloop()

if __name__ == "__main__":
    test_text_fix()