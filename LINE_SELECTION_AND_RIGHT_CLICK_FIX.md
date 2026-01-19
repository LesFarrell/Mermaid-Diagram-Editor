# Line Selection & Right-Click Creation Fix

## Issues Fixed:

### 1. ✅ Line Selection Not Working
**Problem**: Relationship lines couldn't be selected after the deselection fix
**Root Cause**: Canvas click handler was deselecting relationships before line click events could fire

**Solution**: 
- Added relationship detection in canvas click handler
- Only deselect relationships if we didn't click on one
- Added event propagation control (`return "break"`) in relationship click handler

**Before**:
```python
def canvas_click(self, event):
    # Always deselected all relationships
    for rel in self.relationships:
        rel.deselect()  # ❌ Prevented line selection
```

**After**:
```python
def canvas_click(self, event):
    # Check if we clicked on a relationship line
    clicked_relationship = None
    canvas_item = self.canvas.find_closest(event.x, event.y)[0]
    for rel in self.relationships:
        if canvas_item == rel.line or canvas_item == rel.arrow:
            clicked_relationship = rel
            break
    
    # Only deselect if we didn't click on a relationship
    if not clicked_relationship:
        for rel in self.relationships:
            rel.deselect()  # ✅ Smart deselection
```

### 2. ✅ Right-Click Class Creation
**Problem**: Double-click for class creation conflicted with class editing
**Solution**: Moved class creation to right-click mouse button

**Changes**:
- Removed `<Double-Button-1>` canvas binding
- Added `<Button-3>` (right-click) canvas binding
- Renamed `canvas_double_click` to `canvas_right_click`
- Updated documentation and user instructions

**Before**:
```python
self.canvas.bind("<Double-Button-1>", self.canvas_double_click)
```

**After**:
```python
self.canvas.bind("<Button-3>", self.canvas_right_click)  # Right-click
```

## Technical Implementation:

### Smart Relationship Detection:
```python
# Find the closest canvas item to click point
canvas_item = self.canvas.find_closest(event.x, event.y)[0]

# Check if it belongs to any relationship
for rel in self.relationships:
    if canvas_item == rel.line or canvas_item == rel.arrow:
        clicked_relationship = rel
        break
```

### Event Propagation Control:
```python
def on_click(self, event):
    # Handle relationship selection
    # ...selection logic...
    
    # Stop event propagation to prevent canvas click
    return "break"  # ✅ Prevents canvas deselection
```

### Right-Click Context:
```python
def canvas_right_click(self, event):
    # Check if right-clicking on existing class
    clicked_class = None
    for class_box in self.classes:
        if (class_box.x <= event.x <= class_box.x + class_box.width and
            class_box.y <= event.y <= class_box.y + class_box.height):
            clicked_class = class_box
            break
    
    # Only create if clicking on empty space
    if not clicked_class:
        self.add_class_at_position(event.x, event.y)
```

## User Experience:

### Interaction Model:
| Action | Result |
|--------|--------|
| Left-click relationship line | Selects relationship (red) |
| Left-click class | Selects class, deselects relationships |
| Left-click empty canvas | Deselects everything |
| Right-click empty canvas | Creates new class |
| Right-click existing class | No action (prevents accidental creation) |
| Double-click class | Opens edit dialog |

### Visual Feedback:
- ✅ Relationship lines turn red when selected
- ✅ Status bar shows relationship information
- ✅ New classes auto-select with red border
- ✅ Clear deselection behavior

## Result:
- ✅ Relationship lines are fully selectable and interactive
- ✅ Right-click provides intuitive class creation
- ✅ No conflicts between editing and creation
- ✅ Professional interaction model
- ✅ Clear visual feedback for all actions

## Testing:
- Run `python test_line_selection_fix.py` for isolated testing
- Run `python mermaid_diagram_tool.py` for full functionality
- Try clicking relationship lines - should turn red
- Try right-clicking empty canvas - should create classes
- Try right-clicking existing classes - should not create duplicates