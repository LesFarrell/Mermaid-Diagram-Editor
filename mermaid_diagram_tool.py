import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import math
import re
import os

class ClassBox:
    def __init__(self, canvas, x, y, name="NewClass", tool=None):
        self.canvas = canvas
        self.tool = tool  # Reference to main tool for updating relationships
        self.x = x
        self.y = y
        self.name = name
        self.attributes = []
        self.methods = []
        self.annotations = []  # Class annotations like @interface, @abstract
        self.stereotype = ""   # Stereotype like <<interface>>, <<abstract>>
        self.notes = []        # Notes attached to this class
        self.visibility = "public"  # public, private, protected, package
        self.width = 150
        self.height = 100
        self.selected = False
        self.drag_data = {"x": 0, "y": 0}
        
        self.create_visual()
        
    def create_visual(self):
        """Create visual elements with current zoom level from tool"""
        zoom_level = 1.0
        if self.tool and hasattr(self.tool, 'zoom_level'):
            zoom_level = self.tool.zoom_level
        self.create_visual_with_zoom(zoom_level)
    
    def create_visual_with_zoom(self, zoom_level):
        """Create visual elements with specified zoom level"""
        # Delete any existing visual elements first to prevent duplicates
        if hasattr(self, 'rect'):
            self.canvas.delete(self.rect)
        if hasattr(self, 'name_text'):
            self.canvas.delete(self.name_text)
        if hasattr(self, 'sep_line'):
            self.canvas.delete(self.sep_line)
        if hasattr(self, 'stereotype_text'):
            self.canvas.delete(self.stereotype_text)
        if hasattr(self, 'annotation_texts'):
            for text in self.annotation_texts:
                self.canvas.delete(text)
        if hasattr(self, 'selection_indicators'):
            for indicator in self.selection_indicators:
                self.canvas.delete(indicator)
        
        # Clear content elements
        for item in self.canvas.find_withtag("content_" + str(id(self))):
            self.canvas.delete(item)
        
        # Calculate width based on actual text measurements
        # Start with minimum width (NOT scaled by zoom - use base size)
        base_min_width = 150
        max_width = base_min_width
        
        # Use BASE font sizes (not scaled by zoom)
        base_font_name_size = 12
        base_font_content_size = 10
        base_font_small_size = 9
        
        # For measurement, use base fonts
        temp_font_name = ("Arial", base_font_name_size, "bold")
        temp_font_content = ("Arial", base_font_content_size)
        temp_font_small = ("Arial", base_font_small_size, "italic")
        
        # Padding in base units
        base_padding = 40
        
        # Check class name width
        temp_text = self.canvas.create_text(0, 0, text=self.name, font=temp_font_name)
        name_bbox = self.canvas.bbox(temp_text)
        if name_bbox:
            name_width = name_bbox[2] - name_bbox[0] + base_padding
            max_width = max(max_width, name_width)
        self.canvas.delete(temp_text)
        
        # Check stereotype width
        if self.stereotype:
            temp_text = self.canvas.create_text(0, 0, text=f"<<{self.stereotype}>>", font=("Arial", base_font_content_size, "italic"))
            bbox = self.canvas.bbox(temp_text)
            if bbox:
                width = bbox[2] - bbox[0] + base_padding
                max_width = max(max_width, width)
            self.canvas.delete(temp_text)
        
        # Check annotation widths
        for annotation in self.annotations:
            temp_text = self.canvas.create_text(0, 0, text=f"@{annotation}", font=("Arial", base_font_small_size, "italic"))
            bbox = self.canvas.bbox(temp_text)
            if bbox:
                width = bbox[2] - bbox[0] + base_padding
                max_width = max(max_width, width)
            self.canvas.delete(temp_text)
        
        # Check attribute widths
        for attr in self.attributes:
            attr_text = self.format_member(attr, is_method=False)
            temp_text = self.canvas.create_text(0, 0, text=attr_text, font=temp_font_content)
            bbox = self.canvas.bbox(temp_text)
            if bbox:
                width = bbox[2] - bbox[0] + base_padding
                max_width = max(max_width, width)
            self.canvas.delete(temp_text)
        
        # Check method widths
        for method in self.methods:
            method_text = self.format_member(method, is_method=True)
            temp_text = self.canvas.create_text(0, 0, text=method_text, font=temp_font_content)
            bbox = self.canvas.bbox(temp_text)
            if bbox:
                width = bbox[2] - bbox[0] + base_padding
                max_width = max(max_width, width)
            self.canvas.delete(temp_text)
        
        # Check note widths
        for note in self.notes:
            note_text = f"📝 {note}"
            temp_text = self.canvas.create_text(0, 0, text=note_text, font=temp_font_small)
            bbox = self.canvas.bbox(temp_text)
            if bbox:
                width = bbox[2] - bbox[0] + base_padding
                max_width = max(max_width, width)
            self.canvas.delete(temp_text)
        
        # Update width to fit content (with max limit) - then scale by zoom
        base_width = min(max_width, 500)  # Increased max width to prevent text overflow
        self.width = int(base_width * zoom_level)
        
        # Calculate height based on content with minimum height for empty classes
        content_lines = 2  # title + separator
        if self.stereotype:
            content_lines += 1
        if self.annotations:
            content_lines += len(self.annotations)
        content_lines += len(self.attributes) + len(self.methods)
        if self.notes:
            content_lines += len(self.notes) + 1  # notes + separator
        
        # Calculate base height (not scaled by zoom initially)
        base_line_height = 20
        base_padding = 30
        base_calculated_height = content_lines * base_line_height + base_padding
        
        # Ensure minimum height for empty classes
        if len(self.attributes) == 0 and len(self.methods) == 0:
            # Empty class - ensure minimum clickable height
            base_height = max(80, base_calculated_height)
        else:
            base_height = max(100, base_calculated_height)
        
        # Now scale by zoom
        self.height = int(base_height * zoom_level)
        
        # Calculate scaled font sizes for rendering
        font_name_size = max(1, int(base_font_name_size * zoom_level))
        font_content_size = max(1, int(base_font_content_size * zoom_level))
        font_small_size = max(1, int(base_font_small_size * zoom_level))
        
        # Main rectangle
        fill_color = "lightblue"
        if "interface" in self.stereotype.lower() or "interface" in " ".join(self.annotations).lower():
            fill_color = "lightgreen"
        elif "abstract" in self.stereotype.lower() or "abstract" in " ".join(self.annotations).lower():
            fill_color = "lightyellow"
        
        border_width = max(1, int(2 * zoom_level))
        
        self.rect = self.canvas.create_rectangle(
            self.x, self.y, self.x + self.width, self.y + self.height,
            fill=fill_color, outline="black", width=border_width
        )
        
        y_offset = int(15 * zoom_level)  # Start with scaled offset
        
        # Store all visual elements for proper movement
        self.visual_elements = [self.rect]
        
        # Stereotype
        if self.stereotype:
            self.stereotype_text = self.canvas.create_text(
                self.x + self.width/2, self.y + y_offset,
                text=f"<<{self.stereotype}>>", font=("Arial", font_content_size, "italic"),
                fill="gray"
            )
            self.visual_elements.append(self.stereotype_text)
            y_offset += int(18 * zoom_level)
        
        # Annotations
        self.annotation_texts = []
        for annotation in self.annotations:
            annotation_text = self.canvas.create_text(
                self.x + self.width/2, self.y + y_offset,
                text=f"@{annotation}", font=("Arial", font_small_size, "italic"),
                fill="blue"
            )
            self.annotation_texts.append(annotation_text)
            self.visual_elements.append(annotation_text)
            y_offset += int(16 * zoom_level)
        
        # Class name
        name_font = ("Arial", font_name_size, "bold")
        if "abstract" in self.stereotype.lower() or "abstract" in " ".join(self.annotations).lower():
            name_font = ("Arial", font_name_size, "bold italic")
        
        self.name_text = self.canvas.create_text(
            self.x + self.width/2, self.y + y_offset,
            text=self.name, font=name_font
        )
        self.visual_elements.append(self.name_text)
        y_offset += int(20 * zoom_level)
        
        # Separator line
        self.sep_line = self.canvas.create_line(
            self.x, self.y + y_offset, self.x + self.width, self.y + y_offset,
            fill="black", width=max(1, int(1 * zoom_level))
        )
        self.visual_elements.append(self.sep_line)
        y_offset += int(10 * zoom_level)
        
        # Store the header height for content positioning
        self.header_height = y_offset
        
        # Attributes and methods
        self.update_content_with_zoom(zoom_level)
        
        # Bind events to main elements
        for element in [self.rect, self.name_text]:
            self.canvas.tag_bind(element, "<Button-1>", self.on_click)
            self.canvas.tag_bind(element, "<B1-Motion>", self.on_drag)
            self.canvas.tag_bind(element, "<ButtonRelease-1>", self.on_release)
            self.canvas.tag_bind(element, "<Double-Button-1>", self.on_double_click)
        
    def update_content(self):
        """Update content with default zoom level"""
        zoom_level = 1.0
        if self.tool and hasattr(self.tool, 'zoom_level'):
            zoom_level = self.tool.zoom_level
        self.update_content_with_zoom(zoom_level)
    
    def update_content_with_zoom(self, zoom_level):
        """Update content with specified zoom level"""
        # Clear existing content text
        for item in self.canvas.find_withtag("content_" + str(id(self))):
            self.canvas.delete(item)
        
        # Scale font sizes based on zoom level
        font_content_size = max(1, int(10 * zoom_level))
        font_small_size = max(1, int(9 * zoom_level))
            
        # Use stored header height if available, otherwise calculate
        if hasattr(self, 'header_height'):
            y_offset = self.header_height
        else:
            # Fallback calculation
            y_offset = int(15 * zoom_level)  # Base offset
            y_offset += int(20 * zoom_level)  # Class name
            y_offset += int(10 * zoom_level)  # Separator
            if self.stereotype:
                y_offset += int(18 * zoom_level)
            if self.annotations:
                y_offset += len(self.annotations) * int(16 * zoom_level)
        
        # For empty classes, add some visual indication
        if len(self.attributes) == 0 and len(self.methods) == 0 and len(self.notes) == 0:
            # Add empty class indicator
            empty_text = self.canvas.create_text(
                self.x + self.width/2, self.y + y_offset + int(10 * zoom_level),
                text="(empty)", font=("Arial", font_small_size, "italic"),
                fill="gray", tags="content_" + str(id(self))
            )
            # Bind events to empty text
            self.canvas.tag_bind(empty_text, "<Button-1>", self.on_click)
            self.canvas.tag_bind(empty_text, "<B1-Motion>", self.on_drag)
            self.canvas.tag_bind(empty_text, "<ButtonRelease-1>", self.on_release)
            self.canvas.tag_bind(empty_text, "<Double-Button-1>", self.on_double_click)
            return
        
        # Calculate available width for text (with padding)
        text_padding = int(10 * zoom_level)
        available_width = self.width - (2 * text_padding)
        
        # Add attributes
        for attr in self.attributes:
            # Parse attribute for visibility and type
            attr_text = self.format_member(attr, is_method=False)
            
            text_item = self.canvas.create_text(
                self.x + text_padding, self.y + y_offset,
                text=attr_text, font=("Arial", font_content_size),
                anchor="w", tags="content_" + str(id(self)),
                width=available_width  # Constrain text to box width
            )
            # Bind events to content text
            self.canvas.tag_bind(text_item, "<Button-1>", self.on_click)
            self.canvas.tag_bind(text_item, "<B1-Motion>", self.on_drag)
            self.canvas.tag_bind(text_item, "<ButtonRelease-1>", self.on_release)
            self.canvas.tag_bind(text_item, "<Double-Button-1>", self.on_double_click)
            
            # Check if text wrapped to multiple lines
            bbox = self.canvas.bbox(text_item)
            if bbox:
                text_height = bbox[3] - bbox[1]
                y_offset += max(int(18 * zoom_level), text_height + 2)
            else:
                y_offset += int(18 * zoom_level)
            
        # Separator for methods
        if self.attributes and self.methods:
            sep = self.canvas.create_line(
                self.x, self.y + y_offset, self.x + self.width, self.y + y_offset,
                fill="gray", width=max(1, int(1 * zoom_level)), tags="content_" + str(id(self))
            )
            y_offset += int(10 * zoom_level)
            
        # Add methods
        for method in self.methods:
            # Parse method for visibility, parameters, and return type
            method_text = self.format_member(method, is_method=True)
            
            font_style = ("Arial", font_content_size)
            
            # Check if method is abstract (italic)
            if method.startswith("*") or "abstract" in method.lower():
                font_style = ("Arial", font_content_size, "italic")
                
            text_item = self.canvas.create_text(
                self.x + text_padding, self.y + y_offset,
                text=method_text, font=font_style,
                anchor="w", tags="content_" + str(id(self)),
                width=available_width  # Constrain text to box width
            )
            # Bind events to content text
            self.canvas.tag_bind(text_item, "<Button-1>", self.on_click)
            self.canvas.tag_bind(text_item, "<B1-Motion>", self.on_drag)
            self.canvas.tag_bind(text_item, "<ButtonRelease-1>", self.on_release)
            self.canvas.tag_bind(text_item, "<Double-Button-1>", self.on_double_click)
            
            # Check if text wrapped to multiple lines
            bbox = self.canvas.bbox(text_item)
            if bbox:
                text_height = bbox[3] - bbox[1]
                y_offset += max(int(18 * zoom_level), text_height + 2)
            else:
                y_offset += int(18 * zoom_level)
            
        # Add notes if any
        if self.notes:
            # Separator for notes
            sep = self.canvas.create_line(
                self.x, self.y + y_offset, self.x + self.width, self.y + y_offset,
                fill="orange", width=max(1, int(1 * zoom_level)), tags="content_" + str(id(self))
            )
            y_offset += int(10 * zoom_level)
            
            for note in self.notes:
                note_text = f"📝 {note}"
                
                text_item = self.canvas.create_text(
                    self.x + text_padding, self.y + y_offset,
                    text=note_text, font=("Arial", font_small_size, "italic"),
                    anchor="w", tags="content_" + str(id(self)),
                    fill="darkorange", width=available_width
                )
                
                # Check if text wrapped to multiple lines
                bbox = self.canvas.bbox(text_item)
                if bbox:
                    text_height = bbox[3] - bbox[1]
                    y_offset += max(int(16 * zoom_level), text_height + 2)
                else:
                    y_offset += int(16 * zoom_level)
        
        # Update class height if content expanded beyond current height
        content_bottom = y_offset + int(10 * zoom_level)  # Add bottom padding
        if content_bottom > self.height:
            self.height = content_bottom
            # Update rectangle height
            self.canvas.coords(self.rect, self.x, self.y, self.x + self.width, self.y + self.height)
    
    def format_member(self, member, is_method=False):
        """Format attribute or method with proper visibility symbols and syntax"""
        # Handle different visibility formats
        if member.startswith(('+', '-', '#', '~')):
            return member  # Already formatted
        
        # Parse for visibility keywords
        visibility_map = {
            'public': '+',
            'private': '-',
            'protected': '#',
            'package': '~',
            'internal': '~'
        }
        
        for vis_word, symbol in visibility_map.items():
            if member.lower().startswith(vis_word + ' '):
                member = symbol + member[len(vis_word) + 1:]
                break
        else:
            # Default to public if no visibility specified
            if not member.startswith(('+', '-', '#', '~')):
                member = '+' + member
        
        # Add parentheses for methods if not present
        if is_method and not member.endswith(')'):
            if '(' not in member:
                member += '()'
        
        return member
            
    def on_click(self, event):
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y
        
        # Signal to tool that we're dragging a class, not panning
        if self.tool:
            self.tool.is_panning = False
            
            # Deselect all other classes first
            for cls in self.tool.classes:
                if cls != self:
                    cls.deselect()
            
            # Deselect all relationships when clicking on a class
            for rel in self.tool.relationships:
                rel.deselect()
        
        self.select()
        
    def on_drag(self, event):
        dx = event.x - self.drag_data["x"]
        dy = event.y - self.drag_data["y"]
        
        # Mark that dragging occurred
        if dx != 0 or dy != 0:
            self._was_dragged = True
        
        self.move(dx, dy)
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y
        
        # Update relationships when this class moves
        if self.tool:
            self.tool.update_relationships()
        
    def on_release(self, event):
        # Mark as changed when user finishes dragging (only if actually moved)
        if self.tool:
            # Check if the class was actually dragged (not just clicked)
            if hasattr(self, '_was_dragged') and self._was_dragged:
                self.tool.mark_as_changed()
                
                # Auto-save positions when class is moved (if we have a current file)
                if self.tool.current_file and os.path.exists(self.tool.current_file):
                    try:
                        self.tool.save_positions(self.tool.current_file)
                    except Exception as e:
                        print(f"Warning: Could not auto-save positions: {e}")
                
                self._was_dragged = False
        
    def on_double_click(self, event):
        self.edit_class()
        # Stop event propagation to prevent canvas double-click
        return "break"
        
    def update_selection_indicators(self):
        """Update selection indicator positions"""
        if self.selected and hasattr(self, 'selection_indicators'):
            # Remove old indicators
            for indicator in self.selection_indicators:
                self.canvas.delete(indicator)
            
            zoom_level = 1.0
            if self.tool and hasattr(self.tool, 'zoom_level'):
                zoom_level = self.tool.zoom_level
            
            # Create new indicators at current position (scaled)
            indicator_size = max(4, int(6 * zoom_level))
            offset = int(3 * zoom_level)
            
            self.selection_indicators = []
            corners = [
                (self.x - offset, self.y - offset),  # top-left
                (self.x + self.width - offset, self.y - offset),  # top-right
                (self.x - offset, self.y + self.height - offset),  # bottom-left
                (self.x + self.width - offset, self.y + self.height - offset)  # bottom-right
            ]
            
            for corner_x, corner_y in corners:
                indicator = self.canvas.create_rectangle(
                    corner_x, corner_y, corner_x + indicator_size, corner_y + indicator_size,
                    fill="red", outline="darkred", width=max(1, int(1 * zoom_level))
                )
                self.selection_indicators.append(indicator)
                # Keep indicators on top
                self.canvas.tag_raise(indicator)
    
    def move(self, dx, dy):
        self.x += dx
        self.y += dy
        
        # Move all visual elements
        if hasattr(self, 'visual_elements'):
            for element in self.visual_elements:
                self.canvas.move(element, dx, dy)
        
        # Move content elements
        for item in self.canvas.find_withtag("content_" + str(id(self))):
            self.canvas.move(item, dx, dy)
        
        # Update selection indicators if selected
        if self.selected:
            self.update_selection_indicators()
        
        # Update scroll region when class moves
        if self.tool:
            self.tool.update_scroll_region()
            
    def select(self):
        self.selected = True
        zoom_level = 1.0
        if self.tool and hasattr(self.tool, 'zoom_level'):
            zoom_level = self.tool.zoom_level
        
        border_width = max(1, int(3 * zoom_level))
        self.canvas.itemconfig(self.rect, outline="red", width=border_width)
        
        # Bring selected class above other classes (but keep relationships below)
        # We do this by raising it relative to other class elements
        if hasattr(self, 'visual_elements'):
            for element in self.visual_elements:
                self.canvas.tag_raise(element)
        
        # Bring content to front
        for item in self.canvas.find_withtag("content_" + str(id(self))):
            self.canvas.tag_raise(item)
        
        # Remove old selection indicators if they exist
        if hasattr(self, 'selection_indicators'):
            for indicator in self.selection_indicators:
                self.canvas.delete(indicator)
        
        # Add selection indicator - corner squares (scaled)
        indicator_size = max(4, int(6 * zoom_level))
        offset = int(3 * zoom_level)
        
        self.selection_indicators = []
        corners = [
            (self.x - offset, self.y - offset),  # top-left
            (self.x + self.width - offset, self.y - offset),  # top-right
            (self.x - offset, self.y + self.height - offset),  # bottom-left
            (self.x + self.width - offset, self.y + self.height - offset)  # bottom-right
        ]
        
        for corner_x, corner_y in corners:
            indicator = self.canvas.create_rectangle(
                corner_x, corner_y, corner_x + indicator_size, corner_y + indicator_size,
                fill="red", outline="darkred", width=max(1, int(1 * zoom_level))
            )
            self.selection_indicators.append(indicator)
            # Bring indicators above the class
            self.canvas.tag_raise(indicator)
        
    def deselect(self):
        self.selected = False
        zoom_level = 1.0
        if self.tool and hasattr(self.tool, 'zoom_level'):
            zoom_level = self.tool.zoom_level
        
        border_width = max(1, int(2 * zoom_level))
        self.canvas.itemconfig(self.rect, outline="black", width=border_width)
        
        # Remove selection indicators
        if hasattr(self, 'selection_indicators'):
            for indicator in self.selection_indicators:
                self.canvas.delete(indicator)
            self.selection_indicators = []
        
    def edit_class(self):
        dialog = ClassEditDialog(self.canvas.master, self)
        
    def delete(self):
        # Remove selection indicators first
        if hasattr(self, 'selection_indicators'):
            for indicator in self.selection_indicators:
                self.canvas.delete(indicator)
        
        # Remove all visual elements
        if hasattr(self, 'visual_elements'):
            for element in self.visual_elements:
                self.canvas.delete(element)
        
        # Remove content elements
        for item in self.canvas.find_withtag("content_" + str(id(self))):
            self.canvas.delete(item)
            
    def get_center(self):
        return (self.x + self.width/2, self.y + self.height/2)
        
