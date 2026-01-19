#!/usr/bin/env python3
"""
Test script to verify drag handle and double-click fixes
"""

import tkinter as tk
from mermaid_diagram_tool import ClassBox, MermaidDiagramTool

def test_drag_handles():
    print("🧪 Testing Drag Handle and Double-Click Fixes")
    print("=" * 50)
    
    # Create a simple test window
    root = tk.Tk()
    root.title("Drag Handle Test")
    root.geometry("800x600")
    
    canvas = tk.Canvas(root, bg="white", width=800, height=600)
    canvas.pack(fill=tk.BOTH, expand=True)
    
    # Create a mock tool for testing
    class MockTool:
        def __init__(self):
            self.relationships = []
            
        def update_relationships(self):
            pass  # No relationships in this test
    
    tool = MockTool()
    
    # Create test class
    print("📦 Creating test class...")
    test_class = ClassBox(canvas, 200, 150, "TestClass", tool)
    test_class.attributes = ["attribute1", "attribute2"]
    test_class.methods = ["method1", "method2"]
    
    # Recreate visual with content
    test_class.canvas.delete(test_class.rect)
    test_class.canvas.delete(test_class.name_text)
    test_class.canvas.delete(test_class.sep_line)
    test_class.create_visual()
    
    # Select the class to show drag handles
    test_class.select()
    
    print("✅ Test setup complete!")
    print("📋 Test Instructions:")
    print("   • Click on the class to select it (should show red corner handles)")
    print("   • Drag the class around - handles should move with it")
    print("   • Double-click on the class to edit (should NOT create a new class)")
    print("   • Double-click on empty canvas to create new class")
    print("   • Close window when done testing")
    
    # Add test labels
    canvas.create_text(400, 50, text="Drag Handle & Double-Click Test", font=("Arial", 16, "bold"))
    canvas.create_text(400, 70, text="Select and drag the class to test handles", font=("Arial", 12))
    canvas.create_text(400, 500, text="Double-click class = edit | Double-click canvas = new class", font=("Arial", 10))
    
    root.mainloop()

if __name__ == "__main__":
    test_drag_handles()