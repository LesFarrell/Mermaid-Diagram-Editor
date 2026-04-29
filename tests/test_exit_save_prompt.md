# Test: Exit Save Prompt

## Overview
This test verifies that the application prompts you to save changes when exiting with unsaved modifications.

## Test Scenarios

### Test 1: Exit with Unsaved New Class
1. Start the application
2. Add a new class (right-click or "Add Class" button)
3. Try to close the window (click X)
4. **Expected**: Dialog appears: "You have unsaved changes. Do you want to save before closing?"
5. **Options**:
   - **Yes** → Prompts for filename, saves, then closes
   - **No** → Closes without saving (changes lost)
   - **Cancel** → Returns to application

### Test 2: Exit with Unsaved Edits
1. Open an existing diagram
2. Double-click a class to edit it
3. Change the class name or add attributes
4. Click OK
5. Try to close the window
6. **Expected**: Save prompt appears
7. Test all three options (Yes/No/Cancel)

### Test 3: Exit with Unsaved Relationship
1. Open or create a diagram with classes
2. Add a relationship between two classes
3. Try to close the window
4. **Expected**: Save prompt appears

### Test 4: Exit with Unsaved Deletion
1. Open a diagram
2. Select a class or relationship
3. Press Delete key
4. Try to close the window
5. **Expected**: Save prompt appears

### Test 5: Exit with Moved Classes
1. Open a diagram
2. Drag a class to a new position
3. Try to close the window
4. **Expected**: Save prompt appears (position changes count!)

### Test 6: Exit After Saving
1. Make changes to a diagram
2. Save the diagram (File → Save)
3. Try to close the window
4. **Expected**: No prompt, closes immediately (no unsaved changes)

### Test 7: Make Changes After Save
1. Open a diagram
2. Make a change
3. Save the diagram
4. Make another change
5. Try to close the window
6. **Expected**: Save prompt appears (new changes after save)

### Test 8: Window Title Indicator
1. Open a diagram
2. **Check**: Title shows filename without asterisk
3. Make a change
4. **Check**: Title shows asterisk (*) before filename
5. Save the diagram
6. **Check**: Asterisk disappears
7. Make another change
8. **Check**: Asterisk reappears

### Test 9: Cancel Save Dialog
1. Make changes to a diagram
2. Try to close the window
3. Click "Yes" in the save prompt
4. In the file save dialog, click "Cancel"
5. **Expected**: Returns to application (doesn't close)

### Test 10: Multiple Changes
1. Create a new diagram
2. Add 3 classes
3. Add 2 relationships
4. Edit 1 class
5. Move 1 class
6. Try to close
7. **Expected**: Single save prompt for all changes

## What Triggers "Unsaved Changes"

The following actions mark the diagram as changed:
- ✅ Adding a class
- ✅ Deleting a class
- ✅ Editing a class (name, attributes, methods, etc.)
- ✅ Adding a relationship
- ✅ Deleting a relationship
- ✅ Moving a class (dragging)
- ✅ Creating a class via right-click

The following do NOT trigger unsaved changes:
- ❌ Selecting a class
- ❌ Zooming in/out
- ❌ Panning the canvas
- ❌ Hovering over elements
- ❌ Opening the edit dialog without making changes

## Visual Indicators

### Window Title Format
```
No changes:     diagram.md - Mermaid UML Class Diagram Tool
With changes:   *diagram.md - Mermaid UML Class Diagram Tool
New diagram:    Mermaid UML Class Diagram Tool
New + changes:  *Mermaid UML Class Diagram Tool
```

### Save Prompt Dialog
```
Title: "Unsaved Changes"
Message: "You have unsaved changes. Do you want to save before closing?"
Buttons: [Yes] [No] [Cancel]
```

## Expected Behavior

### Clicking "Yes"
1. If file was previously saved → Saves to same file
2. If new diagram → Prompts for filename
3. After successful save → Closes application
4. If save cancelled → Returns to application

### Clicking "No"
1. Closes application immediately
2. All changes are lost
3. No further prompts

### Clicking "Cancel"
1. Returns to application
2. Changes remain
3. Can continue working

## Integration with Other Features

### Works With Auto-Load
1. Make changes to a diagram
2. Close without saving (click "No")
3. Reopen application
4. **Expected**: Loads last saved version (changes lost)

### Works With Position Saving
1. Move classes to new positions
2. Try to close
3. **Expected**: Prompted to save (positions are changes)
4. Save and close
5. Reopen
6. **Expected**: Classes in new positions

### Works With File → New
1. Make changes to current diagram
2. Click File → New
3. **Expected**: Prompted to save current diagram first
4. Same Yes/No/Cancel options

### Works With File → Open
1. Make changes to current diagram
2. Click File → Open
3. **Expected**: Prompted to save current diagram first
4. Same Yes/No/Cancel options

## Troubleshooting

### Prompt Not Appearing?
- Check if you actually made changes
- Verify window title shows asterisk (*)
- Try a different type of change (add class, edit, etc.)

### Prompt Appearing When It Shouldn't?
- Check if you accidentally made a change
- Look for asterisk in window title
- Save the file to clear the flag

### Can't Close Application?
- Click "No" to close without saving
- Or click "Cancel" and then save manually

## Notes

- The prompt only appears if there are unsaved changes
- Saving clears the unsaved flag
- The asterisk (*) in the title is your visual indicator
- Position changes are tracked (moving classes counts!)
- All structural changes are tracked
- The feature works with all file operations (New, Open, Close)

## Success Criteria

✅ Prompt appears when closing with unsaved changes
✅ Prompt does NOT appear when closing without changes
✅ "Yes" button saves and closes
✅ "No" button closes without saving
✅ "Cancel" button returns to application
✅ Window title shows asterisk when there are changes
✅ Asterisk disappears after saving
✅ Works with all types of changes (add, edit, delete, move)
✅ Integrates with File → New and File → Open
✅ Position changes trigger the prompt
