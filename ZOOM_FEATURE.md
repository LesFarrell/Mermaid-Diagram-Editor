# Zoom Feature

## Overview
Full zoom functionality with mouse wheel and toolbar buttons, scaling all elements including text, arrows, and borders.

## Features

### Zoom Controls
1. **Mouse Wheel**: Scroll up to zoom in, scroll down to zoom out
2. **Toolbar Buttons**:
   - `+` button: Zoom in (120% per click)
   - `-` button: Zoom out (80% per click)
   - `Reset` button: Return to 100% zoom
3. **Zoom Display**: Current zoom level shown in toolbar (e.g., "150%")

### Zoom Range
- **Minimum**: 10% (0.1x)
- **Maximum**: 500% (5.0x)
- **Default**: 100% (1.0x)

## What Gets Scaled

### Class Elements
- ✅ **Text sizes**: All fonts scale proportionally
  - Class names (12pt base)
  - Attributes and methods (10pt base)
  - Stereotypes and annotations (10pt/9pt base)
  - Notes (9pt base)
  - Empty class indicators (9pt base)
- ✅ **Box dimensions**: Width and height scale with content
- ✅ **Border widths**: Rectangle borders scale (2px base)
- ✅ **Padding**: Internal spacing scales proportionally
- ✅ **Selection indicators**: Corner squares scale (6px base)

### Relationship Elements
- ✅ **Line widths**: Connection lines scale (2px base, 3px when selected)
- ✅ **Arrow sizes**: All arrow types scale
  - Inheritance triangles (15px base)
  - Composition diamonds (10px base)
  - Aggregation diamonds (10px base)
  - Dependency arrows (12px base)
- ✅ **Label text**: Relationship labels scale (9pt base)
- ✅ **Multiplicity text**: Multiplicity indicators scale (8pt base)

### Canvas Behavior
- ✅ **Scroll region**: Automatically updates after zoom
- ✅ **Element positions**: All elements reposition correctly
- ✅ **Text wrapping**: Text stays within scaled box boundaries

## Technical Implementation

### Zoom Level Tracking
```python
self.zoom_level = 1.0  # Track current zoom level
```

### Mouse Wheel Handler
```python
def on_mouse_wheel(self, event):
    # Zoom in/out based on wheel direction
    if event.delta > 0:
        scale_factor = 1.1  # Zoom in
    else:
        scale_factor = 0.9  # Zoom out
    
    self.apply_zoom(scale_factor, mouse_x, mouse_y)
```

### Zoom Application
```python
def apply_zoom(self, scale_factor, center_x, center_y):
    # Update zoom level
    new_zoom = self.zoom_level * scale_factor
    
    # Limit range (0.1 to 5.0)
    if new_zoom < 0.1 or new_zoom > 5.0:
        return
    
    # Update class positions relative to zoom center
    for class_box in self.classes:
        class_box.x = center_x + (class_box.x - center_x) * scale_factor
        class_box.y = center_y + (class_box.y - center_y) * scale_factor
        class_box.width *= scale_factor
        class_box.height *= scale_factor
    
    # Recreate all visuals with scaled fonts
    self.recreate_visuals_with_zoom()
```

### Font Scaling
```python
# Base font sizes
base_font_name_size = 12
base_font_content_size = 10
base_font_small_size = 9

# Scaled font sizes
font_name_size = max(1, int(base_font_name_size * zoom_level))
font_content_size = max(1, int(base_font_content_size * zoom_level))
font_small_size = max(1, int(base_font_small_size * zoom_level))
```

### Width Calculation with Zoom
```python
# Minimum width scaled by zoom
max_width = int(150 * zoom_level)

# Measure text with scaled fonts
temp_text = canvas.create_text(0, 0, text=text, font=scaled_font)
bbox = canvas.bbox(temp_text)
width = bbox[2] - bbox[0] + int(40 * zoom_level)  # Scaled padding

# Update width (with max limit)
self.width = min(max_width, int(400 * zoom_level))
```

### Element Recreation
All visual elements are recreated (not just scaled) to ensure:
- Text is properly positioned
- Fonts are correct size
- Borders are correct width
- Everything stays within bounds

## User Experience

### Zoom In (Mouse Wheel Up / + Button)
- Elements get larger
- Text becomes more readable
- Details are easier to see
- Useful for editing small text or complex diagrams

### Zoom Out (Mouse Wheel Down / - Button)
- Elements get smaller
- More diagram fits on screen
- Overview of entire structure
- Useful for large diagrams with many classes

### Reset (Reset Button)
- Returns to 100% zoom
- Original size and proportions
- Quick way to return to default view

### Zoom Center Point
- **Mouse wheel**: Zooms toward/away from mouse cursor position
- **Toolbar buttons**: Zooms toward/away from canvas center
- Elements closer to zoom point move less
- Elements farther from zoom point move more

## Behavior Details

### Text Positioning
- Text is recreated at correct positions for zoom level
- No text falls outside boxes
- Proper wrapping within scaled boundaries
- Padding scales proportionally

### Class Dimensions
- Width recalculated based on content at new zoom level
- Height adjusted for scaled line spacing
- Minimum dimensions maintained (scaled)
- Maximum width limit respected (scaled)

### Relationships
- Lines connect to correct edge points
- Arrows scale proportionally
- Labels remain readable
- Multiplicities scale with relationships

### Selection Indicators
- Corner squares scale with zoom
- Border width scales appropriately
- Indicators remain visible at all zoom levels

### Scroll Region
- Automatically updates after zoom
- Includes all elements with padding
- Scrollbars adjust to new content size

## Performance

### Efficient Scaling
- Only recreates visuals when zoom changes
- Reuses existing class data
- No redundant calculations
- Smooth zoom transitions

### Memory Management
- Old visual elements properly deleted
- No memory leaks from scaling
- Efficient canvas item management

## Use Cases

### Detailed Editing (Zoom In)
- Edit long method signatures
- Read small text clearly
- Precise positioning of elements
- Fine-tune relationships

### Overview (Zoom Out)
- See entire diagram structure
- Understand high-level architecture
- Navigate large diagrams
- Plan layout changes

### Presentation
- Zoom in to focus on specific classes
- Zoom out to show overall design
- Dynamic exploration during demos
- Better visibility for audiences

## Testing

Run `python test_zoom.py` to verify:
1. Mouse wheel zooms in/out smoothly
2. Toolbar buttons work correctly
3. Zoom level displays accurately
4. Text scales and stays within boxes
5. All elements scale proportionally
6. Scroll region updates properly
7. Can zoom from 10% to 500%
8. Reset returns to 100%
9. Dragging works at any zoom level
10. Creating classes works at any zoom level

## Keyboard Shortcuts (Future Enhancement)
- `Ctrl +` or `Ctrl =`: Zoom in
- `Ctrl -`: Zoom out
- `Ctrl 0`: Reset to 100%

## Status Bar Integration
- Shows current zoom level during zoom operations
- Format: "Zoom: 150%"
- Updates in real-time
- Clears after zoom completes
