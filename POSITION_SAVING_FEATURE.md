# Position Saving Feature

## Overview
The Mermaid Diagram Tool now saves and restores the exact positions of all classes and the zoom level, preserving your custom layout between sessions.

## How It Works

### Automatic Position Saving
When you save a diagram, the tool automatically creates a companion file that stores:
- X and Y coordinates of each class
- Width and height of each class
- Current zoom level
- Metadata (version, timestamp)

### File Structure
For a diagram file named `my_diagram.md`, the tool creates:
- `my_diagram.md` - The Mermaid diagram (standard format)
- `my_diagram.md.positions.json` - Position data (JSON format)

### Position File Format
```json
{
  "zoom_level": 1.0,
  "classes": {
    "ClassName1": {
      "x": 200,
      "y": 150,
      "width": 180,
      "height": 120
    },
    "ClassName2": {
      "x": 450,
      "y": 150,
      "width": 200,
      "height": 140
    }
  },
  "metadata": {
    "version": "1.0",
    "saved_at": "1234567890.123"
  }
}
```

## Features

### 1. Preserves Custom Layouts
- Manually arranged classes stay in place
- No need to re-layout after opening
- Works with any arrangement (grid, hierarchical, custom)

### 2. Saves Zoom Level
- Restores the exact zoom level you were using
- Maintains the same view scale
- Useful for large diagrams

### 3. Automatic Loading
- Positions load automatically when opening a file
- Works with "Open Mermaid" command
- Works with startup auto-load feature

### 4. Backward Compatible
- If no position file exists, uses default layout
- Old diagrams still work (just without saved positions)
- Position files are optional

### 5. Transparent Operation
- Position saving happens automatically
- No extra steps required
- Status bar shows when positions are loaded

## User Workflow

### Saving with Positions
1. Arrange your classes as desired
2. Adjust zoom level if needed
3. Save the diagram (File → Save or Ctrl+S)
4. Position file is created automatically

### Loading with Positions
1. Open a diagram (File → Open)
2. Classes appear in saved positions
3. Zoom level is restored
4. Status bar confirms: "Loaded from filename.md (with saved positions)"

### Without Position File
1. Open a diagram without a position file
2. Classes use default grid layout
3. Status bar shows: "Loaded from filename.md"
4. You can arrange and save to create position file

## Benefits

### 1. Time Saving
- No need to rearrange classes every time
- Instant restoration of your layout
- Preserves hours of manual positioning work

### 2. Consistency
- Same layout every time you open the file
- Team members see the same arrangement
- Professional, polished diagrams

### 3. Large Diagrams
- Essential for complex diagrams with many classes
- Maintains carefully crafted layouts
- Zoom level preservation helps navigation

### 4. Collaboration
- Share both .md and .positions.json files
- Everyone sees the same layout
- Reduces confusion and miscommunication

## Technical Details

### Position Calculation
- Positions are absolute canvas coordinates
- Independent of window size
- Scaled appropriately with zoom level

### Class Identification
- Classes identified by name
- Spaces in names converted to underscores
- Matches Mermaid class naming convention

### Zoom Restoration
- Calculates scale factor from saved zoom
- Applies zoom transformation
- Maintains relative positions

### Error Handling
- Missing position file: Uses default layout
- Corrupted position file: Falls back gracefully
- Class name mismatch: Positions available classes

## File Management

### Position Files
- Created automatically on save
- Plain JSON format (human-readable)
- Can be edited manually if needed
- Small file size (typically < 1KB)

### Sharing Diagrams
To share a diagram with positions:
1. Share both files:
   - `diagram.md`
   - `diagram.md.positions.json`
2. Recipient opens `diagram.md`
3. Positions load automatically

### Version Control
Both files can be committed to Git:
```bash
git add diagram.md diagram.md.positions.json
git commit -m "Add class diagram with layout"
```

## Examples

### Example 1: Custom Layout
```
Before Save:
- Manually arrange classes in a specific pattern
- Adjust zoom to 150%
- Save diagram

After Reopen:
- Classes appear in exact same positions
- Zoom is at 150%
- Ready to continue work
```

### Example 2: Team Collaboration
```
Developer A:
- Creates diagram
- Arranges classes logically
- Saves and commits both files

Developer B:
- Pulls changes
- Opens diagram
- Sees exact same layout as Developer A
```

### Example 3: Large Diagram
```
Complex System:
- 50+ classes
- Carefully organized by subsystem
- Custom grouping and spacing
- Zoom at 75% for overview

After Save/Load:
- All 50+ classes in correct positions
- Zoom at 75%
- No need to reorganize
```

## Limitations

### Class Name Changes
- If you rename a class, its position is lost
- Workaround: Rename in both diagram and position file
- Or: Rearrange and save again

### Manual Position File Editing
- Possible but not recommended
- Use JSON format strictly
- Backup before editing

### File Synchronization
- Both files must be kept together
- Deleting position file reverts to default layout
- Moving files: Move both together

## Tips

### Best Practices
1. **Save Often** - Positions saved with each save
2. **Commit Both Files** - Keep them synchronized in version control
3. **Backup** - Position files are small, easy to backup
4. **Share Together** - Always share both files with team

### Troubleshooting
- **Positions not loading?** - Check if .positions.json file exists
- **Wrong positions?** - Delete position file and rearrange
- **Classes overlapping?** - Use Auto Layout, then save new positions
- **Zoom wrong?** - Manually adjust and save again

## Future Enhancements

Potential improvements:
- Export positions to different formats
- Import positions from other tools
- Position templates for common layouts
- Animated transitions when loading positions
- Position history/undo for layouts
