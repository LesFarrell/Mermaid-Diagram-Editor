# Position Save Fix

## Problem
Positions were not being saved automatically when moving classes around. The position file was only updated when explicitly saving the diagram file (File → Save).

## Root Cause
The `save_positions()` method was only called in the `save_mermaid()` method, meaning:
- Moving classes didn't trigger position saves
- Closing the application didn't save positions unless you explicitly saved the diagram
- Panning the canvas didn't save positions

## Solution
Added automatic position saving in three key places:

### 1. After Dragging a Class (`ClassBox.on_release`)
When you finish dragging a class, positions are now auto-saved:
```python
def on_release(self, event):
    if self.tool:
        if hasattr(self, '_was_dragged') and self._was_dragged:
            self.tool.mark_as_changed()
            
            # Auto-save positions when class is moved
            if self.tool.current_file and os.path.exists(self.tool.current_file):
                try:
                    self.tool.save_positions(self.tool.current_file)
                except Exception as e:
                    print(f"Warning: Could not auto-save positions: {e}")
            
            self._was_dragged = False
```

### 2. After Panning the Canvas (`canvas_release`)
When you finish panning (moving all classes), positions are auto-saved:
```python
def canvas_release(self, event):
    if self.is_panning:
        self.is_panning = False
        self.canvas.config(cursor="")
        self.update_status("Ready")
        
        # Auto-save positions after panning
        if self.current_file and os.path.exists(self.current_file):
            try:
                self.save_positions(self.current_file)
            except Exception as e:
                print(f"Warning: Could not auto-save positions after panning: {e}")
```

### 3. On Application Close (`on_closing`)
When closing the application, positions are saved even if the diagram itself hasn't changed:
```python
def on_closing(self):
    # ... existing unsaved changes check ...
    
    # Auto-save positions if we have a current file
    if self.current_file and os.path.exists(self.current_file):
        try:
            self.save_positions(self.current_file)
        except Exception as e:
            print(f"Warning: Could not save positions on exit: {e}")
    
    # ... rest of closing logic ...
```

## Benefits
- ✅ Positions are saved immediately after moving classes
- ✅ Positions are saved after panning the canvas
- ✅ Positions are saved when closing the application
- ✅ No need to explicitly save the diagram to preserve positions
- ✅ Silent failures (prints warnings but doesn't interrupt workflow)

## Testing
Run `test_position_save.py` to verify:
1. Position file exists
2. Contains valid JSON
3. Has correct structure (zoom_level, classes, canvas_viewport)
4. Timestamp updates when you move classes

## Position File Format
```json
{
  "zoom_level": 1.0,
  "canvas_viewport": {
    "xview": [0.0, 1.0],
    "yview": [0.0, 1.0]
  },
  "classes": {
    "ClassName": {
      "x": 100.0,
      "y": 200.0,
      "width": 150.0,
      "height": 100.0
    }
  },
  "metadata": {
    "version": "1.1",
    "saved_at": "timestamp"
  }
}
```

## Notes
- Position files are named `<diagram_file>.positions.json`
- Position saving is optional and fails silently if there are issues
- Positions are only saved if a diagram file is currently open
- The file must exist on disk (not just in memory)
