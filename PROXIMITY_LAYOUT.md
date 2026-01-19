# Proximity-Based Layout Improvements

## Overview
Enhanced the hierarchical layout algorithm to keep related classes closer together based on their relationships.

## Key Improvements

### 1. Connection Tracking
- Tracks **all relationships** (not just hierarchical ones)
- Builds a connection map for each class
- Uses this to determine proximity preferences

### 2. Smart Sorting Within Levels
Classes within the same level are now sorted to keep related ones together:

**Algorithm:**
1. Start with the class that has the most connections overall
2. Iteratively add classes that have connections to already-placed classes
3. Classes with more connections to placed classes are added first
4. Result: Related classes cluster together

**Example:**
```
Before: [ClassA, ClassB, ClassC, ClassD]
After:  [ClassA, ClassC, ClassD, ClassB]
         (if A-C-D are connected, B is separate)
```

### 3. Force-Directed Adjustment
After initial placement, applies physics-based forces:

**Attraction Forces:**
- Connected classes pull toward each other
- Force strength proportional to distance
- Only horizontal movement (preserves level structure)

**Parameters:**
- 5 iterations of force application
- 0.1 force magnitude (spring-like)
- 0.5 damping factor (prevents oscillation)
- Max 20px movement per iteration (prevents chaos)

### 4. Reduced Horizontal Gap
- Changed from 80px to 60px between classes
- Allows related classes to be visually closer
- Still maintains readability

## Technical Details

### Connection Map
```python
all_connections[cls] = set()
# Tracks bidirectional relationships
all_connections[rel.from_class].add(rel.to_class)
all_connections[rel.to_class].add(rel.from_class)
```

### Sorting Score
```python
score = sum(1 for sorted_cls in sorted_level 
           if sorted_cls in all_connections[candidate])
# Higher score = more connections to already-placed classes
```

### Force Calculation
```python
force_magnitude = distance * 0.1
move_x = (dx / distance) * force_magnitude * damping
# Attraction force pulls connected classes together
```

## Benefits

1. **Visual Clarity** - Related classes are grouped together
2. **Shorter Lines** - Connections between related classes are shorter
3. **Better Organization** - Logical grouping emerges naturally
4. **Maintained Hierarchy** - Vertical structure preserved
5. **Reduced Clutter** - Less line crossing

## Example Scenarios

### Scenario 1: Repository Pattern
```
Database (top)
  ↓
[UserRepo, ProductRepo, OrderRepo] (grouped together)
  ↓
[UserService, ProductService, OrderService] (grouped together)
  ↓
[UserController, ProductController, OrderController] (grouped together)
```

### Scenario 2: Inheritance Tree
```
Animal (top)
  ↓
[Dog, Cat, Bird] (siblings grouped)
  ↓
[GermanShepherd, Poodle] (Dog's children near Dog)
```

### Scenario 3: Complex Dependencies
```
ClassA (top)
  ↓
[ClassB, ClassC] (both depend on A, grouped)
  ↓
ClassD (depends on both B and C, positioned between them)
```

## Usage

1. Open any Mermaid diagram
2. Click "Auto Layout" button
3. Algorithm automatically:
   - Determines hierarchy
   - Sorts classes by connections
   - Applies force-directed adjustment
   - Resolves overlaps
   - Updates display

## Test Files

- `test_proximity_layout.md` - Repository/Service/Controller pattern
- `test_layout_demo.md` - Vehicle inheritance hierarchy
- `showcase_layout.md` - Shape rendering system

## Configuration

You can adjust these parameters in the code:

```python
horizontal_gap = 60      # Space between classes (px)
vertical_gap = 100       # Space between levels (px)
iterations = 5           # Force-directed iterations
force_magnitude = 0.1    # Attraction strength
damping = 0.5           # Movement damping
max_move = 20           # Max movement per iteration (px)
```

## Future Enhancements

Potential improvements:
- User-adjustable force strength
- Different layouts for different relationship types
- Manual pinning of specific classes
- Animated layout transitions
- Save/load layout preferences
