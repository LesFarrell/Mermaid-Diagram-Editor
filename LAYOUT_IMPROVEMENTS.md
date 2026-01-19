# Layout Improvements - Mermaid-Style Display

## New Features

### 1. Curved Lines (Bezier Curves)
- All relationship lines now use smooth bezier curves instead of straight lines
- Creates a more professional, Mermaid-like appearance
- Curves are calculated based on line length for optimal visual appeal

### 2. Hierarchical Auto-Layout
- New "Auto Layout" button in the toolbar (green button)
- Automatically arranges classes based on their relationships:
  - **Parent classes** (inheritance targets) appear at the top
  - **Child classes** appear below their parents
  - **Composition/Realization** relationships also influence hierarchy
  - **Unrelated classes** are grouped at the bottom

### 3. Collision Avoidance
- Automatic gap enforcement between classes (minimum 30px)
- Iterative overlap resolution algorithm
- Ensures no classes overlap after layout

### 4. Smart Spacing
- Horizontal gap: 80px between classes in the same level
- Vertical gap: 100px between hierarchy levels
- Classes are centered within each level
- Spacing adapts to actual class dimensions

## How to Use

### Automatic Layout on Load
When you open a Mermaid file, the hierarchical layout is **automatically applied**.

### Manual Layout Adjustment
1. Click the **"Auto Layout"** button in the toolbar
2. The diagram will reorganize based on relationships
3. Status bar shows: "Layout applied: X levels, Y classes"

### Layout Algorithm
1. **Builds dependency graph** from inheritance, composition, and realization relationships
2. **Topological sort** determines hierarchy levels
3. **Positions classes** level by level from top to bottom
4. **Resolves overlaps** using iterative adjustment
5. **Updates all relationships** with curved lines

## Visual Improvements

### Before
- Straight lines between classes
- Simple grid layout
- Classes could overlap
- No hierarchy consideration

### After
- Smooth curved lines (bezier curves)
- Hierarchical tree layout
- Guaranteed spacing between classes
- Parent-child relationships clearly visible
- Mermaid-style professional appearance

## Test Files

- `test_curved_layout.md` - Simple inheritance hierarchy
- `test_layout_demo.md` - Complex multi-level hierarchy with various relationship types

## Tips

- Use inheritance (`<|--`) and composition (`*--`) to create clear hierarchies
- The layout algorithm works best with tree-like structures
- You can still manually drag classes after auto-layout
- Press "Auto Layout" again to reapply the algorithm
