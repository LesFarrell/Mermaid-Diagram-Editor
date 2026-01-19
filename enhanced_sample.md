# Enhanced Mermaid UML Class Diagram Sample

This sample demonstrates all the enhanced UML features supported by the tool:

```mermaid
classDiagram
    %% Annotations and stereotypes
    Drawable : @FunctionalInterface
    Drawable : <<interface>>
    Shape : @Entity
    Shape : <<abstract>>
    MathUtils : @Utility
    MathUtils : <<utility>>
    
    class Drawable {
        +draw() void
        +getArea() double
    }
    
    class Shape {
        -color String
        #id int
        +getColor() String
        +setColor(color String) void
        *calculateArea() double
    }
    
    class Circle {
        -radius double
        +center Point
        +Circle(radius double)
        +calculateArea() double
        +draw() void
        +getRadius() double
        +setRadius(radius double) void
    }
    
    class Rectangle {
        -width double
        -height double
        +Rectangle(width double, height double)
        +calculateArea() double
        +draw() void
        +getWidth() double
        +getHeight() double
    }
    
    class MathUtils {
        +PI double
        +E double
        +sqrt(x double) double
        +pow(base double, exp double) double
        +max(a double, b double) double
    }
    
    class Point {
        +x double
        +y double
        +Point(x double, y double)
        +distance(other Point) double
    }
    
    %% Enhanced relationships with multiplicities and labels
    Circle "1" --|> "1" Shape : extends
    Rectangle "1" --|> "1" Shape : extends
    Shape "1" ..|> "1" Drawable : implements
    Circle "1" --> "1" Point : has center
    Rectangle "1" ..> "1" MathUtils : uses
    Circle "1" ..> "1" MathUtils : uses
    Shape "1" *-- "0..*" Point : contains points
    
    %% Notes
    note for Drawable "All drawable objects must implement these methods"
    note for Shape "Abstract base class for geometric shapes"
    note for Circle "Represents a circular shape with radius and center"
    note for MathUtils "Utility class with mathematical functions"
```

## Features Demonstrated:

### Class Features:
- **Stereotypes**: `<<interface>>`, `<<abstract>>`, `<<utility>>`
- **Annotations**: `@FunctionalInterface`, `@Entity`, `@Utility`
- **Visibility Modifiers**: `+` (public), `-` (private), `#` (protected)
- **Method Parameters**: `method(param Type) ReturnType`
- **Abstract Methods**: `*methodName()` (shown in italics)
- **Class Notes**: Attached documentation

### Relationship Features:
- **Inheritance**: `--|>` (solid line with triangle)
- **Realization**: `..|>` (dashed line with triangle)
- **Association**: `-->` (solid line with arrow)
- **Dependency**: `..>` (dashed line with arrow)
- **Composition**: `*--` (solid line with filled diamond)
- **Aggregation**: `o--` (solid line with empty diamond)
- **Multiplicities**: `"1"`, `"0..*"`, `"1..*"`
- **Labels**: `: extends`, `: implements`, `: uses`

### Visual Enhancements:
- **Color Coding**: Interfaces (green), Abstract classes (yellow), Concrete classes (blue)
- **Typography**: Abstract methods in italics, stereotypes in gray
- **Notes**: Orange text with emoji indicators
- **Enhanced Layout**: Proper spacing for complex class hierarchies