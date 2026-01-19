#!/usr/bin/env python3
"""
Test script to demonstrate Mermaid import functionality
"""

import re

def extract_mermaid_code(content):
    """Extract Mermaid code from markdown code blocks or plain text"""
    # Try to find mermaid code block first
    mermaid_block_pattern = r'```mermaid\s*\n(.*?)\n```'
    match = re.search(mermaid_block_pattern, content, re.DOTALL | re.IGNORECASE)
    
    if match:
        return match.group(1).strip()
    
    # If no code block, check if the entire content is mermaid
    if 'classDiagram' in content:
        return content.strip()
    
    return None

def parse_mermaid_demo(mermaid_code):
    """Parse Mermaid class diagram code and show what would be created"""
    lines = [line.strip() for line in mermaid_code.split('\n') if line.strip()]
    
    # Find classDiagram declaration
    if not any('classDiagram' in line for line in lines):
        raise ValueError("Not a valid Mermaid class diagram")
    
    classes_data = {}
    relationships = []
    current_class = None
    
    print("🔍 Parsing Mermaid diagram...")
    print("=" * 50)
    
    for line in lines:
        if 'classDiagram' in line:
            print("📋 Found class diagram declaration")
            continue
            
        # Parse class definition start
        class_match = re.match(r'\s*class\s+(\w+)\s*\{', line)
        if class_match:
            current_class = class_match.group(1)
            classes_data[current_class] = {'attributes': [], 'methods': []}
            print(f"📦 Found class: {current_class}")
            continue
        
        # Parse class definition end
        if line.strip() == '}':
            if current_class:
                attrs = classes_data[current_class]['attributes']
                methods = classes_data[current_class]['methods']
                print(f"   └─ Attributes: {attrs}")
                print(f"   └─ Methods: {methods}")
            current_class = None
            continue
        
        # Parse class members (attributes and methods)
        if current_class:
            member_match = re.match(r'\s*[+\-#~]?\s*(.+)', line)
            if member_match:
                member = member_match.group(1).strip()
                if member.endswith('()'):
                    # It's a method
                    method_name = member[:-2]
                    classes_data[current_class]['methods'].append(method_name)
                else:
                    # It's an attribute
                    classes_data[current_class]['attributes'].append(member)
            continue
        
        # Parse relationships
        rel_patterns = [
            (r'(\w+)\s*<\|\-\-\s*(\w+)', 'inheritance', True),  # inheritance (reversed)
            (r'(\w+)\s*\*\-\-\s*(\w+)', 'composition', False),  # composition
            (r'(\w+)\s*o\-\-\s*(\w+)', 'aggregation', False),   # aggregation
            (r'(\w+)\s*\-\->\s*(\w+)', 'association', False),   # association
            (r'(\w+)\s*\-\-\s*(\w+)', 'association', False),    # simple association
        ]
        
        for pattern, rel_type, reversed_rel in rel_patterns:
            match = re.match(pattern, line)
            if match:
                if reversed_rel:
                    # For inheritance, the arrow points from child to parent
                    from_class, to_class = match.group(2), match.group(1)
                else:
                    from_class, to_class = match.group(1), match.group(2)
                
                relationships.append({
                    'from': from_class,
                    'to': to_class,
                    'type': rel_type
                })
                print(f"🔗 Found {rel_type}: {from_class} → {to_class}")
                break
    
    print("\n📊 Summary:")
    print(f"   Classes found: {len(classes_data)}")
    print(f"   Relationships found: {len(relationships)}")
    
    return classes_data, relationships

def main():
    print("🎨 Mermaid Import Demo")
    print("=" * 50)
    
    # Read the sample diagram
    try:
        with open('sample_diagram.md', 'r') as f:
            content = f.read()
        
        print("📖 Reading sample_diagram.md...")
        
        # Extract mermaid code
        mermaid_code = extract_mermaid_code(content)
        if mermaid_code:
            print("✅ Mermaid code extracted successfully!")
            print("\n📝 Extracted code:")
            print("-" * 30)
            print(mermaid_code[:200] + "..." if len(mermaid_code) > 200 else mermaid_code)
            print("-" * 30)
            
            # Parse the code
            classes_data, relationships = parse_mermaid_demo(mermaid_code)
            
            print(f"\n🎯 Would create {len(classes_data)} visual class boxes:")
            for class_name, data in classes_data.items():
                print(f"   • {class_name} ({len(data['attributes'])} attrs, {len(data['methods'])} methods)")
            
            print(f"\n🔗 Would create {len(relationships)} relationship lines:")
            for rel in relationships:
                print(f"   • {rel['from']} --{rel['type']}--> {rel['to']}")
                
        else:
            print("❌ No valid Mermaid code found")
            
    except FileNotFoundError:
        print("❌ sample_diagram.md not found")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()