# Auto Save/Load Feature

## Overview
The Mermaid Diagram Tool now automatically loads the last used diagram on startup and prompts to save changes before closing or opening a new file.

## New Features

### 1. Load Last Diagram on Startup
- When you start the application, it automatically loads the last diagram you were working on
- The last file path is saved in `mermaid_tool_config.txt`
- If the file no longer exists, starts with a blank diagram

### 2. Unsaved Changes Tracking
The application tracks when you make changes:
- Adding a class
- Deleting a class
- Editing a class (name, attributes, methods, etc.)
- Adding a relationship
- Deleting a relationship
- Creating a class via right-click

### 3. Window Title Indicator
The window title shows:
- Current filename (if saved)
- Asterisk (*) prefix when there are unsaved changes
- Examples:
  - `Mermaid UML Class Diagram Tool` - New, unsaved diagram
  - `diagram.md - Mermaid UML Class Diagram Tool` - Saved diagram
  - `*diagram.md - Mermaid UML Class Diagram Tool` - Unsaved changes

### 4. Save Prompts

#### On Exit (Close Window)
When you try to close the application with unsaved changes:
- Dialog: "You have unsaved changes. Do you want to save before closing?"
- Options:
  - **Yes** - Saves the file then closes
  - **No** - Closes without saving (changes lost)
  - **Cancel** - Returns to the application

#### On New Diagram
When you click "New" with unsaved changes:
- Dialog: "You have unsaved changes. Do you want to save before creating a new diagram?"
- Options:
  - **Yes** - Saves current file then creates new diagram
  - **No** - Creates new diagram without saving (changes lost)
  - **Cancel** - Returns to current diagram

#### On Open File
When you click "Open Mermaid" with unsaved changes:
- Dialog: "You have unsaved changes. Do you want to save before opening a new file?"
- Options:
  - **Yes** - Saves current file then opens new file
  - **No** - Opens new file without saving (changes lost)
  - **Cancel** - Returns to current diagram

### 5. Smart Save Behavior
- First save: Prompts for filename
- Subsequent saves: Saves to the same file automatically
- File path is remembered for next session

## Technical Implementation

### Change Tracking
```python
self.has_unsaved_changes = False  # Tracks if changes were made
self.current_file = None          # Current file path
```

### Methods Added
- `mark_as_changed()` - Called when user makes changes
- `mark_as_saved()` - Called after successful save
- `update_window_title()` - Updates title with file and status
- `save_last_file_path()` - Saves path to config file
- `load_last_file_path()` - Loads path from config file
- `load_last_diagram()` - Loads diagram on startup
- `on_closing()` - Handles window close event

### Config File
- Location: `mermaid_tool_config.txt` (in same directory as script)
- Content: Path to last opened file
- Created automatically when you save a file

## User Workflow Examples

### Example 1: Normal Workflow
1. Start application → Last diagram loads automatically
2. Make changes → Title shows asterisk (*)
3. Save → Asterisk disappears
4. Close → No prompt (no unsaved changes)

### Example 2: Unsaved Changes
1. Start application → Last diagram loads
2. Make changes → Title shows asterisk (*)
3. Try to close → Prompt appears
4. Click "Yes" → Saves and closes
5. Next startup → Loads the saved diagram

### Example 3: Multiple Files
1. Open file A → Make changes → Save
2. Open file B → Prompt to save A → Click "Yes"
3. Make changes to B → Don't save
4. Close application → Prompt to save B
5. Next startup → Loads file B (last opened)

## Benefits

1. **Never Lose Work** - Always prompted before losing changes
2. **Quick Resume** - Continue where you left off
3. **Visual Feedback** - Asterisk shows unsaved status
4. **Flexible** - Can choose to save or discard changes
5. **Automatic** - No manual configuration needed

## Configuration File

The `mermaid_tool_config.txt` file:
- Stores only the last file path
- Plain text format
- Can be deleted to reset (starts fresh)
- Automatically created on first save

## Notes

- Moving classes doesn't mark as changed (only structural changes)
- Zooming and panning don't mark as changed
- Selecting items doesn't mark as changed
- Only actual diagram modifications trigger the unsaved flag
- If save is cancelled, the application stays open

## Testing

To test the feature:
1. Create a new diagram with some classes
2. Close the application → Should prompt to save
3. Save the file
4. Reopen the application → Should load automatically
5. Make a change
6. Try File → New → Should prompt to save
7. Check window title for asterisk indicator