class Relationship:
    def __init__(self, canvas, from_class, to_class, rel_type="association", tool=None):
        self.canvas = canvas
        self.tool = tool
        self.from_class = from_class
        self.to_class = to_class
        self.rel_type = rel_type  # association, inheritance, composition, aggregation, dependency, realization
        self.label = ""  # Relationship label
        self.from_multiplicity = ""  # e.g., "1", "0..*", "1..*"
        self.to_multiplicity = ""
        self.line = None
        self.arrow = None
        self.selected = False
        self.create_visual()
        
    def calculate_bezier_curve(self, from_point, to_point, num_points=20):
        """Calculate points for a smooth bezier curve between two points"""
        # Calculate control points for the bezier curve
        dx = to_point[0] - from_point[0]
        dy = to_point[1] - from_point[1]
        
        # Create control points offset perpendicular to the line
        # This creates a gentle curve
        mid_x = (from_point[0] + to_point[0]) / 2
        mid_y = (from_point[1] + to_point[1]) / 2
        
        # Calculate perpendicular offset
        length = math.sqrt(dx*dx + dy*dy)
        if length == 0:
            return [from_point[0], from_point[1], to_point[0], to_point[1]]
        
        # Offset amount based on distance (creates more curve for longer lines)
        offset = min(length * 0.2, 50)
        
        # Control points for cubic bezier
        ctrl1_x = from_point[0] + dx * 0.25
        ctrl1_y = from_point[1] + dy * 0.25 - offset
        
        ctrl2_x = from_point[0] + dx * 0.75
        ctrl2_y = from_point[1] + dy * 0.75 - offset
        
        # Generate points along the bezier curve
        points = []
        for i in range(num_points + 1):
            t = i / num_points
            # Cubic bezier formula
            x = (1-t)**3 * from_point[0] + 3*(1-t)**2*t * ctrl1_x + 3*(1-t)*t**2 * ctrl2_x + t**3 * to_point[0]
            y = (1-t)**3 * from_point[1] + 3*(1-t)**2*t * ctrl1_y + 3*(1-t)*t**2 * ctrl2_y + t**3 * to_point[1]
            points.extend([x, y])
        
        return points
    
    def get_connection_points(self):
        """Calculate the best connection points on the edges of the classes"""
        from_center = self.from_class.get_center()
        to_center = self.to_class.get_center()
        
        # Calculate direction vector
        dx = to_center[0] - from_center[0]
        dy = to_center[1] - from_center[1]
        
        # Normalize direction
        length = math.sqrt(dx*dx + dy*dy)
        if length == 0:
            return from_center, to_center
            
        dx_norm = dx / length
        dy_norm = dy / length
        
        # Calculate intersection points with class rectangles
        # For from_class
        from_rect = {
            'left': self.from_class.x,
            'right': self.from_class.x + self.from_class.width,
            'top': self.from_class.y,
            'bottom': self.from_class.y + self.from_class.height
        }
        
        # For to_class
        to_rect = {
            'left': self.to_class.x,
            'right': self.to_class.x + self.to_class.width,
            'top': self.to_class.y,
            'bottom': self.to_class.y + self.to_class.height
        }
        
        # Find intersection point on from_class edge
        from_point = self.get_rect_intersection(from_center, (dx_norm, dy_norm), from_rect)
        
        # Find intersection point on to_class edge (reverse direction)
        to_point = self.get_rect_intersection(to_center, (-dx_norm, -dy_norm), to_rect)
        
        return from_point, to_point
    
    def get_rect_intersection(self, center, direction, rect):
        """Find intersection point of a ray from center in direction with rectangle"""
        cx, cy = center
        dx, dy = direction
        
        # Calculate intersection with each edge
        intersections = []
        
        # Right edge
        if dx > 0:
            t = (rect['right'] - cx) / dx
            y = cy + t * dy
            if rect['top'] <= y <= rect['bottom']:
                intersections.append((rect['right'], y))
        
        # Left edge
        if dx < 0:
            t = (rect['left'] - cx) / dx
            y = cy + t * dy
            if rect['top'] <= y <= rect['bottom']:
                intersections.append((rect['left'], y))
        
        # Bottom edge
        if dy > 0:
            t = (rect['bottom'] - cy) / dy
            x = cx + t * dx
            if rect['left'] <= x <= rect['right']:
                intersections.append((x, rect['bottom']))
        
        # Top edge
        if dy < 0:
            t = (rect['top'] - cy) / dy
            x = cx + t * dx
            if rect['left'] <= x <= rect['right']:
                intersections.append((x, rect['top']))
        
        # Return the closest intersection point
        if intersections:
            # Find the intersection closest to the center
            min_dist = float('inf')
            best_point = center
            for point in intersections:
                dist = math.sqrt((point[0] - cx)**2 + (point[1] - cy)**2)
                if dist < min_dist:
                    min_dist = dist
                    best_point = point
            return best_point
        
        return center
        
    def create_visual(self):
        from_point, to_point = self.get_connection_points()
        
        # Create line with selection capability
        line_color = "red" if self.selected else "black"
        line_width = max(1, int((3 if self.selected else 2) * (self.tool.zoom_level if self.tool and hasattr(self.tool, 'zoom_level') else 1.0)))
        
        # Create curved line using bezier curve
        curve_points = self.calculate_bezier_curve(from_point, to_point)
        
        # Different line styles for different relationship types
        if self.rel_type == "dependency":
            # Dashed line for dependency
            self.line = self.canvas.create_line(
                *curve_points,
                width=line_width, fill=line_color, dash=(5, 5), smooth=True
            )
        elif self.rel_type == "realization":
            # Dashed line for realization
            self.line = self.canvas.create_line(
                *curve_points,
                width=line_width, fill=line_color, dash=(10, 5), smooth=True
            )
        else:
            # Solid curved line for other types
            self.line = self.canvas.create_line(
                *curve_points,
                width=line_width, fill=line_color, smooth=True
            )
        
        # Keep line behind classes
        self.canvas.tag_lower(self.line)
        
        # Bind click events to line
        self.canvas.tag_bind(self.line, "<Button-1>", self.on_click)
        self.canvas.tag_bind(self.line, "<Double-Button-1>", self.on_double_click)
        
        # Create arrow based on relationship type
        if self.rel_type == "inheritance":
            self.create_inheritance_arrow(to_point, from_point)
        elif self.rel_type == "composition":
            self.create_composition_arrow(from_point, to_point)
        elif self.rel_type == "aggregation":
            self.create_aggregation_arrow(from_point, to_point)
        elif self.rel_type == "dependency":
            self.create_dependency_arrow(to_point, from_point)
        elif self.rel_type == "realization":
            self.create_realization_arrow(to_point, from_point)
        
        # Keep labels behind classes but visible
        if self.label or self.from_multiplicity or self.to_multiplicity:
            zoom_level = 1.0
            if self.tool and hasattr(self.tool, 'zoom_level'):
                zoom_level = self.tool.zoom_level
            
            label_font_size = max(1, int(9 * zoom_level))
            mult_font_size = max(1, int(8 * zoom_level))
            
            # Calculate midpoint for label
            mid_x = (from_point[0] + to_point[0]) / 2
            mid_y = (from_point[1] + to_point[1]) / 2
            
            # Relationship label
            if self.label:
                self.label_text = self.canvas.create_text(
                    mid_x, mid_y - int(10 * zoom_level),
                    text=self.label, font=("Arial", label_font_size),
                    fill="blue", anchor="center"
                )
                # Keep label behind classes
                self.canvas.tag_lower(self.label_text)
                self.canvas.tag_bind(self.label_text, "<Button-1>", self.on_click)
                self.canvas.tag_bind(self.label_text, "<Double-Button-1>", self.on_double_click)
            
            # From multiplicity
            if self.from_multiplicity:
                self.from_mult_text = self.canvas.create_text(
                    from_point[0] + int(15 * zoom_level), from_point[1] - int(10 * zoom_level),
                    text=self.from_multiplicity, font=("Arial", mult_font_size),
                    fill="darkgreen", anchor="center"
                )
                # Keep multiplicity behind classes
                self.canvas.tag_lower(self.from_mult_text)
            
            # To multiplicity
            if self.to_multiplicity:
                self.to_mult_text = self.canvas.create_text(
                    to_point[0] - int(15 * zoom_level), to_point[1] - int(10 * zoom_level),
                    text=self.to_multiplicity, font=("Arial", mult_font_size),
                    fill="darkgreen", anchor="center"
                )
                # Keep multiplicity behind classes
                self.canvas.tag_lower(self.to_mult_text)
    
    def create_dependency_arrow(self, to_point, from_point):
        # Open arrow for dependency
        angle = math.atan2(
            to_point[1] - from_point[1],
            to_point[0] - from_point[0]
        )
        
        zoom_level = 1.0
        if self.tool and hasattr(self.tool, 'zoom_level'):
            zoom_level = self.tool.zoom_level
        
        arrow_size = max(8, int(12 * zoom_level))
        x1 = to_point[0] - arrow_size * math.cos(angle - 0.4)
        y1 = to_point[1] - arrow_size * math.sin(angle - 0.4)
        x2 = to_point[0] - arrow_size * math.cos(angle + 0.4)
        y2 = to_point[1] - arrow_size * math.sin(angle + 0.4)
        
        arrow_color = "red" if self.selected else "black"
        arrow_width = max(1, int(2 * zoom_level))
        
        # Create two lines for open arrow
        self.arrow = []
        line1 = self.canvas.create_line(
            to_point[0], to_point[1], x1, y1,
            width=arrow_width, fill=arrow_color
        )
        line2 = self.canvas.create_line(
            to_point[0], to_point[1], x2, y2,
            width=arrow_width, fill=arrow_color
        )
        self.arrow = [line1, line2]
        
        # Keep arrows behind classes
        for arrow_part in self.arrow:
            self.canvas.tag_lower(arrow_part)
            # Bind events to arrow parts
            self.canvas.tag_bind(arrow_part, "<Button-1>", self.on_click)
            self.canvas.tag_bind(arrow_part, "<Double-Button-1>", self.on_double_click)
    
    def create_realization_arrow(self, to_point, from_point):
        # Triangle arrow for realization (same as inheritance but with dashed line)
        self.create_inheritance_arrow(to_point, from_point)
            
    def on_click(self, event):
        """Handle line selection"""
        if self.tool:
            # Deselect all other relationships
            for rel in self.tool.relationships:
                if rel != self:
                    rel.deselect()
            # Deselect all classes
            for cls in self.tool.classes:
                cls.deselect()
            
            self.select()
        
        # Stop event propagation to prevent canvas click
        return "break"
            
    def on_double_click(self, event):
        """Handle relationship type change"""
        self.change_type()
        return "break"
        
    def select(self):
        """Select this relationship"""
        self.selected = True
        self.update_position()  # Redraw with selection styling
        
        # Update status bar
        if self.tool:
            self.tool.update_status(f"Selected {self.rel_type} relationship: {self.from_class.name} → {self.to_class.name} (Double-click to change type)")
        
    def deselect(self):
        """Deselect this relationship"""
        self.selected = False
        self.update_position()  # Redraw without selection styling
        
        # Clear status bar
        if self.tool:
            self.tool.update_status("Ready")
        
    def change_type(self):
        """Cycle through relationship types"""
        types = ["association", "inheritance", "composition", "aggregation", "dependency", "realization"]
        current_index = types.index(self.rel_type)
        next_index = (current_index + 1) % len(types)
        self.rel_type = types[next_index]
        self.update_position()
        
        # Update the toolbar dropdown if tool is available
        if self.tool and hasattr(self.tool, 'rel_type_var'):
            self.tool.rel_type_var.set(self.rel_type)
            
        # Update status bar
        if self.tool:
            self.tool.update_status(f"Changed to {self.rel_type} relationship: {self.from_class.name} → {self.to_class.name}")
            
    def create_inheritance_arrow(self, to_point, from_point):
        # Triangle arrow for inheritance
        angle = math.atan2(
            to_point[1] - from_point[1],
            to_point[0] - from_point[0]
        )
        
        zoom_level = 1.0
        if self.tool and hasattr(self.tool, 'zoom_level'):
            zoom_level = self.tool.zoom_level
        
        arrow_size = max(8, int(15 * zoom_level))
        x1 = to_point[0] - arrow_size * math.cos(angle - 0.5)
        y1 = to_point[1] - arrow_size * math.sin(angle - 0.5)
        x2 = to_point[0] - arrow_size * math.cos(angle + 0.5)
        y2 = to_point[1] - arrow_size * math.sin(angle + 0.5)
        
        arrow_color = "red" if self.selected else "black"
        arrow_width = max(1, int(2 * zoom_level))
        
        self.arrow = self.canvas.create_polygon(
            to_point[0], to_point[1], x1, y1, x2, y2,
            fill="white", outline=arrow_color, width=arrow_width
        )
        
        # Keep arrow behind classes
        self.canvas.tag_lower(self.arrow)
        
        # Bind events to arrow too
        self.canvas.tag_bind(self.arrow, "<Button-1>", self.on_click)
        self.canvas.tag_bind(self.arrow, "<Double-Button-1>", self.on_double_click)
        
    def create_composition_arrow(self, from_point, to_point):
        # Diamond for composition
        angle = math.atan2(
            to_point[1] - from_point[1],
            to_point[0] - from_point[0]
        )
        
        zoom_level = 1.0
        if self.tool and hasattr(self.tool, 'zoom_level'):
            zoom_level = self.tool.zoom_level
        
        diamond_size = max(6, int(10 * zoom_level))
        x1 = from_point[0] + diamond_size * math.cos(angle)
        y1 = from_point[1] + diamond_size * math.sin(angle)
        x2 = from_point[0] + diamond_size * math.cos(angle + math.pi/2)
        y2 = from_point[1] + diamond_size * math.sin(angle + math.pi/2)
        x3 = from_point[0] - diamond_size * math.cos(angle)
        y3 = from_point[1] - diamond_size * math.sin(angle)
        x4 = from_point[0] + diamond_size * math.cos(angle - math.pi/2)
        y4 = from_point[1] + diamond_size * math.sin(angle - math.pi/2)
        
        arrow_color = "red" if self.selected else "black"
        
        self.arrow = self.canvas.create_polygon(
            x1, y1, x2, y2, x3, y3, x4, y4,
            fill=arrow_color, outline=arrow_color
        )
        
        # Keep arrow behind classes
        self.canvas.tag_lower(self.arrow)
        
        # Bind events to arrow too
        self.canvas.tag_bind(self.arrow, "<Button-1>", self.on_click)
        self.canvas.tag_bind(self.arrow, "<Double-Button-1>", self.on_double_click)
        
    def create_aggregation_arrow(self, from_point, to_point):
        # Empty diamond for aggregation
        angle = math.atan2(
            to_point[1] - from_point[1],
            to_point[0] - from_point[0]
        )
        
        zoom_level = 1.0
        if self.tool and hasattr(self.tool, 'zoom_level'):
            zoom_level = self.tool.zoom_level
        
        diamond_size = max(6, int(10 * zoom_level))
        x1 = from_point[0] + diamond_size * math.cos(angle)
        y1 = from_point[1] + diamond_size * math.sin(angle)
        x2 = from_point[0] + diamond_size * math.cos(angle + math.pi/2)
        y2 = from_point[1] + diamond_size * math.sin(angle + math.pi/2)
        x3 = from_point[0] - diamond_size * math.cos(angle)
        y3 = from_point[1] - diamond_size * math.sin(angle)
        x4 = from_point[0] + diamond_size * math.cos(angle - math.pi/2)
        y4 = from_point[1] + diamond_size * math.sin(angle - math.pi/2)
        
        arrow_color = "red" if self.selected else "black"
        arrow_width = max(1, int(2 * zoom_level))
        
        self.arrow = self.canvas.create_polygon(
            x1, y1, x2, y2, x3, y3, x4, y4,
            fill="white", outline=arrow_color, width=arrow_width
        )
        
        # Keep arrow behind classes
        self.canvas.tag_lower(self.arrow)
        
        # Bind events to arrow too
        self.canvas.tag_bind(self.arrow, "<Button-1>", self.on_click)
        self.canvas.tag_bind(self.arrow, "<Double-Button-1>", self.on_double_click)
        
    def update_position(self):
        if self.line:
            self.canvas.delete(self.line)
        if self.arrow:
            if isinstance(self.arrow, list):
                for arrow_part in self.arrow:
                    self.canvas.delete(arrow_part)
            else:
                self.canvas.delete(self.arrow)
        
        # Delete labels if they exist
        if hasattr(self, 'label_text'):
            self.canvas.delete(self.label_text)
        if hasattr(self, 'from_mult_text'):
            self.canvas.delete(self.from_mult_text)
        if hasattr(self, 'to_mult_text'):
            self.canvas.delete(self.to_mult_text)
            
        self.create_visual()
        
    def delete(self):
        if self.line:
            self.canvas.delete(self.line)
        if self.arrow:
            if isinstance(self.arrow, list):
                for arrow_part in self.arrow:
                    self.canvas.delete(arrow_part)
            else:
                self.canvas.delete(self.arrow)
        
        # Delete labels if they exist
        if hasattr(self, 'label_text'):
            self.canvas.delete(self.label_text)
        if hasattr(self, 'from_mult_text'):
            self.canvas.delete(self.from_mult_text)
        if hasattr(self, 'to_mult_text'):
            self.canvas.delete(self.to_mult_text)

