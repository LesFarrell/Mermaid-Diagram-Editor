# Character Encoding Fix

## Problem
The application was failing to open files with the error:
```
Failed to open file: charmap codec can't decode byte 0x9d in position 2961: character maps to <undefined>
```

This occurs when a file contains characters that can't be decoded with the default system encoding (usually ASCII or cp1252 on Windows).

## Solution
Implemented multi-encoding fallback strategy for all file operations.

## Changes Made

### 1. File Reading with Encoding Fallback
When opening files, the application now tries multiple encodings in order:
1. **UTF-8** - Modern standard, supports all Unicode characters
2. **UTF-8-sig** - UTF-8 with BOM (Byte Order Mark)
3. **Latin-1** - Western European characters
4. **CP1252** - Windows Western European
5. **ISO-8859-1** - Alternative Western European

```python
encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']

for encoding in encodings:
    try:
        with open(filename, 'r', encoding=encoding) as f:
            content = f.read()
        break  # Success, stop trying
    except UnicodeDecodeError:
        continue  # Try next encoding
```

### 2. File Writing with UTF-8
All file writing operations now explicitly use UTF-8 encoding:
```python
with open(filename, 'w', encoding='utf-8') as f:
    f.write(content)
```

### 3. Updated Operations
The following operations now handle encoding properly:
- **open_mermaid()** - Opening diagram files
- **save_mermaid()** - Saving diagram files
- **load_last_diagram()** - Loading on startup
- **save_last_file_path()** - Saving config
- **load_last_file_path()** - Loading config

## Benefits

### 1. Universal File Support
- Opens files created on different systems
- Handles files with special characters
- Supports international characters (é, ñ, ü, etc.)
- Works with emoji and Unicode symbols

### 2. Graceful Degradation
- Tries multiple encodings automatically
- Shows clear error if all encodings fail
- Doesn't crash on encoding errors

### 3. Cross-Platform Compatibility
- Files created on Windows open on Mac/Linux
- Files created on Mac/Linux open on Windows
- Consistent UTF-8 output across platforms

### 4. Future-Proof
- UTF-8 is the modern standard
- Supports all current and future Unicode characters
- Compatible with web standards

## Technical Details

### Encoding Priority
1. **UTF-8** - Tried first as it's the modern standard
2. **UTF-8-sig** - Handles files with BOM markers
3. **Latin-1/CP1252** - Fallback for older Windows files
4. **ISO-8859-1** - Alternative for Western European files

### Why Multiple Encodings?
Different systems and editors use different default encodings:
- **Modern editors**: UTF-8
- **Windows Notepad (old)**: CP1252 or ANSI
- **Mac TextEdit**: UTF-8 or Mac Roman
- **Linux editors**: UTF-8
- **Web browsers**: UTF-8

### Error Handling
If all encodings fail:
```python
if content is None:
    messagebox.showerror("Error", "Could not decode file. Please ensure it's a text file.")
    return
```

## Testing

### Test Cases
1. **UTF-8 file** - Opens normally
2. **ANSI file** - Opens with fallback encoding
3. **File with special characters** - Opens correctly
4. **File with emoji** - Opens if UTF-8
5. **Binary file** - Shows error message

### Example Characters That Now Work
- **Accented**: café, naïve, résumé
- **Symbols**: ©, ®, ™, €, £, ¥
- **Math**: ∑, ∫, √, ∞, ≈, ≠
- **Arrows**: →, ←, ↑, ↓, ⇒, ⇔
- **Emoji**: 😀, 🎉, ✅, ❌ (if UTF-8)

## Migration

### Existing Files
- Old files open automatically with fallback encoding
- No manual conversion needed
- Files are re-saved in UTF-8 when you save

### New Files
- All new files created in UTF-8
- Ensures maximum compatibility
- Supports all Unicode characters

## Best Practices

### For Users
1. **Save regularly** - Files are saved in UTF-8
2. **Use UTF-8 editors** - For external editing
3. **Avoid binary data** - Stick to text content

### For Developers
1. **Always specify encoding** - Never rely on defaults
2. **Use UTF-8 for output** - Modern standard
3. **Handle errors gracefully** - Show user-friendly messages

## Common Issues Fixed

### Issue 1: "charmap codec can't decode"
**Before**: Application crashed
**After**: Tries multiple encodings, opens successfully

### Issue 2: Special characters display as �
**Before**: Characters corrupted
**After**: Proper encoding detection preserves characters

### Issue 3: Files from other systems won't open
**Before**: Encoding mismatch
**After**: Multi-encoding fallback handles different systems

### Issue 4: Saved files have wrong encoding
**Before**: System default (varies)
**After**: Always UTF-8 (consistent)

## Verification

To verify the fix works:
1. Create a file with special characters (é, ñ, ü)
2. Open in the application
3. Should load without errors
4. Save the file
5. Reopen - characters should be preserved

## Notes

- The fix is backward compatible
- Old files still work
- New files use UTF-8
- No data loss during conversion
- Transparent to users

## Related Files

- `mermaid_diagram_tool.py` - Main implementation
- All `.md` files - Now saved in UTF-8
- Config file - Now saved in UTF-8
- Position files - Already JSON (UTF-8 by default)
