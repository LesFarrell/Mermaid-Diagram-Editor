# Zoom Level Loading Fix

## Problem
When loading a diagram with saved positions, the zoom level was not being applied correctly. Classes would be created at zoom 1.0 even though the saved zoom level was different (e.g., 0.5 or 0.8).

## Root Cause
The `ClassBox.create_visual()` method was hardcoded to use zoom level 1.0:

```python
def create_visual(self):
    """Create visual elements with default zoom level"""
    self.create_visual_with_zoom(1.0)  # ❌ Always 1.0!
```

This meant that even though we set the tool's zoom level before parsing, when classes were created they ignored it and used 1.0 instead.

## Solution
Modified `ClassBox.create_visual()` to use the tool's current zoom level:

```python
def create_visual(self):
    """Create visual elements with current zoom level from tool"""
    zoom_level = 1.0
    if self.tool and hasattr(self, 'zoom_level'):
        zoom_level = self.tool.zoom_level
    self.create_visual_with_zoom(zoom_level)
```

## Loading Sequence
The correct sequence for loading with saved zoom level:

1. **Load position file** - Read saved zoom level and positions
2. **Set zoom level** - Use `set_zoom_level()` to set zoom WITHOUT moving classes
3. **Parse diagram** - Classes are now created at the correct zoom level
4. **Apply positions** - Move classes to saved positions (scaled to current zoom)

```python
# Load positions
positions = self.load_positions(filename)

# Set zoom level BEFORE parsing
if positions and "zoom_level" in positions:
    self.set_zoom_level(positions["zoom_level"])

# Parse diagram (classes created at current zoom)
self.parse_mermaid(mermaid_code, apply_auto_layout=(positions is None))

# Apply positions
if positions:
    self.apply_positions(positions, skip_zoom=True)
```

## Key Methods

### `set_zoom_level(new_zoom)`
Sets zoom level without moving classes (only scales dimensions):
- Updates `self.zoom_level`
- Scales class widths and heights
- Recreates visuals with scaled fonts
- Does NOT move class positions

### `apply_zoom(scale_factor, center_x, center_y)`
Applies zoom transformation with position scaling:
- Updates `self.zoom_level`
- Scales class positions relative to center point
- Scales class dimensions
- Used for interactive zooming (zoom in/out buttons)

## Testing
To verify zoom level is restored correctly:

```bash
python test_zoom_restore.py
```

Expected output:
```
Saved zoom level: 0.41 (41%)
Loaded zoom level: 0.41 (41%)
✓ Zoom level restored correctly!
```

## Benefits
- ✅ Zoom level correctly restored when loading diagrams
- ✅ Classes created at the correct zoom scale
- ✅ Visual appearance matches saved state
- ✅ Font sizes and dimensions scale properly
- ✅ No more "wrong zoom" on load

## Related Files
- `mermaid_diagram_tool.py` - Main implementation
- `test_zoom_restore.py` - Test script
- `test.md.positions.json` - Example position file with zoom level
