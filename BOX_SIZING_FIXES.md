# Box Sizing Fixes

## Issues Fixed

### 1. Boxes Expanding Too Much When Zoomed
**Problem:** When zooming in, boxes would become excessively large because width/height calculations were being scaled by zoom multiple times.

**Solution:**
- Calculate box dimensions using **base font sizes** (not scaled)
- Measure text width/height at normal size
- Only apply zoom scaling **once** at the end
- Base width calculation: measure → determine size → then scale
- Base height calculation: count lines → calculate height → then scale

### 2. Text Drawing Outside Boxes
**Problem:** Text would overflow outside the box boundaries, especially with long attribute/method names.

**Solution:**
- Increased maximum base width from 400px to 500px
- Added proper text padding calculation (10px scaled by zoom)
- Set `width` parameter on text items to constrain them within box bounds
- Text automatically wraps if it exceeds available width
- Box height dynamically expands if content requires more space

### 3. Improved Text Wrapping
- Calculate available width: `box_width - (2 * padding)`
- Apply width constraint to all text items (attributes, methods, notes)
- Check actual rendered text height after wrapping
- Adjust y_offset based on actual text height
- Expand box height if content exceeds initial calculation

## Technical Changes

### Width Calculation
```python
# OLD: Scaled measurements
max_width = int(150 * zoom_level)
font_size = int(10 * zoom_level)
# Measurements were already scaled

# NEW: Base measurements, then scale
base_min_width = 150
font_size = 10  # Base size
# Measure at base size
base_width = calculate_width()
self.width = int(base_width * zoom_level)  # Scale once
```

### Height Calculation
```python
# OLD: Scaled line height
calculated_height = int((content_lines * 20 + 30) * zoom_level)

# NEW: Base calculation, then scale
base_line_height = 20
base_padding = 30
base_height = content_lines * base_line_height + base_padding
self.height = int(base_height * zoom_level)  # Scale once
```

### Text Rendering
```python
# OLD: Width constraint scaled by zoom
width=self.width - int(20 * zoom_level)

# NEW: Calculate available width properly
text_padding = int(10 * zoom_level)
available_width = self.width - (2 * text_padding)
width=available_width
```

## Benefits

1. **Consistent sizing** - Boxes maintain proper proportions at all zoom levels
2. **No text overflow** - All text stays within box boundaries
3. **Dynamic expansion** - Boxes grow if content needs more space
4. **Better readability** - Proper padding and text wrapping
5. **Zoom stability** - Boxes don't become excessively large when zoomed

## Test File

Use `test_box_sizing.md` to test:
- Very long class/attribute/method names
- Short names
- Empty classes
- Various zoom levels (use +/- buttons or mouse wheel)

## Zoom Behavior

- **100% (1.0x)**: Normal size, all text fits properly
- **50% (0.5x)**: Smaller, text still readable and contained
- **200% (2.0x)**: Larger, boxes scale proportionally without excessive expansion
- **500% (5.0x)**: Maximum zoom, boxes remain properly sized