class ClassEditDialog:
    def __init__(self, parent, class_box):
        self.class_box = class_box
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Edit Class")
        self.dialog.geometry("500x700")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.create_widgets()
        
    def create_widgets(self):
        # Create notebook for tabs
        notebook = ttk.Notebook(self.dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Basic tab
        basic_frame = ttk.Frame(notebook)
        notebook.add(basic_frame, text="Basic")
        
        # Advanced tab
        advanced_frame = ttk.Frame(notebook)
        notebook.add(advanced_frame, text="Advanced")
        
        # Notes tab
        notes_frame = ttk.Frame(notebook)
        notebook.add(notes_frame, text="Notes")
        
        self.create_basic_tab(basic_frame)
        self.create_advanced_tab(advanced_frame)
        self.create_notes_tab(notes_frame)
        
        # Buttons
        btn_frame = tk.Frame(self.dialog)
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="OK", command=self.ok_clicked).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Cancel", command=self.cancel_clicked).pack(side=tk.LEFT, padx=10)
        
    def create_basic_tab(self, parent):
        # Class name
        tk.Label(parent, text="Class Name:").pack(pady=5)
        self.name_entry = tk.Entry(parent, width=40)
        self.name_entry.insert(0, self.class_box.name)
        self.name_entry.pack(pady=5)
        
        # Attributes
        tk.Label(parent, text="Attributes:").pack(pady=(20, 5))
        
        attr_frame = tk.Frame(parent)
        attr_frame.pack(fill=tk.BOTH, expand=True, padx=10)
        
        self.attr_listbox = tk.Listbox(attr_frame, height=8)
        self.attr_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        attr_scroll = tk.Scrollbar(attr_frame, orient=tk.VERTICAL)
        attr_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.attr_listbox.config(yscrollcommand=attr_scroll.set)
        attr_scroll.config(command=self.attr_listbox.yview)
        
        for attr in self.class_box.attributes:
            self.attr_listbox.insert(tk.END, attr)
            
        attr_btn_frame = tk.Frame(parent)
        attr_btn_frame.pack(pady=5)
        
        tk.Button(attr_btn_frame, text="Add Attribute", 
                 command=self.add_attribute).pack(side=tk.LEFT, padx=5)
        tk.Button(attr_btn_frame, text="Remove Attribute", 
                 command=self.remove_attribute).pack(side=tk.LEFT, padx=5)
        
        # Methods
        tk.Label(parent, text="Methods:").pack(pady=(20, 5))
        
        method_frame = tk.Frame(parent)
        method_frame.pack(fill=tk.BOTH, expand=True, padx=10)
        
        self.method_listbox = tk.Listbox(method_frame, height=8)
        self.method_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        method_scroll = tk.Scrollbar(method_frame, orient=tk.VERTICAL)
        method_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.method_listbox.config(yscrollcommand=method_scroll.set)
        method_scroll.config(command=self.method_listbox.yview)
        
        for method in self.class_box.methods:
            self.method_listbox.insert(tk.END, method)
            
        method_btn_frame = tk.Frame(parent)
        method_btn_frame.pack(pady=5)
        
        tk.Button(method_btn_frame, text="Add Method", 
                 command=self.add_method).pack(side=tk.LEFT, padx=5)
        tk.Button(method_btn_frame, text="Remove Method", 
                 command=self.remove_method).pack(side=tk.LEFT, padx=5)
    
    def create_advanced_tab(self, parent):
        # Stereotype
        tk.Label(parent, text="Stereotype (e.g., interface, abstract):").pack(pady=5)
        self.stereotype_entry = tk.Entry(parent, width=40)
        self.stereotype_entry.insert(0, self.class_box.stereotype)
        self.stereotype_entry.pack(pady=5)
        
        # Annotations
        tk.Label(parent, text="Annotations:").pack(pady=(20, 5))
        
        annotation_frame = tk.Frame(parent)
        annotation_frame.pack(fill=tk.BOTH, expand=True, padx=10)
        
        self.annotation_listbox = tk.Listbox(annotation_frame, height=6)
        self.annotation_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        annotation_scroll = tk.Scrollbar(annotation_frame, orient=tk.VERTICAL)
        annotation_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.annotation_listbox.config(yscrollcommand=annotation_scroll.set)
        annotation_scroll.config(command=self.annotation_listbox.yview)
        
        for annotation in self.class_box.annotations:
            self.annotation_listbox.insert(tk.END, annotation)
            
        annotation_btn_frame = tk.Frame(parent)
        annotation_btn_frame.pack(pady=5)
        
        tk.Button(annotation_btn_frame, text="Add Annotation", 
                 command=self.add_annotation).pack(side=tk.LEFT, padx=5)
        tk.Button(annotation_btn_frame, text="Remove Annotation", 
                 command=self.remove_annotation).pack(side=tk.LEFT, padx=5)
        
        # Visibility
        tk.Label(parent, text="Default Visibility:").pack(pady=(20, 5))
        self.visibility_var = tk.StringVar(value=self.class_box.visibility)
        visibility_frame = tk.Frame(parent)
        visibility_frame.pack(pady=5)
        
        for vis in ["public", "private", "protected", "package"]:
            tk.Radiobutton(visibility_frame, text=vis.capitalize(), 
                          variable=self.visibility_var, value=vis).pack(side=tk.LEFT, padx=10)
    
    def create_notes_tab(self, parent):
        tk.Label(parent, text="Class Notes:").pack(pady=5)
        
        notes_frame = tk.Frame(parent)
        notes_frame.pack(fill=tk.BOTH, expand=True, padx=10)
        
        self.notes_listbox = tk.Listbox(notes_frame, height=10)
        self.notes_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        notes_scroll = tk.Scrollbar(notes_frame, orient=tk.VERTICAL)
        notes_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.notes_listbox.config(yscrollcommand=notes_scroll.set)
        notes_scroll.config(command=self.notes_listbox.yview)
        
        for note in self.class_box.notes:
            self.notes_listbox.insert(tk.END, note)
            
        notes_btn_frame = tk.Frame(parent)
        notes_btn_frame.pack(pady=5)
        
        tk.Button(notes_btn_frame, text="Add Note", 
                 command=self.add_note).pack(side=tk.LEFT, padx=5)
        tk.Button(notes_btn_frame, text="Remove Note", 
                 command=self.remove_note).pack(side=tk.LEFT, padx=5)
        
        # Help text
        help_text = tk.Label(parent, 
                           text="Notes appear at the bottom of the class box and are included in Mermaid export",
                           font=("Arial", 9), fg="gray", wraplength=400)
        help_text.pack(pady=10)
        
    def add_attribute(self):
        attr = simpledialog.askstring("Add Attribute", 
                                     "Enter attribute (e.g., +name: String, -id: int):")
        if attr:
            self.attr_listbox.insert(tk.END, attr)
            
    def remove_attribute(self):
        selection = self.attr_listbox.curselection()
        if selection:
            self.attr_listbox.delete(selection[0])
            
    def add_method(self):
        method = simpledialog.askstring("Add Method", 
                                       "Enter method (e.g., +getName(): String, -setId(id: int)):")
        if method:
            self.method_listbox.insert(tk.END, method)
            
    def remove_method(self):
        selection = self.method_listbox.curselection()
        if selection:
            self.method_listbox.delete(selection[0])
    
    def add_annotation(self):
        annotation = simpledialog.askstring("Add Annotation", 
                                           "Enter annotation (e.g., Override, Deprecated):")
        if annotation:
            self.annotation_listbox.insert(tk.END, annotation)
            
    def remove_annotation(self):
        selection = self.annotation_listbox.curselection()
        if selection:
            self.annotation_listbox.delete(selection[0])
    
    def add_note(self):
        note = simpledialog.askstring("Add Note", 
                                     "Enter note text:")
        if note:
            self.notes_listbox.insert(tk.END, note)
            
    def remove_note(self):
        selection = self.notes_listbox.curselection()
        if selection:
            self.notes_listbox.delete(selection[0])
            
    def ok_clicked(self):
        # Update class box
        self.class_box.name = self.name_entry.get()
        self.class_box.stereotype = self.stereotype_entry.get()
        self.class_box.visibility = self.visibility_var.get()
        
        self.class_box.attributes = []
        for i in range(self.attr_listbox.size()):
            self.class_box.attributes.append(self.attr_listbox.get(i))
            
        self.class_box.methods = []
        for i in range(self.method_listbox.size()):
            self.class_box.methods.append(self.method_listbox.get(i))
            
        self.class_box.annotations = []
        for i in range(self.annotation_listbox.size()):
            self.class_box.annotations.append(self.annotation_listbox.get(i))
            
        self.class_box.notes = []
        for i in range(self.notes_listbox.size()):
            self.class_box.notes.append(self.notes_listbox.get(i))
            
        # Update visual
        self.class_box.canvas.delete(self.class_box.rect)
        self.class_box.canvas.delete(self.class_box.name_text)
        self.class_box.canvas.delete(self.class_box.sep_line)
        for item in self.class_box.canvas.find_withtag("content_" + str(id(self.class_box))):
            self.class_box.canvas.delete(item)
            
        self.class_box.create_visual()
        
        # Mark as changed
        if self.class_box.tool:
            self.class_box.tool.mark_as_changed()
        
        self.dialog.destroy()
        
    def cancel_clicked(self):
        self.dialog.destroy()

