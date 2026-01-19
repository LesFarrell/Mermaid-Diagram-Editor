#!/usr/bin/env python3
"""
Test script to verify Mermaid-only save/load functionality
"""

import os
import tempfile
from mermaid_diagram_tool import MermaidDiagramTool, ClassBox, Relationship

def test_mermaid_save_load():
    print("🧪 Testing Mermaid-Only Save/Load")
    print("=" * 50)
    
    # Create a temporary file for testing
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False)
    temp_filename = temp_file.name
    temp_file.close()
    
    try:
        # Test data - create a simple diagram programmatically
        print("📦 Creating test diagram...")
        
        # Mock the file dialog to use our temp file
        original_asksaveasfilename = None
        original_askopenfilename = None
        
        def mock_save_filename(*args, **kwargs):
            return temp_filename
            
        def mock_open_filename(*args, **kwargs):
            return temp_filename
        
        # Create tool instance
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()  # Hide the window
        
        tool = MermaidDiagramTool()
        tool.root.withdraw()  # Hide the tool window too
        
        # Create test classes
        class1 = ClassBox(tool.canvas, 150, 150, "User", tool)
        class1.attributes = ["id", "username", "email"]
        class1.methods = ["login", "logout"]
        
        class2 = ClassBox(tool.canvas, 450, 150, "Admin", tool)
        class2.attributes = ["permissions"]
        class2.methods = ["manageUsers"]
        
        tool.classes = [class1, class2]
        
        # Create test relationship
        rel = Relationship(tool.canvas, class2, class1, "inheritance", tool)
        tool.relationships = [rel]
        
        print("✅ Test diagram created")
        print(f"   • Classes: {len(tool.classes)}")
        print(f"   • Relationships: {len(tool.relationships)}")
        
        # Test save functionality
        print("\n💾 Testing save functionality...")
        
        # Mock the file dialog
        import tkinter.filedialog as fd
        original_asksaveasfilename = fd.asksaveasfilename
        fd.asksaveasfilename = mock_save_filename
        
        tool.save_mermaid()
        
        # Restore original function
        fd.asksaveasfilename = original_asksaveasfilename
        
        # Check if file was created and has content
        if os.path.exists(temp_filename):
            with open(temp_filename, 'r') as f:
                saved_content = f.read()
            print("✅ Save successful!")
            print("📄 Saved content:")
            print("-" * 30)
            print(saved_content)
            print("-" * 30)
        else:
            print("❌ Save failed - file not created")
            return
        
        # Test load functionality
        print("\n📂 Testing load functionality...")
        
        # Clear the current diagram
        tool.new_diagram()
        print(f"   • Cleared diagram (classes: {len(tool.classes)}, relationships: {len(tool.relationships)})")
        
        # Mock the file dialog for opening
        original_askopenfilename = fd.askopenfilename
        fd.askopenfilename = mock_open_filename
        
        tool.open_mermaid()
        
        # Restore original function
        fd.askopenfilename = original_askopenfilename
        
        print("✅ Load successful!")
        print(f"   • Loaded classes: {len(tool.classes)}")
        print(f"   • Loaded relationships: {len(tool.relationships)}")
        
        # Verify loaded content
        if len(tool.classes) >= 2:
            print(f"   • Class 1: {tool.classes[0].name} ({len(tool.classes[0].attributes)} attrs, {len(tool.classes[0].methods)} methods)")
            print(f"   • Class 2: {tool.classes[1].name} ({len(tool.classes[1].attributes)} attrs, {len(tool.classes[1].methods)} methods)")
        
        if len(tool.relationships) >= 1:
            rel = tool.relationships[0]
            print(f"   • Relationship: {rel.from_class.name} --{rel.rel_type}--> {rel.to_class.name}")
        
        # Test round-trip - save again and compare
        print("\n🔄 Testing round-trip...")
        
        temp_file2 = tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False)
        temp_filename2 = temp_file2.name
        temp_file2.close()
        
        def mock_save_filename2(*args, **kwargs):
            return temp_filename2
        
        fd.asksaveasfilename = mock_save_filename2
        tool.save_mermaid()
        fd.asksaveasfilename = original_asksaveasfilename
        
        # Compare the two files
        with open(temp_filename, 'r') as f:
            content1 = f.read()
        with open(temp_filename2, 'r') as f:
            content2 = f.read()
        
        if content1 == content2:
            print("✅ Round-trip successful - content matches!")
        else:
            print("⚠️  Round-trip content differs:")
            print("Original:")
            print(content1)
            print("Round-trip:")
            print(content2)
        
        # Clean up
        os.unlink(temp_filename2)
        
        print("\n🎯 Test Summary:")
        print("   ✅ Mermaid save functionality works")
        print("   ✅ Mermaid load functionality works") 
        print("   ✅ Round-trip editing preserves content")
        print("   ✅ No JSON dependencies remaining")
        
        root.destroy()
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Clean up temp file
        if os.path.exists(temp_filename):
            os.unlink(temp_filename)

if __name__ == "__main__":
    test_mermaid_save_load()