# Canvas Panning Feature

## Overview
Pan the entire diagram by clicking and dragging on empty canvas space, making it easy to navigate large diagrams and reposition all elements together.

## How to Use

### Panning the Diagram
1. **Click on empty space** (not on a class or relationship)
2. **Hold and drag** the mouse to move the entire diagram
3. **Release** to stop panning

### Visual Feedback
- **Cursor changes to four-way arrow** (⊕) when panning
- **Status bar shows "Pan mode"** while dragging
- **Hand cursor** (👆) appears when hovering over classes
- **Default cursor** appears over empty space

## Behavior

### What Gets Moved
When panning, ALL elements move together:
- ✅ All classes
- ✅ All relationships (lines and arrows)
- ✅ All labels and multiplicities
- ✅ Selection indicators (if any class is selected)

### What Doesn't Trigger Panning
- ❌ Clicking on a class (selects/drags that class only)
- ❌ Clicking on a relationship line (selects that relationship)
- ❌ Dragging a selected class (moves only that class)
- ❌ Right-clicking (creates new class)

### Smart Detection
The tool automatically detects whether you clicked on:
1. **A class**: Selects and allows dragging that class individually
2. **A relationship**: Selects that relationship
3. **Empty space**: Starts panning mode

## Use Cases

### Large Diagrams
- Navigate diagrams with many classes
- Move entire diagram to center it on screen
- Reposition all elements together
- Explore different sections

### Layout Adjustment
- Move entire diagram after importing
- Center diagram in viewport
- Adjust position after zooming
- Organize workspace

### Presentation
- Pan to focus on specific areas
- Move diagram for better visibility
- Navigate during demonstrations
- Explore architecture dynamically

## Technical Details

### Coordinate System
- Uses canvas coordinates (not screen coordinates)
- Accounts for scroll position
- Works correctly at any zoom level
- Smooth movement tracking

### Panning Detection
```python
# Check if click is on empty space
canvas_x = self.canvas.canvasx(event.x)
canvas_y = self.canvas.canvasy(event.y)

# Verify no class at this position
really_empty = True
for class_box in self.classes:
    if (class_box.x <= canvas_x <= class_box.x + class_box.width and
        class_box.y <= canvas_y <= class_box.y + class_box.height):
        really_empty = False
        break

if really_empty:
    # Start panning
    self.is_panning = True
```

### Movement Calculation
```python
# Calculate drag distance
dx = canvas_x - self.pan_start_x
dy = canvas_y - self.pan_start_y

# Move all classes
for class_box in self.classes:
    class_box.x += dx
    class_box.y += dy
    # Move visual elements...

# Update relationships
self.update_relationships()
```

### Cursor Management
- **Default cursor**: Over empty space (ready to pan)
- **Hand cursor** (`hand2`): Over classes (ready to drag)
- **Four-way arrow** (`fleur`): While panning
- **Automatic reset**: Cursor returns to default after panning

## Integration with Other Features

### Works With Zoom
- Pan at any zoom level
- Zoom center point independent of pan
- Smooth interaction between pan and zoom
- Can pan, zoom, then pan again

### Works With Scrolling
- Scroll region updates after panning
- Can pan beyond current viewport
- Scrollbars adjust automatically
- No conflicts with scroll behavior

### Works With Selection
- Can pan while a class is selected
- Selection indicators move with panning
- Deselects all when starting pan
- Can select after panning

### Works With Relationships
- Relationships update during pan
- Lines stay connected to classes
- Arrows move with endpoints
- Labels and multiplicities move together

## Keyboard Shortcuts (Future Enhancement)
- `Space + Drag`: Pan (alternative to click-drag)
- `Middle Mouse Button + Drag`: Pan
- `Arrow Keys`: Pan in discrete steps

## Performance

### Efficient Movement
- Only updates changed positions
- Batch moves all elements
- Single relationship update pass
- Smooth 60fps movement

### Scroll Region Updates
- Updates once per drag event
- Efficient bounding box calculation
- No redundant updates
- Minimal performance impact

## Status Bar Messages

| Action | Status Message |
|--------|---------------|
| Start panning | "Pan mode - drag to move diagram" |
| Stop panning | "Ready" |
| Hover over class | (No message, cursor changes) |
| Hover over empty space | (No message, cursor changes) |

## Testing

Run `python test_panning.py` to verify:
1. ✓ Click on empty space starts panning
2. ✓ Drag moves all elements together
3. ✓ Cursor changes to four-way arrow while panning
4. ✓ Release stops panning and resets cursor
5. ✓ Clicking on class doesn't trigger panning
6. ✓ Dragging a class doesn't trigger panning
7. ✓ Relationships stay connected during pan
8. ✓ Scroll region updates after panning
9. ✓ Works correctly at different zoom levels
10. ✓ Status bar shows appropriate messages

## User Experience

### Before Panning Feature:
- ❌ Had to drag each class individually to reposition diagram
- ❌ Difficult to move entire diagram
- ❌ Time-consuming to adjust layout
- ❌ No way to center diagram

### After Panning Feature:
- ✅ Quick diagram repositioning
- ✅ Easy navigation of large diagrams
- ✅ Intuitive click-and-drag interaction
- ✅ Visual feedback with cursor changes
- ✅ Smooth, responsive movement
- ✅ Works seamlessly with other features

## Tips

1. **Quick Centering**: Pan to center your diagram in the viewport
2. **Zoom + Pan**: Zoom out to see overview, pan to navigate, zoom in for details
3. **Layout Adjustment**: After importing, pan to position diagram optimally
4. **Presentation**: Use panning to dynamically explore diagram during demos
5. **Large Diagrams**: Pan to navigate between different sections efficiently