class MermaidDiagramTool:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Mermaid UML Class Diagram Tool")
        self.root.geometry("1200x800")
        
        self.classes = []
        self.relationships = []
        self.selected_class = None
        self.relationship_mode = False
        self.relationship_type = "association"
        self.relationship_start = None
        self.zoom_level = 1.0  # Track current zoom level
        self.pan_start_x = 0  # Track panning start position
        self.pan_start_y = 0
        self.is_panning = False  # Track if currently panning
        
        # Track changes and current file
        self.has_unsaved_changes = False
        self.current_file = None
        self.config_file = "mermaid_tool_config.txt"
        
        self.create_widgets()
        
        # Set up window close handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Load last used diagram
        self.load_last_diagram()
        
    def create_widgets(self):
        # Menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New", command=self.new_diagram)
        file_menu.add_command(label="Open Mermaid", command=self.open_mermaid)
        file_menu.add_command(label="Save Mermaid", command=self.save_mermaid)
        
        # Toolbar
        toolbar = tk.Frame(self.root, bg="lightgray", height=50)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        
        tk.Button(toolbar, text="Add Class", command=self.add_class).pack(side=tk.LEFT, padx=5, pady=5)
        tk.Button(toolbar, text="Delete Selected", command=self.delete_selected).pack(side=tk.LEFT, padx=5, pady=5)
        tk.Button(toolbar, text="Auto Layout", command=self.apply_hierarchical_layout, bg="lightgreen").pack(side=tk.LEFT, padx=5, pady=5)
        
        tk.Label(toolbar, text="Relationship:", bg="lightgray").pack(side=tk.LEFT, padx=(20, 5), pady=5)
        
        self.rel_type_var = tk.StringVar(value="association")
        rel_combo = ttk.Combobox(toolbar, textvariable=self.rel_type_var, 
                                values=["association", "inheritance", "composition", "aggregation", "dependency", "realization"],
                                state="readonly", width=15)
        rel_combo.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.rel_button = tk.Button(toolbar, text="Add Relationship", 
                                   command=self.toggle_relationship_mode)
        self.rel_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Zoom controls
        tk.Label(toolbar, text="Zoom:", bg="lightgray").pack(side=tk.LEFT, padx=(20, 5), pady=5)
        tk.Button(toolbar, text="-", command=self.zoom_out, width=2).pack(side=tk.LEFT, padx=2, pady=5)
        self.zoom_label = tk.Label(toolbar, text="100%", bg="lightgray", width=6)
        self.zoom_label.pack(side=tk.LEFT, padx=2, pady=5)
        tk.Button(toolbar, text="+", command=self.zoom_in, width=2).pack(side=tk.LEFT, padx=2, pady=5)
        tk.Button(toolbar, text="Reset", command=self.zoom_reset, width=5).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Canvas
        canvas_frame = tk.Frame(self.root)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(canvas_frame, bg="white")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbars
        v_scrollbar = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=v_scrollbar.set)
        
        h_scrollbar = tk.Scrollbar(self.root, orient=tk.HORIZONTAL, command=self.canvas.xview)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.configure(xscrollcommand=h_scrollbar.set)
        
        # Configure scroll region
        self.canvas.configure(scrollregion=(0, 0, 2000, 2000))
        self.update_scroll_region()
        
        # Bind canvas events
        self.canvas.bind("<Button-1>", self.canvas_click)
        self.canvas.bind("<B1-Motion>", self.canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.canvas_release)
        self.canvas.bind("<Button-3>", self.canvas_right_click)  # Right-click for class creation
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)  # Mouse wheel for zooming
        self.canvas.bind("<Motion>", self.canvas_motion)  # Track mouse movement for cursor changes
        
        # Status bar
        self.status_bar = tk.Label(self.root, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Bind keyboard events
        self.root.bind("<Key>", self.on_key_press)
        self.root.focus_set()  # Make sure root can receive key events
        
    def update_status(self, message):
        """Update status bar message"""
        if hasattr(self, 'status_bar'):
            self.status_bar.config(text=message)
    
    def update_relationships(self):
        """Update all relationship positions when classes move"""
        for rel in self.relationships:
            rel.update_position()
        # Update scroll region after relationships change
        self.update_scroll_region()
    
    def on_key_press(self, event):
        """Handle keyboard events"""
        if event.keysym == "Delete":
            self.delete_selected()
        elif event.keysym == "Escape":
            # Deselect all and cancel relationship mode
            for class_box in self.classes:
                class_box.deselect()
            for rel in self.relationships:
                rel.deselect()
            if self.relationship_mode:
                self.toggle_relationship_mode()
            self.update_status("Ready")
    
    def point_to_curve_distance(self, px, py, rel):
        """Calculate the minimum distance from a point to a bezier curve"""
        from_point, to_point = rel.get_connection_points()
        curve_points = rel.calculate_bezier_curve(from_point, to_point)
        
        # Check distance to each segment of the curve
        min_distance = float('inf')
        
        # curve_points is a flat list [x1, y1, x2, y2, x3, y3, ...]
        for i in range(0, len(curve_points) - 2, 2):
            x1, y1 = curve_points[i], curve_points[i + 1]
            x2, y2 = curve_points[i + 2], curve_points[i + 3]
            
            distance = self.point_to_line_distance(px, py, x1, y1, x2, y2)
            min_distance = min(min_distance, distance)
        
        return min_distance
    
    def point_to_line_distance(self, px, py, x1, y1, x2, y2):
        """Calculate the distance from a point to a line segment"""
        # Vector from line start to end
        dx = x2 - x1
        dy = y2 - y1
        
        # If line segment is actually a point
        if dx == 0 and dy == 0:
            return math.sqrt((px - x1)**2 + (py - y1)**2)
        
        # Calculate the parameter t that represents the projection of point onto line
        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
        
        # Find the closest point on the line segment
        closest_x = x1 + t * dx
        closest_y = y1 + t * dy
        
        # Return distance from point to closest point on line
        return math.sqrt((px - closest_x)**2 + (py - closest_y)**2)
    
    def on_mouse_wheel(self, event):
        """Handle mouse wheel for zooming"""
        # Get mouse position relative to canvas
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        
        # Determine zoom direction
        if event.delta > 0:
            # Zoom in
            scale_factor = 1.1
        else:
            # Zoom out
            scale_factor = 0.9
        
        # Apply zoom
        self.apply_zoom(scale_factor, x, y)
    
    def apply_zoom(self, scale_factor, center_x=None, center_y=None):
        """Apply zoom transformation"""
        # Calculate new zoom level
        new_zoom = self.zoom_level * scale_factor
        
        # Limit zoom range (0.1x to 5x)
        if new_zoom < 0.1 or new_zoom > 5.0:
            return
        
        # If no center point provided, use canvas center
        if center_x is None or center_y is None:
            center_x = self.canvas.winfo_width() / 2
            center_y = self.canvas.winfo_height() / 2
            center_x = self.canvas.canvasx(center_x)
            center_y = self.canvas.canvasy(center_y)
        
        # Update zoom level
        old_zoom = self.zoom_level
        self.zoom_level = new_zoom
        
        # Update class positions and dimensions relative to zoom center
        for class_box in self.classes:
            # Scale position relative to zoom point
            class_box.x = center_x + (class_box.x - center_x) * scale_factor
            class_box.y = center_y + (class_box.y - center_y) * scale_factor
            class_box.width *= scale_factor
            class_box.height *= scale_factor
        
        # Recreate all visuals with scaled fonts and positions
        self.recreate_visuals_with_zoom()
        
        # Update scroll region after zoom
        self.update_scroll_region()
        
        # Update zoom label
        zoom_percent = int(self.zoom_level * 100)
        if hasattr(self, 'zoom_label'):
            self.zoom_label.config(text=f"{zoom_percent}%")
        self.update_status(f"Zoom: {zoom_percent}%")
    
    def set_zoom_level(self, new_zoom):
        """Set zoom level without moving classes (for loading saved state)"""
        if new_zoom < 0.1 or new_zoom > 5.0:
            return
        
        # Calculate scale factor for dimensions only
        scale_factor = new_zoom / self.zoom_level
        
        # Update zoom level
        self.zoom_level = new_zoom
        
        # Update class dimensions (but NOT positions)
        for class_box in self.classes:
            class_box.width *= scale_factor
            class_box.height *= scale_factor
        
        # Recreate all visuals with scaled fonts
        self.recreate_visuals_with_zoom()
        
        # Update scroll region
        self.update_scroll_region()
        
        # Update zoom label
        zoom_percent = int(self.zoom_level * 100)
        if hasattr(self, 'zoom_label'):
            self.zoom_label.config(text=f"{zoom_percent}%")
        self.update_status(f"Zoom: {zoom_percent}%")
    
    def recreate_visuals_with_zoom(self):
        """Recreate all visual elements with scaled fonts"""
        # Store selection states
        selected_classes = [cls for cls in self.classes if cls.selected]
        selected_relationships = [rel for rel in self.relationships if rel.selected]
        
        # Recreate class visuals with scaled fonts
        for class_box in self.classes:
            was_selected = class_box.selected
            class_box.selected = False  # Temporarily deselect to avoid indicator issues
            class_box.create_visual_with_zoom(self.zoom_level)
            if was_selected:
                class_box.select()
        
        # Recreate relationship visuals
        for rel in self.relationships:
            was_selected = rel.selected
            rel.update_position()
            if was_selected:
                rel.select()
    
    def zoom_in(self):
        """Zoom in button handler"""
        self.apply_zoom(1.2)
    
    def zoom_out(self):
        """Zoom out button handler"""
        self.apply_zoom(0.8)
    
    def zoom_reset(self):
        """Reset zoom to 100%"""
        if self.zoom_level != 1.0:
            scale_factor = 1.0 / self.zoom_level
            self.apply_zoom(scale_factor)
    
    def add_class(self):
        x = 150 + (len(self.classes) % 4) * 250  # Better positioning with wrapping
        y = 150 + (len(self.classes) // 4) * 200
        class_box = ClassBox(self.canvas, x, y, f"Class{len(self.classes) + 1}", self)
        self.classes.append(class_box)
        
        # Auto-select the new class
        for cls in self.classes:
            cls.deselect()
        class_box.select()
        self.selected_class = class_box
        
        self.update_scroll_region()
        self.mark_as_changed()
        
    def canvas_click(self, event):
        # Convert to canvas coordinates (accounts for scrolling and zoom)
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        if self.relationship_mode:
            # Find clicked class using canvas coordinates
            clicked_class = None
            for class_box in self.classes:
                if (class_box.x <= canvas_x <= class_box.x + class_box.width and
                    class_box.y <= canvas_y <= class_box.y + class_box.height):
                    clicked_class = class_box
                    break
                    
            if clicked_class:
                if self.relationship_start is None:
                    self.relationship_start = clicked_class
                    clicked_class.select()
                else:
                    if clicked_class != self.relationship_start:
                        # Create relationship
                        rel = Relationship(self.canvas, self.relationship_start, 
                                         clicked_class, self.rel_type_var.get(), self)
                        self.relationships.append(rel)
                        self.mark_as_changed()
                    
                    # Reset relationship mode
                    if self.relationship_start:
                        self.relationship_start.deselect()
                    self.relationship_start = None
                    self.relationship_mode = False
                    self.rel_button.config(text="Add Relationship", relief=tk.RAISED)
        else:
            # Check if we clicked on a class with improved detection using canvas coordinates
            clicked_class = None
            for class_box in self.classes:
                # Use a slightly larger hit area for better selection of small/empty classes
                hit_margin = 2
                if (class_box.x - hit_margin <= canvas_x <= class_box.x + class_box.width + hit_margin and
                    class_box.y - hit_margin <= canvas_y <= class_box.y + class_box.height + hit_margin):
                    clicked_class = class_box
                    break
            
            # Check if we clicked on a relationship line
            clicked_relationship = None
            if not clicked_class:  # Only check relationships if we didn't click a class
                # Check each relationship with a tolerance for easier selection
                selection_tolerance = 50  # pixels - larger area for easier clicking
                
                for rel in self.relationships:
                    # Calculate distance from click point to the curved line
                    distance = self.point_to_curve_distance(canvas_x, canvas_y, rel)
                    
                    if distance <= selection_tolerance:
                        clicked_relationship = rel
                        break
            
            # Handle different click scenarios
            if clicked_class:
                # Clicked on a class - definitely not panning
                self.is_panning = False
                
                # Deselect all classes first
                for class_box in self.classes:
                    class_box.deselect()
                
                # Deselect all relationships
                for rel in self.relationships:
                    rel.deselect()
                
                # Select the clicked class
                clicked_class.select()
                self.selected_class = clicked_class
                self.update_status(f"Selected class: {clicked_class.name}")
                
            elif clicked_relationship:
                # Clicked on a relationship - not panning
                self.is_panning = False
                
            else:
                # Clicked on empty space - check if really empty
                # Convert event coordinates to canvas coordinates
                canvas_x = self.canvas.canvasx(event.x)
                canvas_y = self.canvas.canvasy(event.y)
                
                # Double-check no class at this position (using canvas coordinates)
                really_empty = True
                for class_box in self.classes:
                    if (class_box.x <= canvas_x <= class_box.x + class_box.width and
                        class_box.y <= canvas_y <= class_box.y + class_box.height):
                        really_empty = False
                        break
                
                if really_empty:
                    # Start panning
                    self.is_panning = True
                    self.pan_start_x = canvas_x
                    self.pan_start_y = canvas_y
                    
                    # Change cursor to indicate panning mode
                    self.canvas.config(cursor="fleur")  # Four-way arrow cursor
                    
                    # Deselect all classes
                    for class_box in self.classes:
                        class_box.deselect()
                    
                    # Deselect all relationships
                    for rel in self.relationships:
                        rel.deselect()
                    
                    self.selected_class = None
                    self.update_status("Pan mode - drag to move diagram")
                else:
                    self.is_panning = False
    
    def canvas_drag(self, event):
        """Handle canvas drag for panning"""
        # Don't pan if a class is selected (it's being dragged individually)
        if self.selected_class is not None:
            return
            
        if self.is_panning:
            # Convert to canvas coordinates
            canvas_x = self.canvas.canvasx(event.x)
            canvas_y = self.canvas.canvasy(event.y)
            
            # Calculate drag distance
            dx = canvas_x - self.pan_start_x
            dy = canvas_y - self.pan_start_y
            
            # Move all classes
            for class_box in self.classes:
                class_box.x += dx
                class_box.y += dy
                
                # Move all visual elements
                if hasattr(class_box, 'visual_elements'):
                    for element in class_box.visual_elements:
                        self.canvas.move(element, dx, dy)
                
                # Move content elements
                for item in self.canvas.find_withtag("content_" + str(id(class_box))):
                    self.canvas.move(item, dx, dy)
                
                # Update selection indicators if selected
                if class_box.selected:
                    class_box.update_selection_indicators()
            
            # Update all relationships
            self.update_relationships()
            
            # Update pan start position for next drag event
            self.pan_start_x = canvas_x
            self.pan_start_y = canvas_y
            
            # Update scroll region
            self.update_scroll_region()
        # If not panning, the drag event will be handled by individual class objects
    
    def canvas_release(self, event):
        """Handle mouse button release"""
        if self.is_panning:
            self.is_panning = False
            # Reset cursor to default
            self.canvas.config(cursor="")
            self.update_status("Ready")
            
            # Auto-save positions after panning (if we have a current file)
            if self.current_file and os.path.exists(self.current_file):
                try:
                    self.save_positions(self.current_file)
                except Exception as e:
                    print(f"Warning: Could not auto-save positions after panning: {e}")
    
    def canvas_motion(self, event):
        """Handle mouse motion to update cursor"""
        # Don't change cursor if we're in relationship mode or currently panning
        if self.relationship_mode or self.is_panning:
            return
        
        # Convert to canvas coordinates
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        # Check if mouse is over a class
        over_class = False
        for class_box in self.classes:
            if (class_box.x <= canvas_x <= class_box.x + class_box.width and
                class_box.y <= canvas_y <= class_box.y + class_box.height):
                over_class = True
                break
        
        # Set cursor based on what we're hovering over
        if over_class:
            self.canvas.config(cursor="hand2")  # Hand cursor over classes
        else:
            self.canvas.config(cursor="")  # Default cursor over empty space
    
    def canvas_right_click(self, event):
        """Handle right-click to create new class"""
        if not self.relationship_mode:
            # Convert to canvas coordinates
            canvas_x = self.canvas.canvasx(event.x)
            canvas_y = self.canvas.canvasy(event.y)
            
            # Check if we right-clicked on a class first
            clicked_class = None
            for class_box in self.classes:
                if (class_box.x <= canvas_x <= class_box.x + class_box.width and
                    class_box.y <= canvas_y <= class_box.y + class_box.height):
                    clicked_class = class_box
                    break
            
            # Only create new class if we didn't right-click on an existing one
            if not clicked_class:
                self.add_class_at_position(canvas_x, canvas_y)
            
    def add_class_at_position(self, x, y):
        class_box = ClassBox(self.canvas, x, y, f"Class{len(self.classes) + 1}", self)
        self.classes.append(class_box)
        
        # Auto-select the new class
        for cls in self.classes:
            cls.deselect()
        class_box.select()
        self.selected_class = class_box
        
        self.update_scroll_region()
        self.mark_as_changed()
        
    def delete_selected(self):
        # Delete selected classes
        to_remove = []
        for class_box in self.classes:
            if class_box.selected:
                to_remove.append(class_box)
                
        for class_box in to_remove:
            # Remove relationships involving this class
            rel_to_remove = []
            for rel in self.relationships:
                if rel.from_class == class_box or rel.to_class == class_box:
                    rel_to_remove.append(rel)
                    
            for rel in rel_to_remove:
                rel.delete()
                self.relationships.remove(rel)
                
            # Remove class
            class_box.delete()
            self.classes.remove(class_box)
            
        # Delete selected relationships
        rel_to_remove = []
        for rel in self.relationships:
            if rel.selected:
                rel_to_remove.append(rel)
                
        for rel in rel_to_remove:
            rel.delete()
            self.relationships.remove(rel)
        
        # Mark as changed if anything was deleted
        if to_remove or rel_to_remove:
            self.mark_as_changed()
            
    def toggle_relationship_mode(self):
        if self.relationship_mode:
            self.relationship_mode = False
            self.rel_button.config(text="Add Relationship", relief=tk.RAISED)
            if self.relationship_start:
                self.relationship_start.deselect()
            self.relationship_start = None
        else:
            self.relationship_mode = True
            self.rel_button.config(text="Cancel Relationship", relief=tk.SUNKEN)
            
    def update_scroll_region(self):
        """Update canvas scroll region to include all elements with padding"""
        # Get bounding box of all items on canvas
        bbox = self.canvas.bbox("all")
        
        if bbox:
            # Add padding around the content
            padding = 100
            x1, y1, x2, y2 = bbox
            scroll_region = (
                x1 - padding,
                y1 - padding,
                x2 + padding,
                y2 + padding
            )
            self.canvas.configure(scrollregion=scroll_region)
        else:
            # Default scroll region if no items
            self.canvas.configure(scrollregion=(0, 0, 2000, 2000))
        
    def save_mermaid(self):
        """Save diagram as Mermaid format"""
        # If no current file, ask for filename
        if not self.current_file:
            filename = filedialog.asksaveasfilename(
                defaultextension=".md",
                filetypes=[("Markdown files", "*.md"), ("Text files", "*.txt"), ("All files", "*.*")]
            )
        else:
            # Save to current file
            filename = self.current_file
        
        if filename:
            try:
                mermaid_code = self.generate_mermaid()
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write("```mermaid\n")
                    f.write(mermaid_code)
                    f.write("\n```")
                
                # Save positions to companion file
                self.save_positions(filename)
                
                self.current_file = filename
                self.mark_as_saved()
                self.save_last_file_path()
                self.update_status(f"Saved to {os.path.basename(filename)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {str(e)}")
            
    def open_mermaid(self):
        """Open and load a Mermaid diagram"""
        # Check for unsaved changes
        if self.has_unsaved_changes:
            response = messagebox.askyesnocancel(
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save before opening a new file?"
            )
            
            if response is None:  # Cancel
                return
            elif response:  # Yes - save
                self.save_mermaid()
                if self.has_unsaved_changes:  # Save was cancelled
                    return
        
        filename = filedialog.askopenfilename(
            filetypes=[("Markdown files", "*.md"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            try:
                # Try UTF-8 first, then fall back to other encodings
                content = None
                encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']
                
                for encoding in encodings:
                    try:
                        with open(filename, 'r', encoding=encoding) as f:
                            content = f.read()
                        break  # Success, stop trying
                    except UnicodeDecodeError:
                        continue  # Try next encoding
                
                if content is None:
                    messagebox.showerror("Error", "Could not decode file. Please ensure it's a text file.")
                    return
                
                # Extract mermaid code from markdown code blocks or plain text
                mermaid_code = self.extract_mermaid_code(content)
                if mermaid_code:
                    # Check if position file exists before parsing
                    positions = self.load_positions(filename)
                    
                    # Set zoom level BEFORE parsing if we have saved positions (don't move classes)
                    if positions and "zoom_level" in positions:
                        saved_zoom = positions["zoom_level"]
                        if saved_zoom > 0:
                            print(f"Debug: Setting zoom level to: {saved_zoom}")
                            self.set_zoom_level(saved_zoom)
                    
                    # Parse diagram (skip auto-layout if we have saved positions)
                    self.parse_mermaid(mermaid_code, apply_auto_layout=(positions is None))
                    
                    # Apply saved positions if they exist (but skip zoom since we already did it)
                    if positions:
                        self.apply_positions(positions, skip_zoom=True)
                        self.update_status(f"Loaded from {os.path.basename(filename)} (with saved positions)")
                    else:
                        self.update_status(f"Loaded from {os.path.basename(filename)} (auto-layout applied)")
                    
                    self.current_file = filename
                    self.mark_as_saved()
                    self.save_last_file_path()
                else:
                    messagebox.showerror("Error", "No valid Mermaid class diagram found in file")
                    
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open file: {str(e)}")
    
    def new_diagram(self):
        """Create a new diagram"""
        # Check for unsaved changes
        if self.has_unsaved_changes:
            response = messagebox.askyesnocancel(
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save before creating a new diagram?"
            )
            
            if response is None:  # Cancel
                return
            elif response:  # Yes - save
                self.save_mermaid()
                if self.has_unsaved_changes:  # Save was cancelled
                    return
        
        # Clear the diagram
        for class_box in self.classes:
            class_box.delete()
        for rel in self.relationships:
            rel.delete()
        self.classes.clear()
        self.relationships.clear()
        
        self.current_file = None
        self.mark_as_saved()
        self.update_status("New diagram created")
        
    def extract_mermaid_code(self, content):
        """Extract Mermaid code from markdown code blocks or plain text"""
        # Try to find mermaid code block first
        mermaid_block_pattern = r'```mermaid\s*\n(.*?)\n```'
        match = re.search(mermaid_block_pattern, content, re.DOTALL | re.IGNORECASE)
        
        if match:
            return match.group(1).strip()
        
        # If no code block, check if the entire content is mermaid
        if 'classDiagram' in content:
            return content.strip()
        
        return None
    
    def parse_mermaid(self, mermaid_code, apply_auto_layout=True):
        """Parse Mermaid class diagram code and create visual elements"""
        self.new_diagram()  # Clear current diagram
        
        lines = [line.strip() for line in mermaid_code.split('\n') if line.strip()]
        
        # Find classDiagram declaration
        if not any('classDiagram' in line for line in lines):
            raise ValueError("Not a valid Mermaid class diagram")
        
        classes_data = {}
        relationships = []
        notes = {}
        current_class = None
        
        for line in lines:
            if 'classDiagram' in line:
                continue
            
            # Parse notes
            note_match = re.match(r'\s*note\s+for\s+(\w+)\s+"([^"]+)"', line)
            if note_match:
                class_name, note_text = note_match.groups()
                if class_name not in notes:
                    notes[class_name] = []
                notes[class_name].append(note_text)
                continue
            
            # Parse class annotations and stereotypes
            annotation_match = re.match(r'\s*(\w+)\s*:\s*@(\w+)', line)
            if annotation_match:
                class_name, annotation = annotation_match.groups()
                if class_name not in classes_data:
                    classes_data[class_name] = {'attributes': [], 'methods': [], 'annotations': [], 'stereotype': ''}
                classes_data[class_name]['annotations'].append(annotation)
                continue
            
            stereotype_match = re.match(r'\s*(\w+)\s*:\s*<<([^>]+)>>', line)
            if stereotype_match:
                class_name, stereotype = stereotype_match.groups()
                if class_name not in classes_data:
                    classes_data[class_name] = {'attributes': [], 'methods': [], 'annotations': [], 'stereotype': ''}
                classes_data[class_name]['stereotype'] = stereotype
                continue
                
            # Parse class definition start
            class_match = re.match(r'\s*class\s+(\w+)\s*\{', line)
            if class_match:
                current_class = class_match.group(1)
                if current_class not in classes_data:
                    classes_data[current_class] = {'attributes': [], 'methods': [], 'annotations': [], 'stereotype': ''}
                continue
            
            # Parse class definition end
            if line.strip() == '}':
                current_class = None
                continue
            
            # Parse class members (attributes and methods)
            if current_class:
                member_match = re.match(r'\s*([+\-#~]?\s*.+)', line)
                if member_match:
                    member = member_match.group(1).strip()
                    if member.endswith('()') or '(' in member:
                        # It's a method
                        classes_data[current_class]['methods'].append(member)
                    else:
                        # It's an attribute
                        classes_data[current_class]['attributes'].append(member)
                continue
            
            # Parse relationships with enhanced syntax
            rel_patterns = [
                # Inheritance
                (r'(\w+)(?:\s+"([^"]+)")?\s*<\|\-\-(?:\s+"([^"]+)")?\s*(\w+)(?:\s*:\s*(.+))?', 'inheritance', True),
                # Realization
                (r'(\w+)(?:\s+"([^"]+)")?\s*<\|\.\.\s*(?:\s+"([^"]+)")?\s*(\w+)(?:\s*:\s*(.+))?', 'realization', True),
                # Composition
                (r'(\w+)(?:\s+"([^"]+)")?\s*\*\-\-(?:\s+"([^"]+)")?\s*(\w+)(?:\s*:\s*(.+))?', 'composition', False),
                # Aggregation
                (r'(\w+)(?:\s+"([^"]+)")?\s*o\-\-(?:\s+"([^"]+)")?\s*(\w+)(?:\s*:\s*(.+))?', 'aggregation', False),
                # Dependency
                (r'(\w+)(?:\s+"([^"]+)")?\s*<\.\.(?:\s+"([^"]+)")?\s*(\w+)(?:\s*:\s*(.+))?', 'dependency', False),
                # Association
                (r'(\w+)(?:\s+"([^"]+)")?\s*\-\->(?:\s+"([^"]+)")?\s*(\w+)(?:\s*:\s*(.+))?', 'association', False),
                (r'(\w+)(?:\s+"([^"]+)")?\s*\-\-(?:\s+"([^"]+)")?\s*(\w+)(?:\s*:\s*(.+))?', 'association', False),
            ]
            
            for pattern, rel_type, reversed_rel in rel_patterns:
                match = re.match(pattern, line)
                if match:
                    groups = match.groups()
                    class1, mult1, mult2, class2, label = groups
                    
                    if reversed_rel:
                        # For inheritance/realization, the arrow points from child to parent
                        from_class, to_class = class2, class1
                        from_mult, to_mult = mult2 or "", mult1 or ""
                    else:
                        from_class, to_class = class1, class2
                        from_mult, to_mult = mult1 or "", mult2 or ""
                    
                    relationships.append({
                        'from': from_class,
                        'to': to_class,
                        'type': rel_type,
                        'label': label or "",
                        'from_multiplicity': from_mult,
                        'to_multiplicity': to_mult
                    })
                    break
        
        # Create visual classes
        class_positions = self.calculate_class_positions(len(classes_data))
        class_objects = {}
        
        for i, (class_name, class_data) in enumerate(classes_data.items()):
            x, y = class_positions[i]
            class_box = ClassBox(self.canvas, x, y, class_name, self)
            class_box.attributes = class_data['attributes']
            class_box.methods = class_data['methods']
            class_box.annotations = class_data['annotations']
            class_box.stereotype = class_data['stereotype']
            class_box.notes = notes.get(class_name, [])
            
            # Recreate visual with updated content
            class_box.canvas.delete(class_box.rect)
            class_box.canvas.delete(class_box.name_text)
            class_box.canvas.delete(class_box.sep_line)
            class_box.create_visual()
            
            self.classes.append(class_box)
            class_objects[class_name] = class_box
        
        # Create relationships
        for rel_data in relationships:
            if rel_data['from'] in class_objects and rel_data['to'] in class_objects:
                from_class = class_objects[rel_data['from']]
                to_class = class_objects[rel_data['to']]
                rel = Relationship(self.canvas, from_class, to_class, rel_data['type'], self)
                rel.label = rel_data['label']
                rel.from_multiplicity = rel_data['from_multiplicity']
                rel.to_multiplicity = rel_data['to_multiplicity']
                self.relationships.append(rel)
        
        # Apply hierarchical layout automatically (unless positions will be loaded)
        if apply_auto_layout:
            self.apply_hierarchical_layout()
        
        self.update_scroll_region()
    
    def calculate_class_positions(self, num_classes):
        """Calculate positions for imported classes using hierarchical layout"""
        if num_classes == 0:
            return []
        
        # Build a graph of relationships to determine hierarchy
        # This will be populated when relationships are created
        # For now, use a smarter grid layout with better spacing
        positions = []
        
        # Use a more spread out layout similar to Mermaid
        cols = max(1, min(3, int(math.sqrt(num_classes * 1.2))))
        rows = math.ceil(num_classes / cols)
        
        start_x, start_y = 200, 150
        spacing_x, spacing_y = 400, 350  # Increased spacing to prevent overlap
        
        for i in range(num_classes):
            row = i // cols
            col = i % cols
            # Center each row
            row_classes = min(cols, num_classes - row * cols)
            row_offset = (cols - row_classes) * spacing_x / 2
            x = start_x + col * spacing_x + row_offset
            y = start_y + row * spacing_y
            positions.append((x, y))
        
        return positions
    
    def apply_hierarchical_layout(self):
        """Apply hierarchical layout based on relationships with collision avoidance"""
        if not self.classes:
            self.update_status("No classes to layout")
            return
        
        self.update_status("Applying hierarchical layout...")
        
        # Build dependency graph
        graph = {}
        in_degree = {}
        all_connections = {}  # Track all relationships for proximity
        
        for cls in self.classes:
            graph[cls] = []
            in_degree[cls] = 0
            all_connections[cls] = set()
        
        # Build graph from relationships (inheritance and composition create hierarchy)
        for rel in self.relationships:
            if rel.rel_type in ['inheritance', 'composition', 'realization']:
                # Parent/container is at higher level
                graph[rel.to_class].append(rel.from_class)
                in_degree[rel.from_class] += 1
            
            # Track all connections for proximity
            all_connections[rel.from_class].add(rel.to_class)
            all_connections[rel.to_class].add(rel.from_class)
        
        # Topological sort to determine levels
        levels = []
        current_level = [cls for cls in self.classes if in_degree[cls] == 0]
        
        if not current_level:
            # No clear hierarchy, use first class
            current_level = [self.classes[0]]
        
        visited = set()
        while current_level:
            levels.append(current_level[:])
            next_level = []
            
            for cls in current_level:
                visited.add(cls)
                for child in graph[cls]:
                    if child not in visited:
                        next_level.append(child)
            
            # Remove duplicates
            next_level = list(dict.fromkeys(next_level))
            current_level = next_level
        
        # Add any remaining classes that weren't in the hierarchy
        remaining = [cls for cls in self.classes if cls not in visited]
        if remaining:
            levels.append(remaining)
        
        # Sort classes within each level to keep related ones together
        for level in levels:
            if len(level) > 1:
                # Sort by number of connections to already-placed classes
                sorted_level = []
                remaining_in_level = level[:]
                
                # Start with the class that has most connections overall
                if remaining_in_level:
                    first = max(remaining_in_level, key=lambda c: len(all_connections[c]))
                    sorted_level.append(first)
                    remaining_in_level.remove(first)
                
                # Add remaining classes based on proximity to already sorted ones
                while remaining_in_level:
                    best_class = None
                    best_score = -1
                    
                    for candidate in remaining_in_level:
                        # Count connections to already sorted classes
                        score = sum(1 for sorted_cls in sorted_level 
                                  if sorted_cls in all_connections[candidate])
                        
                        if score > best_score:
                            best_score = score
                            best_class = candidate
                    
                    if best_class:
                        sorted_level.append(best_class)
                        remaining_in_level.remove(best_class)
                    else:
                        # No connections, just add the first one
                        sorted_level.append(remaining_in_level[0])
                        remaining_in_level.pop(0)
                
                # Update the level with sorted order
                level[:] = sorted_level
        
        # Calculate maximum width needed for each class in each level
        level_max_widths = []
        for level in levels:
            max_width = max([cls.width for cls in level]) if level else 200
            level_max_widths.append(max_width)
        
        # Calculate maximum height needed for each level
        level_max_heights = []
        for level in levels:
            max_height = max([cls.height for cls in level]) if level else 120
            level_max_heights.append(max_height)
        
        # Position classes based on levels with proper spacing
        start_x, start_y = 200, 150
        horizontal_gap = 60  # Reduced gap for closer placement
        vertical_gap = 100   # Gap between levels vertically
        
        for level_idx, level in enumerate(levels):
            # Calculate Y position for this level
            y = start_y + sum(level_max_heights[:level_idx]) + level_idx * vertical_gap
            
            # Calculate total width needed for this level
            total_width = sum([cls.width for cls in level]) + (len(level) - 1) * horizontal_gap
            
            # Center the level horizontally
            canvas_width = self.canvas.winfo_width() if self.canvas.winfo_width() > 1 else 1200
            start_x_level = max(start_x, (canvas_width - total_width) / 2)
            
            # Position each class in the level
            current_x = start_x_level
            for cls in level:
                # Move class to new position (center it vertically within the level)
                target_x = current_x
                target_y = y
                
                dx = target_x - cls.x
                dy = target_y - cls.y
                cls.move(dx, dy)
                
                # Move to next position
                current_x += cls.width + horizontal_gap
        
        # Apply force-directed adjustment to bring connected classes closer
        self.apply_force_directed_layout(all_connections, levels, iterations=5)
        
        # Resolve any remaining overlaps with iterative adjustment
        self.resolve_overlaps()
        
        # Update all relationships
        self.update_relationships()
        self.update_scroll_region()
        
        self.update_status(f"Layout applied: {len(levels)} levels, {len(self.classes)} classes")
    
    def apply_selected_layout(self):
        """Apply the layout selected in the dropdown"""
        layout_mode = self.layout_mode_var.get()
        
        if layout_mode == "dagre":
            self.apply_dagre_layout()
        else:  # hierarchical (default)
            self.apply_hierarchical_layout()
    
    def apply_force_directed_layout(self, connections, levels, iterations=5):
        """Apply force-directed adjustments to bring connected classes closer"""
        # Create a mapping of class to level index
        class_to_level = {}
        for level_idx, level in enumerate(levels):
            for cls in level:
                class_to_level[cls] = level_idx
        
        for iteration in range(iterations):
            # Calculate forces for each class
            forces = {}
            for cls in self.classes:
                forces[cls] = {'x': 0, 'y': 0}
            
            # Attraction force between connected classes
            for cls in self.classes:
                for connected_cls in connections[cls]:
                    # Only apply horizontal force if they're in the same level
                    if class_to_level[cls] == class_to_level[connected_cls]:
                        # Calculate distance
                        dx = connected_cls.x - cls.x
                        dy = connected_cls.y - cls.y
                        distance = math.sqrt(dx*dx + dy*dy)
                        
                        if distance > 0:
                            # Attraction force (spring-like)
                            force_magnitude = distance * 0.1  # Adjust strength
                            
                            # Only apply horizontal force to keep level structure
                            forces[cls]['x'] += (dx / distance) * force_magnitude
            
            # Apply forces with damping
            damping = 0.5
            for cls in self.classes:
                # Only move horizontally to maintain level structure
                move_x = forces[cls]['x'] * damping
                
                # Limit movement to prevent chaos
                max_move = 20
                move_x = max(-max_move, min(max_move, move_x))
                
                cls.move(move_x, 0)
    
    def resolve_overlaps(self, max_iterations=10):
        """Resolve overlapping classes by adjusting positions"""
        min_gap = 30  # Minimum gap between classes
        
        for iteration in range(max_iterations):
            overlaps_found = False
            
            for i, cls1 in enumerate(self.classes):
                for cls2 in self.classes[i+1:]:
                    # Check if classes overlap
                    if self.classes_overlap(cls1, cls2, min_gap):
                        overlaps_found = True
                        
                        # Calculate overlap amount
                        center1 = cls1.get_center()
                        center2 = cls2.get_center()
                        
                        dx = center2[0] - center1[0]
                        dy = center2[1] - center1[1]
                        distance = math.sqrt(dx*dx + dy*dy)
                        
                        if distance < 1:
                            # Classes are at same position, move one arbitrarily
                            cls2.move(50, 0)
                            continue
                        
                        # Calculate required separation
                        required_dist = (cls1.width + cls2.width) / 2 + min_gap
                        
                        # Move classes apart
                        if distance < required_dist:
                            # Normalize direction
                            dx_norm = dx / distance
                            dy_norm = dy / distance
                            
                            # Calculate how much to move
                            move_amount = (required_dist - distance) / 2
                            
                            # Move both classes apart
                            cls1.move(-dx_norm * move_amount, -dy_norm * move_amount)
                            cls2.move(dx_norm * move_amount, dy_norm * move_amount)
            
            if not overlaps_found:
                break
    
    def classes_overlap(self, cls1, cls2, min_gap=30):
        """Check if two classes overlap or are too close"""
        # Add gap to dimensions
        left1 = cls1.x - min_gap
        right1 = cls1.x + cls1.width + min_gap
        top1 = cls1.y - min_gap
        bottom1 = cls1.y + cls1.height + min_gap
        
        left2 = cls2.x - min_gap
        right2 = cls2.x + cls2.width + min_gap
        top2 = cls2.y - min_gap
        bottom2 = cls2.y + cls2.height + min_gap
        
        # Check for overlap
        return not (right1 < left2 or right2 < left1 or bottom1 < top2 or bottom2 < top1)
    
    def generate_mermaid(self):
        lines = ["classDiagram"]
        
        # Add classes with enhanced features
        for class_box in self.classes:
            class_name = class_box.name.replace(" ", "_")
            
            # Add annotations
            for annotation in class_box.annotations:
                lines.append(f"    {class_name} : @{annotation}")
            
            # Add stereotype
            if class_box.stereotype:
                lines.append(f"    {class_name} : <<{class_box.stereotype}>>")
            
            lines.append(f"    class {class_name} {{")
            
            # Add attributes with proper formatting
            for attr in class_box.attributes:
                formatted_attr = self.format_mermaid_member(attr)
                lines.append(f"        {formatted_attr}")
                
            # Add methods with proper formatting
            for method in class_box.methods:
                formatted_method = self.format_mermaid_member(method, is_method=True)
                lines.append(f"        {formatted_method}")
                
            lines.append("    }")
            
            # Add notes
            for note in class_box.notes:
                lines.append(f"    note for {class_name} \"{note}\"")
            
        # Add relationships with enhanced syntax
        for rel in self.relationships:
            from_name = rel.from_class.name.replace(" ", "_")
            to_name = rel.to_class.name.replace(" ", "_")
            
            # Build relationship line with multiplicities and labels
            rel_line = f"    {from_name}"
            
            # Add from multiplicity
            if rel.from_multiplicity:
                rel_line += f" \"{rel.from_multiplicity}\""
            
            # Add relationship symbol
            if rel.rel_type == "inheritance":
                rel_line += " <|--"
            elif rel.rel_type == "composition":
                rel_line += " *--"
            elif rel.rel_type == "aggregation":
                rel_line += " o--"
            elif rel.rel_type == "dependency":
                rel_line += " <.."
            elif rel.rel_type == "realization":
                rel_line += " <|.."
            else:  # association
                rel_line += " -->"
            
            # Add to multiplicity
            if rel.to_multiplicity:
                rel_line += f" \"{rel.to_multiplicity}\""
            
            rel_line += f" {to_name}"
            
            # Add relationship label
            if rel.label:
                rel_line += f" : {rel.label}"
                
            lines.append(rel_line)
                
        return "\n".join(lines)
    
    def format_mermaid_member(self, member, is_method=False):
        """Format member for Mermaid output with proper visibility symbols"""
        # Ensure proper formatting
        if not member.startswith(('+', '-', '#', '~')):
            member = '+' + member
        
        # Add parentheses for methods if not present
        if is_method and not member.endswith(')'):
            if '(' not in member:
                member += '()'
        
        return member
    
    def save_positions(self, mermaid_file):
        """Save class positions to a companion JSON file (normalized to zoom 1.0)"""
        import json
        
        # Create position file path (same name with .positions.json extension)
        position_file = mermaid_file + ".positions.json"
        
        # Get current canvas scroll position (viewport)
        canvas_xview = self.canvas.xview()
        canvas_yview = self.canvas.yview()
        
        positions = {
            "zoom_level": self.zoom_level,
            "canvas_viewport": {
                "xview": list(canvas_xview),
                "yview": list(canvas_yview)
            },
            "classes": {},
            "metadata": {
                "version": "1.2",  # Updated version for normalized coordinates
                "saved_at": str(os.path.getmtime(mermaid_file)) if os.path.exists(mermaid_file) else ""
            }
        }
        
        # Save each class position (normalized to zoom 1.0)
        for class_box in self.classes:
            try:
                class_name = class_box.name.replace(" ", "_")
                # Normalize positions to zoom 1.0 for consistent loading
                normalized_x = class_box.x / self.zoom_level if self.zoom_level > 0 else class_box.x
                normalized_y = class_box.y / self.zoom_level if self.zoom_level > 0 else class_box.y
                normalized_width = class_box.width / self.zoom_level if self.zoom_level > 0 else class_box.width
                normalized_height = class_box.height / self.zoom_level if self.zoom_level > 0 else class_box.height
                
                positions["classes"][class_name] = {
                    "x": float(normalized_x),
                    "y": float(normalized_y),
                    "width": float(normalized_width),
                    "height": float(normalized_height)
                }
                print(f"Debug: Saving {class_name} at normalized ({normalized_x:.1f}, {normalized_y:.1f}) from actual ({class_box.x:.1f}, {class_box.y:.1f}) at zoom {self.zoom_level}")
            except Exception as e:
                print(f"Warning: Could not save position for class {class_box.name}: {e}")
                continue
        
        try:
            with open(position_file, 'w') as f:
                json.dump(positions, f, indent=2)
            print(f"Debug: Saved {len(positions['classes'])} class positions to {position_file}")
        except Exception as e:
            print(f"Warning: Could not save positions file: {e}")
            # Don't show error to user - position saving is optional
    
    def load_positions(self, mermaid_file):
        """Load class positions from companion JSON file"""
        import json
        
        # Create position file path
        position_file = mermaid_file + ".positions.json"
        
        print(f"Debug: Looking for position file: {position_file}")
        
        if not os.path.exists(position_file):
            # Position file doesn't exist - this is normal for old diagrams
            print(f"Debug: Position file not found")
            return None
        
        print(f"Debug: Position file found, loading...")
        
        try:
            with open(position_file, 'r') as f:
                positions = json.load(f)
            print(f"Debug: Successfully loaded positions with {len(positions.get('classes', {}))} classes")
            return positions
        except json.JSONDecodeError as e:
            # Invalid JSON - silently ignore and use default layout
            print(f"Warning: Could not parse position file (invalid JSON): {e}")
            return None
        except Exception as e:
            # Other errors - silently ignore
            print(f"Warning: Could not load positions: {e}")
            return None
    
    def apply_positions(self, positions, skip_zoom=False):
        """Apply saved positions to classes (positions are normalized to zoom 1.0)"""
        if not positions:
            print("Debug: No positions to apply")
            return
        
        if "classes" not in positions:
            print("Warning: Position file missing 'classes' data")
            return
        
        print(f"Debug: Applying positions for {len(positions['classes'])} classes")
        print(f"Debug: Current zoom level: {self.zoom_level}")
        
        try:
            # Apply zoom level if saved (unless we already did it)
            if not skip_zoom and "zoom_level" in positions:
                saved_zoom = positions["zoom_level"]
                print(f"Debug: Saved zoom level: {saved_zoom}")
                if saved_zoom > 0:
                    print(f"Debug: Setting zoom level to: {saved_zoom}")
                    self.set_zoom_level(saved_zoom)
            
            # Apply positions to each class (scale from normalized to current zoom)
            applied_count = 0
            for class_box in self.classes:
                class_name = class_box.name.replace(" ", "_")
                if class_name in positions["classes"]:
                    pos = positions["classes"][class_name]
                    
                    # Validate position data
                    if "x" in pos and "y" in pos:
                        # Scale normalized positions to current zoom level
                        target_x = pos["x"] * self.zoom_level
                        target_y = pos["y"] * self.zoom_level
                        
                        # Move class to saved position
                        old_x, old_y = class_box.x, class_box.y
                        dx = target_x - class_box.x
                        dy = target_y - class_box.y
                        class_box.move(dx, dy)
                        applied_count += 1
                        print(f"Debug: Moved {class_name} from ({old_x:.1f}, {old_y:.1f}) to ({class_box.x:.1f}, {class_box.y:.1f}) [normalized: ({pos['x']:.1f}, {pos['y']:.1f})]")
                else:
                    print(f"Debug: No saved position for class '{class_name}'")
            
            print(f"Debug: Applied positions to {applied_count}/{len(self.classes)} classes")
            
            # Update relationships after moving classes
            self.update_relationships()
            self.update_scroll_region()
        except Exception as e:
            print(f"Warning: Error applying positions: {e}")
            # Continue anyway - diagram will use default positions
    
    def mark_as_changed(self):
        """Mark the diagram as having unsaved changes"""
        if not self.has_unsaved_changes:
            self.has_unsaved_changes = True
            self.update_window_title()
    
    def mark_as_saved(self):
        """Mark the diagram as saved"""
        self.has_unsaved_changes = False
        self.update_window_title()
    
    def update_window_title(self):
        """Update window title to show current file and unsaved changes"""
        title = "Mermaid UML Class Diagram Tool"
        if self.current_file:
            import os
            filename = os.path.basename(self.current_file)
            title = f"{filename} - {title}"
        if self.has_unsaved_changes:
            title = f"*{title}"
        self.root.title(title)
    
    def save_last_file_path(self):
        """Save the last opened file path to config"""
        if self.current_file:
            try:
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    f.write(self.current_file)
            except Exception as e:
                print(f"Could not save config: {e}")
    
    def load_last_file_path(self):
        """Load the last opened file path from config"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return f.read().strip()
        except Exception as e:
            print(f"Could not load config: {e}")
        return None
    
    def load_last_diagram(self):
        """Load the last used diagram on startup"""
        last_file = self.load_last_file_path()
        if last_file and os.path.exists(last_file):
            try:
                # Try multiple encodings
                content = None
                encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']
                
                for encoding in encodings:
                    try:
                        with open(last_file, 'r', encoding=encoding) as f:
                            content = f.read()
                        break  # Success
                    except UnicodeDecodeError:
                        continue
                
                if content is None:
                    print(f"Could not decode last diagram file: {last_file}")
                    return
                
                mermaid_code = self.extract_mermaid_code(content)
                if mermaid_code:
                    # Check if position file exists before parsing
                    positions = self.load_positions(last_file)
                    
                    # Set zoom level BEFORE parsing if we have saved positions (don't move classes)
                    if positions and "zoom_level" in positions:
                        saved_zoom = positions["zoom_level"]
                        if saved_zoom > 0:
                            print(f"Debug: Setting zoom level to: {saved_zoom}")
                            self.set_zoom_level(saved_zoom)
                    
                    # Parse diagram (skip auto-layout if we have saved positions)
                    self.parse_mermaid(mermaid_code, apply_auto_layout=(positions is None))
                    
                    # Apply saved positions if they exist (but skip zoom since we already did it)
                    if positions:
                        self.apply_positions(positions, skip_zoom=True)
                    
                    self.current_file = last_file
                    self.has_unsaved_changes = False
                    self.update_window_title()
                    self.update_status(f"Loaded: {os.path.basename(last_file)}")
            except Exception as e:
                print(f"Could not load last diagram: {e}")
    
    def on_closing(self):
        """Handle window close event"""
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
        
        # Auto-save positions if we have a current file (even if diagram hasn't changed)
        if self.current_file and os.path.exists(self.current_file):
            try:
                self.save_positions(self.current_file)
            except Exception as e:
                print(f"Warning: Could not save positions on exit: {e}")
        
        # Save the last file path
        self.save_last_file_path()
        
        # Close the application
        self.root.destroy()
        
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = MermaidDiagramTool()
    app.run()