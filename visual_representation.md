# Visual Representation of Imported Mermaid Diagram

When you import the `sample_diagram.md` file using the tool, here's what gets created:

## Classes Created (6 total):

### 📦 User Class
- **Position**: Grid layout (automatically arranged)
- **Attributes**: id, username, email, password
- **Methods**: login(), logout(), updateProfile()
- **Visual**: Blue box with red selection indicators when clicked

### 📦 Customer Class  
- **Inherits from**: User (triangle arrow pointing to User)
- **Attributes**: address, phone, creditCard
- **Methods**: placeOrder(), viewOrderHistory()

### 📦 Admin Class
- **Inherits from**: User (triangle arrow pointing to User)  
- **Attributes**: permissions
- **Methods**: manageUsers(), manageProducts(), viewReports()

### 📦 Product Class
- **Attributes**: id, name, price, description, stock
- **Methods**: updateStock(), getDetails()

### 📦 Order Class
- **Associated with**: Customer (simple arrow from Customer)
- **Attributes**: id, orderDate, totalAmount, status
- **Methods**: calculateTotal(), updateStatus(), cancel()

### 📦 OrderItem Class
- **Composed by**: Order (filled diamond from Order)
- **Associated with**: Product (simple arrow to Product)
- **Attributes**: quantity, unitPrice
- **Methods**: getSubtotal()

## Relationships Created (5 total):

1. **Customer → User** (Inheritance - triangle arrow)
2. **Admin → User** (Inheritance - triangle arrow)  
3. **Customer → Order** (Association - simple arrow)
4. **Order → OrderItem** (Composition - filled diamond)
5. **OrderItem → Product** (Association - simple arrow)

## Interactive Features Available:

- ✅ **Drag & Drop**: Move any class around the canvas
- ✅ **Edit Classes**: Double-click to modify attributes/methods
- ✅ **Selection**: Click to select (shows red border + corner squares)
- ✅ **Add Relationships**: Create new relationships between classes
- ✅ **Delete**: Select and press Delete key to remove classes
- ✅ **Export**: Generate updated Mermaid code after editing

## Layout:
The classes are automatically arranged in a grid pattern:
```
[User]     [Customer]  [Admin]
[Product]  [Order]     [OrderItem]
```

All relationships are drawn with appropriate arrows and symbols connecting the classes based on their types (inheritance triangles, composition diamonds, etc.).

## Usage Instructions:

1. Run: `python mermaid_diagram_tool.py`
2. Go to File → Import Mermaid
3. Select `sample_diagram.md`
4. The diagram will be automatically created and displayed
5. You can now edit, rearrange, and modify the imported diagram visually!