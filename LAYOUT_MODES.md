# Layout Modes

## Overview
The Mermaid Diagram Tool now supports two layout algorithms that you can choose from:

1. **Hierarchical + Force-Directed** (Default)
2. **Dagre** (Compact)

## How to Use

### Layout Selector
In the toolbar, you'll find:
- **Layout dropdown** - Choose between "hierarchical" and "dagre"
- **Apply Layout button** - Click to apply the selected layout

### Steps
1. Select your preferred layout from the dropdown
2. Click "Apply Layout" button
3. The diagram reorganizes using the selected algorithm

## Layout Comparison

### Hierarchical + Force-Directed (Default)

**Best for:**
- Clear inheritance hierarchies
- Interactive editing and manual adjustment
- Readable, spacious diagrams
- Presentations and documentation

**Characteristics:**
- ✅ Clear parent-child relationships
- ✅ Generous spacing (60-80px horizontal, 100px vertical)
- ✅ Groups related classes together
- ✅ Force-directed refinement for optimal positioning
- ✅ Minimal line crossings
- ✅ Easy to read and understand

**Algorithm:**
1. Topological sort based on inheritance/composition
2. Arrange in hierarchical levels
3. Sort within levels by connectivity
4. Apply force-directed adjustment (5 iterations)
5. Resolve overlaps (30px minimum gap)

**Example:**
```
        Animal (top level)
       /   |   \
     Dog  Cat  Bird (second level)
    /  \
Poodle  GermanShepherd (third level)
```

**Spacing:**
- Horizontal gap: 60px
- Vertical gap: 100px
- Minimum gap: 30px

---

### Dagre (Compact)

**Best for:**
- Complex diagrams with many classes
- Minimizing screen space
- Dense relationship networks
- Quick overview of structure

**Characteristics:**
- ✅ Compact representation
- ✅ Efficient use of space
- ✅ Layered approach (like Mermaid.js)
- ✅ All relationships considered (not just hierarchical)
- ✅ Good for large diagrams
- ⚠️ Less spacing (may feel crowded)

**Algorithm:**
1. Topological sort based on ALL relationships
2. Arrange in compact layers
3. Minimal spacing between elements
4. Horizontal-only overlap resolution
5. Maintains layer structure strictly

**Example:**
```
[Controller1] [Controller2] [Controller3]
[Service1] [Service2] [Service3]
[Repository1] [Repository2]
[Database]
```

**Spacing:**
- Horizontal gap: 40px (compact)
- Vertical gap: 120px (compact)
- Minimum gap: 20px (tight)

---

## Detailed Comparison

| Feature | Hierarchical | Dagre |
|---------|-------------|-------|
| **Spacing** | Generous | Compact |
| **Readability** | Excellent | Good |
| **Space Usage** | More space | Less space |
| **Relationships** | Hierarchical only | All types |
| **Force-Directed** | Yes (5 iterations) | No |
| **Overlap Resolution** | Comprehensive | Horizontal only |
| **Best For** | Presentations | Large diagrams |
| **Line Crossings** | Minimized | Minimized |
| **Manual Editing** | Easy | Moderate |

## When to Use Each

### Use Hierarchical When:
- ✅ You have clear inheritance hierarchies
- ✅ Diagram has < 20 classes
- ✅ Readability is priority
- ✅ Creating documentation
- ✅ Presenting to stakeholders
- ✅ You'll manually adjust positions

### Use Dagre When:
- ✅ You have many classes (20+)
- ✅ Space is limited
- ✅ Complex relationship networks
- ✅ Quick overview needed
- ✅ Minimizing scrolling
- ✅ Exporting to small formats

## Examples

### Small Inheritance Tree (5 classes)
**Recommended:** Hierarchical
- Clear hierarchy
- Easy to read
- Professional appearance

### Layered Architecture (15 classes)
**Recommended:** Either works well
- Hierarchical: More readable
- Dagre: More compact

### Complex Network (30+ classes)
**Recommended:** Dagre
- Fits on screen
- Efficient space usage
- Still maintains structure

### Mixed Relationships
**Recommended:** Hierarchical
- Better handles multiple relationship types
- Force-directed optimization
- Clearer grouping

## Tips

### Switching Layouts
1. Try both layouts to see which looks better
2. Hierarchical first for initial organization
3. Switch to Dagre if too spread out
4. Can switch back and forth anytime

### After Applying Layout
- You can still manually adjust positions
- Drag classes to fine-tune
- Save positions to preserve your layout
- Reapply layout anytime to reset

### Combining with Features
- **Position Saving:** Works with both layouts
- **Zoom:** Both layouts respect zoom level
- **Auto-load:** Uses saved positions if available
- **Manual Adjustment:** Always possible after layout

## Technical Details

### Hierarchical Algorithm
```python
1. Build dependency graph (inheritance, composition, realization)
2. Topological sort → determine levels
3. Sort within levels by connectivity
4. Position classes with generous spacing
5. Apply force-directed refinement (5 iterations)
6. Resolve overlaps (30px minimum)
7. Update relationships
```

### Dagre Algorithm
```python
1. Build dependency graph (ALL relationships)
2. Topological sort → determine layers
3. Position classes with compact spacing
4. Resolve overlaps horizontally only (20px minimum)
5. Maintain strict layer structure
6. Update relationships
```

### Performance
- **Hierarchical:** Slightly slower (force-directed iterations)
- **Dagre:** Faster (simpler algorithm)
- Both handle 50+ classes efficiently

## Keyboard Shortcuts

Currently, layouts are applied via button click. Future enhancement could add:
- `Ctrl+H` - Apply Hierarchical layout
- `Ctrl+D` - Apply Dagre layout
- `Ctrl+L` - Toggle between layouts

## Future Enhancements

Potential additions:
- **Circular layout** - For peer relationships
- **Orthogonal layout** - Right-angle connections
- **Custom layout** - User-defined parameters
- **Layout presets** - Save favorite settings
- **Animated transitions** - Smooth layout changes

## Troubleshooting

### Classes Overlapping
- Try the other layout mode
- Manually adjust spacing
- Use "Apply Layout" again

### Too Spread Out
- Switch to Dagre layout
- Zoom out to see full diagram
- Manually move classes closer

### Too Compact
- Switch to Hierarchical layout
- Zoom in for better readability
- Manually spread classes apart

### Lines Crossing
- Both layouts minimize crossings
- Try the other layout
- Manually adjust problematic classes

## Conclusion

Both layouts are excellent for different scenarios:

- **Hierarchical:** Best for most use cases, especially presentations
- **Dagre:** Best for large, complex diagrams where space is limited

Try both and see which works better for your specific diagram!
