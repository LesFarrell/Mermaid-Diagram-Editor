# Exit Save Prompt - Feature Summary

## Overview
The Mermaid Diagram Tool automatically prompts you to save changes when you try to exit the application with unsaved modifications.

## How It Works

### Automatic Detection
The application tracks all changes you make:
- Adding/deleting classes
- Editing class properties
- Adding/deleting relationships
- Moving classes (dragging)
- Any structural modifications

### Visual Indicator
The window title shows an asterisk (*) when there are unsaved changes:
```
*diagram.md - Mermaid UML Class Diagram Tool
```

### Exit Prompt
When you try to close the application with unsaved changes, a dialog appears:

**Title**: "Unsaved Changes"

**Message**: "You have unsaved changes. Do you want to save before closing?"

**Options**:
- **Yes** - Saves the file then closes the application
- **No** - Closes without saving (changes are lost)
- **Cancel** - Returns to the application (keeps working)

## Implementation Details

### Change Tracking
```python
self.has_unsaved_changes = False  # Tracks modification state
```

### Methods That Mark Changes
- `add_class()` - Adding a new class
- `add_class_at_position()` - Right-click to create class
- `delete_selected()` - Deleting classes or relationships
- `canvas_click()` - Adding relationships
- `ClassEditDialog.ok_clicked()` - Editing class properties
- `ClassBox.on_release()` - Finishing a drag operation

### Window Close Handler
```python
def on_closing(self):
    if self.has_unsaved_changes:
        response = messagebox.askyesnocancel(
            "Unsaved Changes",
            "You have unsaved changes. Do you want to save before closing?"
        )
        
        if response is None:  # Cancel
            return
        elif response:  # Yes - save
            self.save_mermaid()
            if self.has_unsaved_changes:  # Save was cancelled
                return
    
    self.save_last_file_path()
    self.root.destroy()
```

### Integration Points
The prompt also appears when:
- Creating a new diagram (File → New)
- Opening another file (File → Open)
- Closing the application window

## User Experience

### Typical Workflow
1. **Make changes** → Asterisk appears in title
2. **Try to close** → Prompt appears
3. **Choose action**:
   - Save and close
   - Discard and close
   - Cancel and continue working

### Safety Features
- **Never lose work accidentally** - Always prompted before losing changes
- **Visual feedback** - Asterisk shows unsaved status at all times
- **Flexible options** - Choose to save, discard, or cancel
- **Smart detection** - Only prompts when there are actual changes

### Position Changes
Moving classes now triggers the unsaved flag:
- Drag a class to a new position
- Release the mouse button
- Application marks as changed
- Exit prompt will appear if you try to close

## Benefits

1. **Data Protection** - Prevents accidental loss of work
2. **User Control** - You decide whether to save or discard
3. **Clear Feedback** - Asterisk shows unsaved status
4. **Consistent Behavior** - Works across all exit scenarios
5. **Position Preservation** - Even layout changes are protected

## Technical Notes

### Change Detection
- Tracks structural changes only
- Doesn't track view changes (zoom, pan, selection)
- Resets after successful save
- Persists across file operations

### Save Behavior
- First save: Prompts for filename
- Subsequent saves: Uses current filename
- Cancelled save: Returns to application
- Failed save: Shows error, keeps unsaved flag

### Window Protocol
```python
self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
```
This intercepts the window close event before the application exits.

## Testing

See `test_exit_save_prompt.md` for comprehensive test scenarios including:
- Exit with various types of changes
- Window title indicator verification
- Save dialog cancellation
- Integration with other features
- Position change tracking

## Related Features

- **Auto-load on startup** - Loads last diagram automatically
- **Position saving** - Preserves class positions
- **File operations** - Prompts before New/Open with unsaved changes
- **Window title** - Shows file and unsaved status

## Code Locations

Key methods in `mermaid_diagram_tool.py`:
- `__init__()` - Sets up window close handler
- `on_closing()` - Handles exit with prompt
- `mark_as_changed()` - Marks diagram as modified
- `mark_as_saved()` - Clears unsaved flag
- `update_window_title()` - Updates title with asterisk
- `ClassBox.on_release()` - Marks changes after dragging

## Future Enhancements

Potential improvements:
- Auto-save timer (save every N minutes)
- Backup copies before closing without saving
- Change history/undo system
- Configurable prompt behavior
- Save reminder after X changes
