# Position Restore Fix

## Problem
When loading a diagram, saved positions were not being restored correctly. Classes would appear at incorrect locations, often far off the visible canvas.

## Root Cause
The position saving/loading had two issues:

1. **Coordinate System Mismatch**: Positions were being saved in the current zoom-scaled coordinates (e.g., at zoom 0.5, a class at visual position 100,100 would have actual coordinates of 200,200). When loading, these scaled coordinates were applied directly without accounting for the zoom level.

2. **Zoom Application Order**: The zoom level was being applied AFTER parsing the diagram, which moved all the classes relative to a center point, causing them to end up in the wrong positions.

## Solution

### 1. Normalized Coordinate Storage
Positions are now saved in **normalized coordinates** (zoom 1.0 scale):

```python
def save_positions(self, mermaid_file):
    # Normalize positions to zoom 1.0 for consistent loading
    normalized_x = class_box.x / self.zoom_level
    normalized_y = class_box.y / self.zoom_level
    # Save normalized coordinates
```

### 2. Proper Zoom Restoration
Added `set_zoom_level()` method that sets zoom WITHOUT moving classes:

```python
def set_zoom_level(self, new_zoom):
    """Set zoom level without moving classes (for loading saved state)"""
    scale_factor = new_zoom / self.zoom_level
    self.zoom_level = new_zoom
    
    # Update class dimensions (but NOT positions)
    for class_box in self.classes:
        class_box.width *= scale_factor
        class_box.height *= scale_factor
```

### 3. Correct Loading Sequence
1. Load position file
2. Set zoom level (without moving classes)
3. Parse diagram (creates classes at default positions)
4. Apply saved positions (scaled to current zoom)

```python
# Set zoom level BEFORE parsing
if positions and "zoom_level" in positions:
    self.set_zoom_level(positions["zoom_level"])

# Parse diagram
self.parse_mermaid(mermaid_code, apply_auto_layout=(positions is None))

# Apply positions (scale from normalized to current zoom)
if positions:
    target_x = pos["x"] * self.zoom_level
    target_y = pos["y"] * self.zoom_level
    class_box.move(dx, dy)
```

## Position File Format (v1.2)
```json
{
  "zoom_level": 0.5,
  "classes": {
    "ClassName": {
      "x": 200.0,      // Normalized to zoom 1.0
      "y": 150.0,      // Normalized to zoom 1.0
      "width": 150.0,  // Normalized to zoom 1.0
      "height": 100.0  // Normalized to zoom 1.0
    }
  },
  "metadata": {
    "version": "1.2"  // Updated version number
  }
}
```

## Testing
To test the fix:

1. Open a diagram
2. Move some classes around
3. Zoom in/out
4. Save the diagram (positions auto-save)
5. Close and reopen the diagram
6. Classes should appear exactly where you left them at the same zoom level

## Backward Compatibility
Old position files (v1.1 and earlier) with non-normalized coordinates will need to be regenerated. The application will still load them but positions may be incorrect. Simply move the classes to the desired positions and save again to update to the new format.

## Benefits
- ✅ Positions restore correctly at any zoom level
- ✅ Zoom level is preserved across sessions
- ✅ Coordinates are stored in a zoom-independent format
- ✅ No more classes appearing off-canvas
- ✅ Consistent behavior regardless of zoom state when saving
