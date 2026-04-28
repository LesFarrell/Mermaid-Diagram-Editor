import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import json
import math
import re
import os


def get_label_perpendicular_vector(from_point, to_point, side=1):
    """Return a normalized perpendicular vector with a stable screen-up bias."""
    dx = to_point[0] - from_point[0]
    dy = to_point[1] - from_point[1]
    length = math.hypot(dx, dy)
    if length == 0:
        return 0.0, -1.0

    perp_x = -dy / length
    perp_y = dx / length
    # Keep the label visually "above" the line in screen space when possible.
    if perp_y > 0:
        perp_x *= -1
        perp_y *= -1

    return perp_x * side, perp_y * side


def get_perpendicular_label_position(from_point, to_point, offset, side=1):
    """Return a point offset from the line midpoint along its perpendicular."""
    mid_x = (from_point[0] + to_point[0]) / 2
    mid_y = (from_point[1] + to_point[1]) / 2
    perp_x, perp_y = get_label_perpendicular_vector(from_point, to_point, side=side)
    return mid_x + (perp_x * offset), mid_y + (perp_y * offset)


def get_endpoint_label_position(point, other_point, along_offset, perpendicular_offset, side=1):
    """Offset a label near a connection endpoint using the line direction."""
    dx = other_point[0] - point[0]
    dy = other_point[1] - point[1]
    length = math.hypot(dx, dy)
    if length == 0:
        return point[0] + along_offset, point[1] - perpendicular_offset

    unit_x = dx / length
    unit_y = dy / length
    perp_x = -unit_y
    perp_y = unit_x
    if perp_y > 0:
        perp_x *= -1
        perp_y *= -1

    return (
        point[0] + (unit_x * along_offset) + (perp_x * perpendicular_offset * side),
        point[1] + (unit_y * along_offset) + (perp_y * perpendicular_offset * side),
    )


def get_centered_text_width(width, ratio, minimum=40):
    """Compute a reasonable wrapped text width inside a scaled shape."""
    return max(minimum, int(width * ratio))


def get_outside_box_label_position(center_point, edge_point, other_point, outward_offset, along_offset=0):
    """Place endpoint text outside a node by moving away from its center."""
    center_dx = edge_point[0] - center_point[0]
    center_dy = edge_point[1] - center_point[1]
    center_length = math.hypot(center_dx, center_dy)
    if center_length == 0:
        outward_x, outward_y = 0, -1
    else:
        outward_x = center_dx / center_length
        outward_y = center_dy / center_length

    line_dx = other_point[0] - edge_point[0]
    line_dy = other_point[1] - edge_point[1]
    line_length = math.hypot(line_dx, line_dy)
    if line_length == 0:
        line_x, line_y = 0, 0
    else:
        line_x = line_dx / line_length
        line_y = line_dy / line_length

    return (
        edge_point[0] + (outward_x * outward_offset) + (line_x * along_offset),
        edge_point[1] + (outward_y * outward_offset) + (line_y * along_offset),
    )


def get_rect_intersection(center, direction, rect):
    """Find the intersection point of a ray from a rectangle center to its edge."""
    cx, cy = center
    dx, dy = direction
    intersections = []

    if dx > 0:
        t = (rect['right'] - cx) / dx
        y = cy + t * dy
        if rect['top'] <= y <= rect['bottom']:
            intersections.append((rect['right'], y))

    if dx < 0:
        t = (rect['left'] - cx) / dx
        y = cy + t * dy
        if rect['top'] <= y <= rect['bottom']:
            intersections.append((rect['left'], y))

    if dy > 0:
        t = (rect['bottom'] - cy) / dy
        x = cx + t * dx
        if rect['left'] <= x <= rect['right']:
            intersections.append((x, rect['bottom']))

    if dy < 0:
        t = (rect['top'] - cy) / dy
        x = cx + t * dx
        if rect['left'] <= x <= rect['right']:
            intersections.append((x, rect['top']))

    if intersections:
        return min(intersections, key=lambda point: math.hypot(point[0] - cx, point[1] - cy))
    return center


def get_box_connection_points(from_rect, to_rect):
    """Calculate line endpoints on the borders of two rectangular nodes."""
    from_center = ((from_rect['left'] + from_rect['right']) / 2, (from_rect['top'] + from_rect['bottom']) / 2)
    to_center = ((to_rect['left'] + to_rect['right']) / 2, (to_rect['top'] + to_rect['bottom']) / 2)
    dx = to_center[0] - from_center[0]
    dy = to_center[1] - from_center[1]
    length = math.hypot(dx, dy)
    if length == 0:
        return from_center, to_center

    dx_norm = dx / length
    dy_norm = dy / length
    from_point = get_rect_intersection(from_center, (dx_norm, dy_norm), from_rect)
    to_point = get_rect_intersection(to_center, (-dx_norm, -dy_norm), to_rect)
    return from_point, to_point


def move_text_away_from_bboxes(canvas, text_item, origin, step_vector, obstacle_bboxes, step_size=8, max_steps=12, padding=2):
    """Nudge a text item along a vector until it no longer overlaps obstacles."""
    step_x = step_vector[0] * step_size
    step_y = step_vector[1] * step_size
    for step in range(max_steps + 1):
        target_x = origin[0] + (step_x * step)
        target_y = origin[1] + (step_y * step)
        canvas.coords(text_item, target_x, target_y)
        bbox = canvas.bbox(text_item)
        if not bbox:
            return
        if not any(
            intersects_bboxes(bbox, obstacle_bbox, padding)
            for obstacle_bbox in obstacle_bboxes
            if obstacle_bbox
        ):
            return


def place_text_avoiding_bboxes(
    canvas,
    text_item,
    preferred_origin,
    preferred_vector,
    obstacle_bboxes,
    alternate_origin=None,
    alternate_vector=None,
    step_size=8,
    max_steps=12,
    padding=2,
):
    """Place text using a preferred direction, then try the alternate side if needed."""
    move_text_away_from_bboxes(
        canvas,
        text_item,
        preferred_origin,
        preferred_vector,
        obstacle_bboxes,
        step_size=step_size,
        max_steps=max_steps,
        padding=padding,
    )
    bbox = canvas.bbox(text_item)
    if not any(intersects_bboxes(bbox, obstacle_bbox, padding) for obstacle_bbox in obstacle_bboxes if obstacle_bbox):
        return
    if alternate_origin is None or alternate_vector is None:
        return
    move_text_away_from_bboxes(
        canvas,
        text_item,
        alternate_origin,
        alternate_vector,
        obstacle_bboxes,
        step_size=step_size,
        max_steps=max_steps,
        padding=padding,
    )


def place_text_near_line(
    canvas,
    text_item,
    from_point,
    to_point,
    obstacle_bboxes,
    preferred_side=1,
    base_offset=12,
    along_offsets=(0, 18, -18, 36, -36, 54, -54),
    offset_steps=(0, 8, 16, 24, 32, 48, 64),
    padding=2,
):
    """Search for a nearby label position that avoids overlapping obstacles."""
    dx = to_point[0] - from_point[0]
    dy = to_point[1] - from_point[1]
    length = math.hypot(dx, dy)
    if length == 0:
        along_x, along_y = 1.0, 0.0
    else:
        along_x, along_y = dx / length, dy / length

    sides = [preferred_side]
    if preferred_side != -preferred_side:
        sides.append(-preferred_side)

    mid_x = (from_point[0] + to_point[0]) / 2
    mid_y = (from_point[1] + to_point[1]) / 2
    fallback = None

    for side in sides:
        perp_x, perp_y = get_label_perpendicular_vector(from_point, to_point, side=side)
        for extra_offset in offset_steps:
            distance = base_offset + extra_offset
            for along in along_offsets:
                candidate_x = mid_x + (along_x * along) + (perp_x * distance)
                candidate_y = mid_y + (along_y * along) + (perp_y * distance)
                canvas.coords(text_item, candidate_x, candidate_y)
                bbox = canvas.bbox(text_item)
                if fallback is None:
                    fallback = (candidate_x, candidate_y)
                if not any(
                    intersects_bboxes(bbox, obstacle_bbox, padding)
                    for obstacle_bbox in obstacle_bboxes
                    if obstacle_bbox
                ):
                    return

    if fallback is not None:
        canvas.coords(text_item, fallback[0], fallback[1])


def intersects_bboxes(a, b, padding=0):
    """Return whether two bboxes intersect."""
    if not a or not b:
        return False
    return not (
        a[2] < b[0] - padding
        or a[0] > b[2] + padding
        or a[3] < b[1] - padding
        or a[1] > b[3] + padding
    )


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
                        self.tool.log_warning(f"Could not auto-save positions: {e}")
                
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
        
        # Keep line behind classes but above grid
        self.canvas.tag_lower(self.line)
        # Raise above grid specifically
        if self.tool and hasattr(self.tool, 'show_grid') and self.canvas.find_withtag("grid"):
            self.canvas.tag_raise(self.line, "grid")
        
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
            label_x, label_y = get_perpendicular_label_position(from_point, to_point, int(12 * zoom_level))
            
            # Relationship label
            if self.label:
                self.label_text = self.canvas.create_text(
                    label_x, label_y,
                    text=self.label, font=("Arial", label_font_size),
                    fill="blue", anchor="center"
                )
                place_text_near_line(
                    self.canvas,
                    self.label_text,
                    from_point,
                    to_point,
                    [
                        self.canvas.bbox(class_box.rect)
                        for class_box in self.tool.classes
                    ] if self.tool else [
                        self.canvas.bbox(self.from_class.rect),
                        self.canvas.bbox(self.to_class.rect),
                    ],
                    preferred_side=1,
                    base_offset=int(12 * zoom_level),
                    padding=2,
                )
                # Keep label behind classes
                self.canvas.tag_lower(self.label_text)
                self.canvas.tag_bind(self.label_text, "<Button-1>", self.on_click)
                self.canvas.tag_bind(self.label_text, "<Double-Button-1>", self.on_double_click)
            
            # From multiplicity
            if self.from_multiplicity:
                from_x, from_y = get_endpoint_label_position(
                    from_point, to_point, int(16 * zoom_level), int(10 * zoom_level)
                )
                self.from_mult_text = self.canvas.create_text(
                    from_x, from_y,
                    text=self.from_multiplicity, font=("Arial", mult_font_size),
                    fill="darkgreen", anchor="center"
                )
                # Keep multiplicity behind classes
                self.canvas.tag_lower(self.from_mult_text)
            
            # To multiplicity
            if self.to_multiplicity:
                to_x, to_y = get_endpoint_label_position(
                    to_point, from_point, int(16 * zoom_level), int(10 * zoom_level)
                )
                self.to_mult_text = self.canvas.create_text(
                    to_x, to_y,
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
        
        # Keep arrows behind classes but above grid
        for arrow_part in self.arrow:
            self.canvas.tag_lower(arrow_part)
            if self.tool and hasattr(self.tool, 'show_grid') and self.canvas.find_withtag("grid"):
                self.canvas.tag_raise(arrow_part, "grid")
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
        
        # Keep arrow behind classes but above grid
        self.canvas.tag_lower(self.arrow)
        if self.tool and hasattr(self.tool, 'show_grid') and self.canvas.find_withtag("grid"):
            self.canvas.tag_raise(self.arrow, "grid")
        
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
        
        # Keep arrow behind classes but above grid
        self.canvas.tag_lower(self.arrow)
        if self.tool and hasattr(self.tool, 'show_grid') and self.canvas.find_withtag("grid"):
            self.canvas.tag_raise(self.arrow, "grid")
        
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
        
        # Keep arrow behind classes but above grid
        self.canvas.tag_lower(self.arrow)
        if self.tool and hasattr(self.tool, 'show_grid') and self.canvas.find_withtag("grid"):
            self.canvas.tag_raise(self.arrow, "grid")
        
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

class FlowchartNode:
    """Represents a flowchart node with different shapes"""
    def __init__(self, canvas, x, y, node_id="node1", text="Node", shape="rectangle", tool=None):
        self.canvas = canvas
        self.tool = tool
        self.x = x
        self.y = y
        self.node_id = node_id
        self.text = text
        self.shape = shape  # rectangle, rounded, diamond, circle
        self.width = 120
        self.height = 60
        self.selected = False
        self.drag_data = {"x": 0, "y": 0}
        
        self.create_visual()
    
    def create_visual(self):
        """Create visual elements"""
        zoom_level = 1.0
        if self.tool and hasattr(self.tool, 'zoom_level'):
            zoom_level = self.tool.zoom_level
        
        # Delete existing elements
        if hasattr(self, 'shape_item'):
            self.canvas.delete(self.shape_item)
        if hasattr(self, 'text_item'):
            self.canvas.delete(self.text_item)
        
        # Scale dimensions
        w = self.width * zoom_level
        h = self.height * zoom_level
        
        # Draw shape based on type
        if self.shape == "rectangle":
            self.shape_item = self.canvas.create_rectangle(
                self.x, self.y, self.x + w, self.y + h,
                fill="lightblue", outline="black", width=max(1, int(2 * zoom_level))
            )
        elif self.shape == "rounded":
            self.shape_item = self.canvas.create_rectangle(
                self.x, self.y, self.x + w, self.y + h,
                fill="lightgreen", outline="black", width=max(1, int(2 * zoom_level))
            )
        elif self.shape == "diamond":
            cx, cy = self.x + w/2, self.y + h/2
            self.shape_item = self.canvas.create_polygon(
                cx, self.y, self.x + w, cy, cx, self.y + h, self.x, cy,
                fill="lightyellow", outline="black", width=max(1, int(2 * zoom_level))
            )
        elif self.shape == "circle":
            self.shape_item = self.canvas.create_oval(
                self.x, self.y, self.x + w, self.y + h,
                fill="lightcoral", outline="black", width=max(1, int(2 * zoom_level))
            )
        
        # Draw text
        font_size = max(8, int(10 * zoom_level))
        text_width_ratio = 0.8
        if self.shape == "diamond":
            text_width_ratio = 0.55
        elif self.shape == "circle":
            text_width_ratio = 0.7
        self.text_item = self.canvas.create_text(
            self.x + w/2, self.y + h/2,
            text=self.text,
            font=("Arial", font_size),
            tags="node_text",
            width=get_centered_text_width(w, text_width_ratio),
            justify="center"
        )
        
        # Bind events
        self.canvas.tag_bind(self.shape_item, "<Button-1>", self.on_press)
        self.canvas.tag_bind(self.shape_item, "<B1-Motion>", self.on_drag)
        self.canvas.tag_bind(self.shape_item, "<ButtonRelease-1>", self.on_release)
        self.canvas.tag_bind(self.shape_item, "<Double-Button-1>", self.on_double_click)
        
        self.canvas.tag_bind(self.text_item, "<Button-1>", self.on_press)
        self.canvas.tag_bind(self.text_item, "<B1-Motion>", self.on_drag)
        self.canvas.tag_bind(self.text_item, "<ButtonRelease-1>", self.on_release)
        self.canvas.tag_bind(self.text_item, "<Double-Button-1>", self.on_double_click)
    
    def on_press(self, event):
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y
        if self.tool:
            self.tool.deselect_all_visuals()
            self.tool.selected_node = self
            self.select()
    
    def on_drag(self, event):
        dx = event.x - self.drag_data["x"]
        dy = event.y - self.drag_data["y"]
        if dx != 0 or dy != 0:
            self._was_dragged = True
        self.x += dx
        self.y += dy
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y
        self.canvas.move(self.shape_item, dx, dy)
        self.canvas.move(self.text_item, dx, dy)
        if self.tool:
            self.tool.update_relationships()
    
    def on_release(self, event):
        if self.tool:
            self.tool.update_scroll_region()
            if hasattr(self, '_was_dragged') and self._was_dragged:
                self.tool.mark_as_changed()
                self._was_dragged = False
            self.tool.save_positions()
    
    def on_double_click(self, event):
        new_text = simpledialog.askstring("Edit Node", "Enter node text:", initialvalue=self.text)
        if new_text:
            self.text = new_text
            self.canvas.itemconfig(self.text_item, text=new_text)
            if self.tool:
                self.tool.mark_as_changed()
    
    def select(self):
        self.selected = True
        self.canvas.itemconfig(self.shape_item, outline="red", width=3)
    
    def deselect(self):
        self.selected = False
        zoom_level = 1.0
        if self.tool and hasattr(self.tool, 'zoom_level'):
            zoom_level = self.tool.zoom_level
        self.canvas.itemconfig(self.shape_item, outline="black", width=max(1, int(2 * zoom_level)))

    def get_center(self):
        zoom_level = self.tool.zoom_level if self.tool and hasattr(self.tool, 'zoom_level') else 1.0
        return (self.x + (self.width * zoom_level) / 2, self.y + (self.height * zoom_level) / 2)

    def delete(self):
        self.canvas.delete(self.shape_item)
        self.canvas.delete(self.text_item)

class SequenceActor:
    """Represents an actor/participant in a sequence diagram"""
    def __init__(self, canvas, x, y, name="Actor", tool=None):
        self.canvas = canvas
        self.tool = tool
        self.x = x
        self.y = y
        self.name = name
        self.width = 80
        self.height = 40
        self.selected = False
        self.drag_data = {"x": 0, "y": 0}
        self.create_visual()
    
    def create_visual(self):
        zoom_level = 1.0
        if self.tool and hasattr(self.tool, 'zoom_level'):
            zoom_level = self.tool.zoom_level
        
        if hasattr(self, 'box'):
            self.canvas.delete(self.box)
        if hasattr(self, 'text_item'):
            self.canvas.delete(self.text_item)
        if hasattr(self, 'lifeline'):
            self.canvas.delete(self.lifeline)
        
        w = self.width * zoom_level
        h = self.height * zoom_level
        
        # Draw actor box
        self.box = self.canvas.create_rectangle(
            self.x, self.y, self.x + w, self.y + h,
            fill="lightblue", outline="black", width=max(1, int(2 * zoom_level))
        )
        
        # Draw lifeline (dashed vertical line) - scale length with zoom
        lifeline_length = 200 * zoom_level
        self.lifeline = self.canvas.create_line(
            self.x + w/2, self.y + h, self.x + w/2, self.y + h + lifeline_length,
            fill="gray", width=max(1, int(1 * zoom_level)), dash=(5, 5)
        )
        
        font_size = max(8, int(10 * zoom_level))
        self.text_item = self.canvas.create_text(
            self.x + w/2, self.y + h/2,
            text=self.name,
            font=("Arial", font_size, "bold"),
            width=get_centered_text_width(w, 0.8),
            justify="center"
        )
        
        # Bind events to all items
        for item in [self.box, self.text_item, self.lifeline]:
            self.canvas.tag_bind(item, "<Button-1>", self.on_press)
            self.canvas.tag_bind(item, "<B1-Motion>", self.on_drag)
            self.canvas.tag_bind(item, "<ButtonRelease-1>", self.on_release)
            self.canvas.tag_bind(item, "<Double-Button-1>", self.on_double_click)
    
    def on_press(self, event):
        if self.tool and self.tool.is_panning:
            return
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y
        if self.tool:
            self.tool.deselect_all_visuals()
            self.tool.selected_item = self
            self.select()
    
    def on_drag(self, event):
        if self.tool and self.tool.is_panning:
            return
        dx = event.x - self.drag_data["x"]
        dy = 0
        if dx != 0:
            self._was_dragged = True
        self.x += dx
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y
        self.canvas.move(self.box, dx, dy)
        self.canvas.move(self.text_item, dx, dy)
        self.canvas.move(self.lifeline, dx, dy)
        if self.tool:
            self.tool.update_relationships()
    
    def on_release(self, event):
        if self.tool:
            self.tool.update_scroll_region()
            if hasattr(self, '_was_dragged') and self._was_dragged:
                self.tool.mark_as_changed()
                self._was_dragged = False
            self.tool.save_positions()
    
    def on_double_click(self, event):
        new_name = simpledialog.askstring("Edit Actor", "Enter actor name:", initialvalue=self.name)
        if new_name:
            self.name = new_name
            self.canvas.itemconfig(self.text_item, text=new_name)
            if self.tool:
                self.tool.mark_as_changed()
    
    def select(self):
        self.selected = True
        zoom_level = 1.0
        if self.tool and hasattr(self.tool, 'zoom_level'):
            zoom_level = self.tool.zoom_level
        self.canvas.itemconfig(self.box, outline="red", width=max(2, int(3 * zoom_level)))
    
    def deselect(self):
        self.selected = False
        zoom_level = 1.0
        if self.tool and hasattr(self.tool, 'zoom_level'):
            zoom_level = self.tool.zoom_level
        self.canvas.itemconfig(self.box, outline="black", width=max(1, int(2 * zoom_level)))

    def get_center(self):
        zoom_level = self.tool.zoom_level if self.tool and hasattr(self.tool, 'zoom_level') else 1.0
        return (self.x + (self.width * zoom_level) / 2, self.y + (self.height * zoom_level) / 2)

    def delete(self):
        self.canvas.delete(self.box)
        self.canvas.delete(self.text_item)
        self.canvas.delete(self.lifeline)

class StateNode:
    """Represents a state in a state diagram"""
    def __init__(self, canvas, x, y, name="State", tool=None):
        self.canvas = canvas
        self.tool = tool
        self.x = x
        self.y = y
        self.name = name
        self.width = 100
        self.height = 50
        self.selected = False
        self.drag_data = {"x": 0, "y": 0}
        self.create_visual()
    
    def create_visual(self):
        zoom_level = 1.0
        if self.tool and hasattr(self.tool, 'zoom_level'):
            zoom_level = self.tool.zoom_level
        
        if hasattr(self, 'box'):
            self.canvas.delete(self.box)
        if hasattr(self, 'text_item'):
            self.canvas.delete(self.text_item)
        
        w = self.width * zoom_level
        h = self.height * zoom_level
        
        # Draw rounded rectangle for state
        self.box = self.canvas.create_rectangle(
            self.x, self.y, self.x + w, self.y + h,
            fill="lightgreen", outline="black", width=max(1, int(2 * zoom_level))
        )
        
        font_size = max(8, int(10 * zoom_level))
        self.text_item = self.canvas.create_text(
            self.x + w/2, self.y + h/2,
            text=self.name,
            font=("Arial", font_size, "bold"),
            width=get_centered_text_width(w, 0.8),
            justify="center"
        )
        
        # Bind events to all items
        for item in [self.box, self.text_item]:
            self.canvas.tag_bind(item, "<Button-1>", self.on_press)
            self.canvas.tag_bind(item, "<B1-Motion>", self.on_drag)
            self.canvas.tag_bind(item, "<ButtonRelease-1>", self.on_release)
            self.canvas.tag_bind(item, "<Double-Button-1>", self.on_double_click)
    
    def on_press(self, event):
        if self.tool and self.tool.is_panning:
            return
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y
        if self.tool:
            self.tool.deselect_all_visuals()
            self.tool.selected_item = self
            self.select()
    
    def on_drag(self, event):
        if self.tool and self.tool.is_panning:
            return
        dx = event.x - self.drag_data["x"]
        dy = event.y - self.drag_data["y"]
        if dx != 0 or dy != 0:
            self._was_dragged = True
        self.x += dx
        self.y += dy
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y
        self.canvas.move(self.box, dx, dy)
        self.canvas.move(self.text_item, dx, dy)
        if self.tool:
            self.tool.update_relationships()
    
    def on_release(self, event):
        if self.tool:
            self.tool.update_scroll_region()
            if hasattr(self, '_was_dragged') and self._was_dragged:
                self.tool.mark_as_changed()
                self._was_dragged = False
            self.tool.save_positions()
    
    def on_double_click(self, event):
        new_name = simpledialog.askstring("Edit State", "Enter state name:", initialvalue=self.name)
        if new_name:
            self.name = new_name
            self.canvas.itemconfig(self.text_item, text=new_name)
            if self.tool:
                self.tool.mark_as_changed()
    
    def select(self):
        self.selected = True
        zoom_level = 1.0
        if self.tool and hasattr(self.tool, 'zoom_level'):
            zoom_level = self.tool.zoom_level
        self.canvas.itemconfig(self.box, outline="red", width=max(2, int(3 * zoom_level)))
    
    def deselect(self):
        self.selected = False
        zoom_level = 1.0
        if self.tool and hasattr(self.tool, 'zoom_level'):
            zoom_level = self.tool.zoom_level
        self.canvas.itemconfig(self.box, outline="black", width=max(1, int(2 * zoom_level)))

    def get_center(self):
        zoom_level = self.tool.zoom_level if self.tool and hasattr(self.tool, 'zoom_level') else 1.0
        return (self.x + (self.width * zoom_level) / 2, self.y + (self.height * zoom_level) / 2)

    def delete(self):
        self.canvas.delete(self.box)
        self.canvas.delete(self.text_item)

class EREntity:
    """Represents an entity in an ER diagram"""
    def __init__(self, canvas, x, y, name="Entity", tool=None):
        self.canvas = canvas
        self.tool = tool
        self.x = x
        self.y = y
        self.name = name
        self.attributes = []
        self.width = 120
        self.height = 80
        self.selected = False
        self.drag_data = {"x": 0, "y": 0}
        self.create_visual()
    
    def create_visual(self):
        zoom_level = 1.0
        if self.tool and hasattr(self.tool, 'zoom_level'):
            zoom_level = self.tool.zoom_level
        
        if hasattr(self, 'box'):
            self.canvas.delete(self.box)
        if hasattr(self, 'text_item'):
            self.canvas.delete(self.text_item)
        
        w = self.width * zoom_level
        h = self.height * zoom_level
        
        # Draw entity box
        self.box = self.canvas.create_rectangle(
            self.x, self.y, self.x + w, self.y + h,
            fill="lightyellow", outline="black", width=max(1, int(2 * zoom_level))
        )
        
        font_size = max(8, int(10 * zoom_level))
        self.text_item = self.canvas.create_text(
            self.x + w/2, self.y + h/2,
            text=self.name,
            font=("Arial", font_size, "bold"),
            width=get_centered_text_width(w, 0.8),
            justify="center"
        )
        
        # Bind events to all items
        for item in [self.box, self.text_item]:
            self.canvas.tag_bind(item, "<Button-1>", self.on_press)
            self.canvas.tag_bind(item, "<B1-Motion>", self.on_drag)
            self.canvas.tag_bind(item, "<ButtonRelease-1>", self.on_release)
            self.canvas.tag_bind(item, "<Double-Button-1>", self.on_double_click)
    
    def on_press(self, event):
        if self.tool and self.tool.is_panning:
            return
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y
        if self.tool:
            self.tool.deselect_all_visuals()
            self.tool.selected_item = self
            self.select()
    
    def on_drag(self, event):
        if self.tool and self.tool.is_panning:
            return
        dx = event.x - self.drag_data["x"]
        dy = event.y - self.drag_data["y"]
        if dx != 0 or dy != 0:
            self._was_dragged = True
        self.x += dx
        self.y += dy
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y
        self.canvas.move(self.box, dx, dy)
        self.canvas.move(self.text_item, dx, dy)
        if self.tool:
            self.tool.update_relationships()
    
    def on_release(self, event):
        if self.tool:
            self.tool.update_scroll_region()
            if hasattr(self, '_was_dragged') and self._was_dragged:
                self.tool.mark_as_changed()
                self._was_dragged = False
            self.tool.save_positions()
    
    def on_double_click(self, event):
        new_name = simpledialog.askstring("Edit Entity", "Enter entity name:", initialvalue=self.name)
        if new_name:
            self.name = new_name
            self.canvas.itemconfig(self.text_item, text=new_name)
            if self.tool:
                self.tool.mark_as_changed()
    
    def select(self):
        self.selected = True
        zoom_level = 1.0
        if self.tool and hasattr(self.tool, 'zoom_level'):
            zoom_level = self.tool.zoom_level
        self.canvas.itemconfig(self.box, outline="red", width=max(2, int(3 * zoom_level)))
    
    def deselect(self):
        self.selected = False
        zoom_level = 1.0
        if self.tool and hasattr(self.tool, 'zoom_level'):
            zoom_level = self.tool.zoom_level
        self.canvas.itemconfig(self.box, outline="black", width=max(1, int(2 * zoom_level)))

    def get_center(self):
        zoom_level = self.tool.zoom_level if self.tool and hasattr(self.tool, 'zoom_level') else 1.0
        return (self.x + (self.width * zoom_level) / 2, self.y + (self.height * zoom_level) / 2)

    def delete(self):
        self.canvas.delete(self.box)
        self.canvas.delete(self.text_item)


class FlowchartConnection:
    def __init__(self, canvas, from_node, to_node, conn_type="arrow", label="", tool=None):
        self.canvas = canvas
        self.tool = tool
        self.from_node = from_node
        self.to_node = to_node
        self.conn_type = conn_type
        self.label = label
        self.selected = False
        self.line = None
        self.label_text = None
        self.create_visual()

    def get_connection_points(self):
        return self.from_node.get_center(), self.to_node.get_center()

    def create_visual(self):
        from_point, to_point = self.get_connection_points()
        color = "red" if self.selected else "#2f3640"
        zoom_level = self.tool.zoom_level if self.tool and hasattr(self.tool, 'zoom_level') else 1.0
        width = max(1, int((3 if self.selected else 2) * zoom_level))
        dash = None
        arrow = None

        if self.conn_type == "dotted":
            dash = (6, 4)
            arrow = tk.LAST
        elif self.conn_type == "thick":
            width = max(2, int((4 if self.selected else 3) * zoom_level))
            arrow = tk.LAST
        elif self.conn_type == "line":
            arrow = None
        else:
            arrow = tk.LAST

        self.line = self.canvas.create_line(
            from_point[0], from_point[1], to_point[0], to_point[1],
            fill=color, width=width, dash=dash, arrow=arrow
        )
        self.canvas.tag_lower(self.line)
        if self.tool and self.canvas.find_withtag("grid"):
            self.canvas.tag_raise(self.line, "grid")
        self.canvas.tag_bind(self.line, "<Button-1>", self.on_click)
        self.canvas.tag_bind(self.line, "<Double-Button-1>", self.on_double_click)

        if self.label:
            mid_x, mid_y = get_perpendicular_label_position(from_point, to_point, int(12 * zoom_level))
            self.label_text = self.canvas.create_text(
                mid_x, mid_y, text=self.label,
                font=("Arial", max(8, int(9 * zoom_level))), fill="#0c2461"
            )
            place_text_near_line(
                self.canvas,
                self.label_text,
                from_point,
                to_point,
                [
                    self.canvas.bbox(self.from_node.shape_item),
                    self.canvas.bbox(self.to_node.shape_item),
                ],
                preferred_side=1,
                base_offset=int(12 * zoom_level),
                padding=2,
            )
            self.canvas.tag_lower(self.label_text)
            self.canvas.tag_bind(self.label_text, "<Button-1>", self.on_click)
            self.canvas.tag_bind(self.label_text, "<Double-Button-1>", self.on_double_click)

    def update_position(self):
        self.delete()
        self.create_visual()

    def on_click(self, event):
        if self.tool:
            self.tool.deselect_all_visuals()
        self.select()
        return "break"

    def on_double_click(self, event):
        new_label = simpledialog.askstring("Connection Label", "Enter connection label:", initialvalue=self.label)
        if new_label is not None:
            self.label = new_label
            self.update_position()
            if self.tool:
                self.tool.mark_as_changed()
        return "break"

    def select(self):
        self.selected = True
        self.update_position()
        if self.tool:
            self.tool.update_status(f"Selected flowchart connection: {self.from_node.node_id} -> {self.to_node.node_id}")

    def deselect(self):
        self.selected = False
        self.update_position()

    def delete(self):
        if self.line:
            self.canvas.delete(self.line)
        if self.label_text:
            self.canvas.delete(self.label_text)
        self.line = None
        self.label_text = None


class SequenceMessage:
    def __init__(self, canvas, from_actor, to_actor, msg_type="sync", label="", index=0, tool=None):
        self.canvas = canvas
        self.tool = tool
        self.from_actor = from_actor
        self.to_actor = to_actor
        self.msg_type = msg_type
        self.label = label or "message"
        self.index = index
        self.selected = False
        self.line = None
        self.label_text = None
        self.create_visual()

    def get_y(self):
        zoom_level = self.tool.zoom_level if self.tool and hasattr(self.tool, 'zoom_level') else 1.0
        top = max(self.from_actor.y + self.from_actor.height * zoom_level, self.to_actor.y + self.to_actor.height * zoom_level)
        return top + ((self.index + 1) * 50 * zoom_level)

    def create_visual(self):
        zoom_level = self.tool.zoom_level if self.tool and hasattr(self.tool, 'zoom_level') else 1.0
        from_x = self.from_actor.get_center()[0]
        to_x = self.to_actor.get_center()[0]
        y = self.get_y()
        color = "red" if self.selected else "#2d3436"
        width = max(1, int((3 if self.selected else 2) * zoom_level))
        dash = None
        arrow = tk.LAST

        if self.msg_type == "return":
            dash = (6, 4)
        elif self.msg_type == "note":
            dash = (2, 4)
            arrow = None
        elif self.msg_type == "async":
            arrow = tk.LAST

        self.line = self.canvas.create_line(from_x, y, to_x, y, fill=color, width=width, dash=dash, arrow=arrow)
        self.canvas.tag_lower(self.line)
        if self.tool and self.canvas.find_withtag("grid"):
            self.canvas.tag_raise(self.line, "grid")
        self.canvas.tag_bind(self.line, "<Button-1>", self.on_click)
        self.canvas.tag_bind(self.line, "<Double-Button-1>", self.on_double_click)

        label_fill = "#6c5ce7" if self.msg_type != "note" else "#b9770e"
        self.label_text = self.canvas.create_text(
            (from_x + to_x) / 2, y - (12 * zoom_level), text=self.label,
            font=("Arial", max(8, int(9 * zoom_level))), fill=label_fill
        )
        self.canvas.tag_lower(self.label_text)
        self.canvas.tag_bind(self.label_text, "<Button-1>", self.on_click)
        self.canvas.tag_bind(self.label_text, "<Double-Button-1>", self.on_double_click)

    def update_position(self):
        self.delete()
        self.create_visual()

    def on_click(self, event):
        if self.tool:
            self.tool.deselect_all_visuals()
        self.select()
        return "break"

    def on_double_click(self, event):
        new_label = simpledialog.askstring("Message Label", "Enter message label:", initialvalue=self.label)
        if new_label is not None:
            self.label = new_label
            self.update_position()
            if self.tool:
                self.tool.mark_as_changed()
        return "break"

    def select(self):
        self.selected = True
        self.update_position()
        if self.tool:
            self.tool.update_status(f"Selected sequence message: {self.from_actor.name} -> {self.to_actor.name}")

    def deselect(self):
        self.selected = False
        self.update_position()

    def delete(self):
        if self.line:
            self.canvas.delete(self.line)
        if self.label_text:
            self.canvas.delete(self.label_text)
        self.line = None
        self.label_text = None


class StateTransition:
    def __init__(self, canvas, from_state, to_state, label="", tool=None):
        self.canvas = canvas
        self.tool = tool
        self.from_state = from_state
        self.to_state = to_state
        self.label = label
        self.selected = False
        self.line = None
        self.label_text = None
        self.create_visual()

    def get_label_side(self):
        """Split labels for reverse transitions onto opposite sides of the shared path."""
        from_name = getattr(self.from_state, "name", "")
        to_name = getattr(self.to_state, "name", "")
        return 1 if from_name <= to_name else -1

    def create_visual(self):
        zoom_level = self.tool.zoom_level if self.tool and hasattr(self.tool, 'zoom_level') else 1.0
        from_point = self.from_state.get_center()
        to_point = self.to_state.get_center()
        color = "red" if self.selected else "#1e8449"
        width = max(1, int((3 if self.selected else 2) * zoom_level))

        self.line = self.canvas.create_line(
            from_point[0], from_point[1], to_point[0], to_point[1],
            fill=color, width=width, arrow=tk.LAST, smooth=True
        )
        self.canvas.tag_lower(self.line)
        if self.tool and self.canvas.find_withtag("grid"):
            self.canvas.tag_raise(self.line, "grid")
        self.canvas.tag_bind(self.line, "<Button-1>", self.on_click)
        self.canvas.tag_bind(self.line, "<Double-Button-1>", self.on_double_click)

        if self.label:
            label_side = self.get_label_side()
            label_x, label_y = get_perpendicular_label_position(
                from_point, to_point, int(12 * zoom_level), side=label_side
            )
            self.label_text = self.canvas.create_text(
                label_x,
                label_y,
                text=self.label,
                font=("Arial", max(8, int(9 * zoom_level))), fill="#145a32"
            )
            place_text_near_line(
                self.canvas,
                self.label_text,
                from_point,
                to_point,
                [
                    self.canvas.bbox(state.box)
                    for state in self.tool.state_nodes
                ] if self.tool else [
                    self.canvas.bbox(self.from_state.box),
                    self.canvas.bbox(self.to_state.box),
                ],
                preferred_side=label_side,
                base_offset=int(12 * zoom_level),
                padding=2,
            )
            self.canvas.tag_lower(self.label_text)
            self.canvas.tag_bind(self.label_text, "<Button-1>", self.on_click)
            self.canvas.tag_bind(self.label_text, "<Double-Button-1>", self.on_double_click)

    def update_position(self):
        self.delete()
        self.create_visual()

    def on_click(self, event):
        if self.tool:
            self.tool.deselect_all_visuals()
        self.select()
        return "break"

    def on_double_click(self, event):
        new_label = simpledialog.askstring("Transition Label", "Enter transition label:", initialvalue=self.label)
        if new_label is not None:
            self.label = new_label
            self.update_position()
            if self.tool:
                self.tool.mark_as_changed()
        return "break"

    def select(self):
        self.selected = True
        self.update_position()
        if self.tool:
            self.tool.update_status(f"Selected state transition: {self.from_state.name} -> {self.to_state.name}")

    def deselect(self):
        self.selected = False
        self.update_position()

    def delete(self):
        if self.line:
            self.canvas.delete(self.line)
        if self.label_text:
            self.canvas.delete(self.label_text)
        self.line = None
        self.label_text = None


class ERRelationship:
    def __init__(self, canvas, from_entity, to_entity, rel_type="one-to-many", label="", tool=None):
        self.canvas = canvas
        self.tool = tool
        self.from_entity = from_entity
        self.to_entity = to_entity
        self.rel_type = rel_type
        self.label = label
        self.selected = False
        self.line = None
        self.label_text = None
        self.from_card_text = None
        self.to_card_text = None
        self.create_visual()

    def cardinalities(self):
        if self.rel_type == "one-to-one":
            return "1", "1"
        if self.rel_type == "many-to-many":
            return "N", "N"
        return "1", "N"

    def create_visual(self):
        zoom_level = self.tool.zoom_level if self.tool and hasattr(self.tool, 'zoom_level') else 1.0
        from_rect = {
            'left': self.from_entity.x,
            'right': self.from_entity.x + (self.from_entity.width * zoom_level),
            'top': self.from_entity.y,
            'bottom': self.from_entity.y + (self.from_entity.height * zoom_level)
        }
        to_rect = {
            'left': self.to_entity.x,
            'right': self.to_entity.x + (self.to_entity.width * zoom_level),
            'top': self.to_entity.y,
            'bottom': self.to_entity.y + (self.to_entity.height * zoom_level)
        }
        from_point, to_point = get_box_connection_points(from_rect, to_rect)
        color = "red" if self.selected else "#8e5a2b"
        width = max(1, int((3 if self.selected else 2) * zoom_level))

        self.line = self.canvas.create_line(
            from_point[0], from_point[1], to_point[0], to_point[1],
            fill=color, width=width
        )
        self.canvas.tag_lower(self.line)
        if self.tool and self.canvas.find_withtag("grid"):
            self.canvas.tag_raise(self.line, "grid")
        self.canvas.tag_bind(self.line, "<Button-1>", self.on_click)
        self.canvas.tag_bind(self.line, "<Double-Button-1>", self.on_double_click)

        from_card, to_card = self.cardinalities()
        from_card_x, from_card_y = get_outside_box_label_position(
            self.from_entity.get_center(), from_point, to_point, int(18 * zoom_level), int(10 * zoom_level)
        )
        to_card_x, to_card_y = get_outside_box_label_position(
            self.to_entity.get_center(), to_point, from_point, int(18 * zoom_level), int(10 * zoom_level)
        )
        self.from_card_text = self.canvas.create_text(
            from_card_x, from_card_y,
            text=from_card, font=("Arial", max(8, int(9 * zoom_level)), "bold"), fill="#784212"
        )
        self.to_card_text = self.canvas.create_text(
            to_card_x, to_card_y,
            text=to_card, font=("Arial", max(8, int(9 * zoom_level)), "bold"), fill="#784212"
        )
        for item in [self.from_card_text, self.to_card_text]:
            self.canvas.tag_raise(item)
            self.canvas.tag_bind(item, "<Button-1>", self.on_click)
            self.canvas.tag_bind(item, "<Double-Button-1>", self.on_double_click)

        if self.label:
            label_x, label_y = get_perpendicular_label_position(from_point, to_point, int(12 * zoom_level))
            self.label_text = self.canvas.create_text(
                label_x,
                label_y,
                text=self.label,
                font=("Arial", max(8, int(9 * zoom_level))), fill="#935116"
            )
            place_text_near_line(
                self.canvas,
                self.label_text,
                from_point,
                to_point,
                [
                    self.canvas.bbox(entity.box)
                    for entity in self.tool.er_entities
                ] if self.tool else [
                    self.canvas.bbox(self.from_entity.box),
                    self.canvas.bbox(self.to_entity.box),
                ],
                preferred_side=1,
                base_offset=int(12 * zoom_level),
                padding=2,
            )
            self.canvas.tag_raise(self.label_text)
            self.canvas.tag_bind(self.label_text, "<Button-1>", self.on_click)
            self.canvas.tag_bind(self.label_text, "<Double-Button-1>", self.on_double_click)

    def update_position(self):
        self.delete()
        self.create_visual()

    def on_click(self, event):
        if self.tool:
            self.tool.deselect_all_visuals()
        self.select()
        return "break"

    def on_double_click(self, event):
        new_label = simpledialog.askstring("Relationship Label", "Enter relationship label:", initialvalue=self.label)
        if new_label is not None:
            self.label = new_label
            self.update_position()
            if self.tool:
                self.tool.mark_as_changed()
        return "break"

    def select(self):
        self.selected = True
        self.update_position()
        if self.tool:
            self.tool.update_status(f"Selected ER relationship: {self.from_entity.name} -> {self.to_entity.name}")

    def deselect(self):
        self.selected = False
        self.update_position()

    def delete(self):
        for item_name in ["line", "label_text", "from_card_text", "to_card_text"]:
            item = getattr(self, item_name, None)
            if item:
                self.canvas.delete(item)
                setattr(self, item_name, None)

class MermaidDiagramTool:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Mermaid Diagram Tool")
        self.root.geometry("1440x900")
        self.root.minsize(1280, 780)
        
        self.diagram_type = "classDiagram"  # or "flowchart", "sequenceDiagram", "stateDiagram", "erDiagram"
        self.classes = []
        self.flowchart_nodes = []  # For flowchart mode
        self.flowchart_connections = []
        self.sequence_actors = []  # For sequence diagram
        self.sequence_messages = []  # For sequence diagram
        self.state_nodes = []  # For state diagram
        self.state_transitions = []  # For state diagram
        self.er_entities = []  # For ER diagram
        self.er_relationships = []  # For ER diagram
        self.relationships = []
        self.selected_class = None
        self.selected_node = None  # For flowchart mode
        self.selected_item = None  # Generic selection for other diagram types
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
        self.debug_logging = False
        
        self.create_widgets()
        self.update_diagram_type_ui()
        
        # Set up window close handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Load last used diagram
        self.load_last_diagram()
        
    def create_widgets(self):
        self.root.configure(bg="#f3f6fb")
        self.configure_ttk_styles()

        # Menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New", command=self.new_diagram)
        file_menu.add_command(label="Open Mermaid", command=self.open_mermaid)
        file_menu.add_command(label="Save Mermaid", command=self.save_mermaid)
        
        app_shell = tk.Frame(self.root, bg="#f3f6fb")
        app_shell.pack(fill=tk.BOTH, expand=True, padx=14, pady=14)

        header = tk.Frame(app_shell, bg="#f3f6fb")
        header.pack(fill=tk.X, pady=(0, 12))

        brand_frame = tk.Frame(header, bg="#f3f6fb")
        brand_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(
            brand_frame,
            text="Mermaid Diagram Studio",
            bg="#f3f6fb",
            fg="#132238",
            font=("Segoe UI Semibold", 16),
        ).pack(anchor=tk.W)
        tk.Label(
            brand_frame,
            text="Visual editing with live Mermaid output, modeled after the code-plus-preview rhythm of the official Mermaid editors.",
            bg="#f3f6fb",
            fg="#5b6b80",
            font=("Segoe UI", 9),
            wraplength=700,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(2, 0))

        document_card = tk.Frame(
            header,
            bg="#ffffff",
            highlightthickness=1,
            highlightbackground="#d8e1ed",
            padx=14,
            pady=10,
        )
        document_card.pack(side=tk.RIGHT, padx=(16, 0))
        tk.Label(
            document_card,
            text="Current file",
            bg="#ffffff",
            fg="#66758a",
            font=("Segoe UI", 8, "bold"),
        ).pack(anchor=tk.W)
        self.document_label = tk.Label(
            document_card,
            text="Untitled diagram",
            bg="#ffffff",
            fg="#132238",
            font=("Segoe UI Semibold", 10),
        )
        self.document_label.pack(anchor=tk.W, pady=(2, 0))
        self.document_meta_label = tk.Label(
            document_card,
            text="Saved",
            bg="#ffffff",
            fg="#4b6584",
            font=("Segoe UI", 8),
        )
        self.document_meta_label.pack(anchor=tk.W, pady=(2, 0))

        toolbar = tk.Frame(
            app_shell,
            bg="#ffffff",
            highlightthickness=1,
            highlightbackground="#d8e1ed",
            padx=12,
            pady=12,
        )
        toolbar.pack(fill=tk.X, pady=(0, 12))
        self.toolbar = toolbar

        file_tools = self.create_control_group(toolbar, "Diagram")
        mode_tools = self.create_control_group(toolbar, "Edit")
        connector_tools = self.create_control_group(toolbar, "Connector")
        zoom_tools = self.create_control_group(toolbar, "View")

        self.diagram_type_var = tk.StringVar(value="classDiagram")
        type_combo = ttk.Combobox(
            file_tools,
            textvariable=self.diagram_type_var,
            values=["classDiagram", "flowchart", "sequenceDiagram", "stateDiagram", "erDiagram"],
            state="readonly",
            width=14,
            style="Friendly.TCombobox",
        )
        type_combo.pack(side=tk.LEFT, padx=(0, 8), pady=2)
        type_combo.bind("<<ComboboxSelected>>", self.on_diagram_type_changed)

        self.new_button = tk.Button(file_tools, text="New", command=self.new_diagram, width=7)
        self.new_button.pack(side=tk.LEFT, padx=3, pady=2)
        self.open_button = tk.Button(file_tools, text="Open", command=self.open_mermaid, width=7)
        self.open_button.pack(side=tk.LEFT, padx=3, pady=2)
        self.save_button = tk.Button(file_tools, text="Save", command=self.save_mermaid, width=7)
        self.save_button.pack(side=tk.LEFT, padx=3, pady=2)

        self.add_button = tk.Button(mode_tools, text="Add Class", command=self.add_primary_element, width=11)
        self.add_button.pack(side=tk.LEFT, padx=3, pady=2)
        self.delete_button = tk.Button(mode_tools, text="Delete", command=self.delete_selected, width=10)
        self.delete_button.pack(side=tk.LEFT, padx=3, pady=2)
        self.layout_button = tk.Button(mode_tools, text="Layout", command=self.apply_hierarchical_layout, width=9)
        self.layout_button.pack(side=tk.LEFT, padx=3, pady=2)

        self.connection_label = tk.Label(
            connector_tools,
            text="Connector:",
            bg="#f7f9fc",
            fg="#243447",
            font=("Segoe UI", 9, "bold"),
        )
        self.connection_label.pack(side=tk.LEFT, padx=(0, 6), pady=2)

        self.rel_type_var = tk.StringVar(value="association")
        rel_combo = ttk.Combobox(
            connector_tools,
            textvariable=self.rel_type_var,
            values=["association", "inheritance", "composition", "aggregation", "dependency", "realization"],
            state="readonly",
            width=14,
            style="Friendly.TCombobox",
        )
        rel_combo.pack(side=tk.LEFT, padx=(0, 8), pady=2)
        rel_combo.bind("<<ComboboxSelected>>", self.on_relationship_type_changed)
        self.rel_combo = rel_combo

        self.rel_button = tk.Button(connector_tools, text="Draw", command=self.toggle_relationship_mode, width=9)
        self.rel_button.pack(side=tk.LEFT, padx=3, pady=2)

        tk.Label(
            zoom_tools,
            text="Zoom",
            bg="#f7f9fc",
            fg="#243447",
            font=("Segoe UI", 9, "bold"),
        ).pack(side=tk.LEFT, padx=(0, 6), pady=2)
        self.zoom_out_button = tk.Button(zoom_tools, text="-", command=self.zoom_out, width=3)
        self.zoom_out_button.pack(side=tk.LEFT, padx=2, pady=2)
        self.zoom_label = tk.Label(
            zoom_tools,
            text="100%",
            bg="#f7f9fc",
            width=4,
            fg="#243447",
            font=("Segoe UI Semibold", 9),
        )
        self.zoom_label.pack(side=tk.LEFT, padx=2, pady=2)
        self.zoom_in_button = tk.Button(zoom_tools, text="+", command=self.zoom_in, width=3)
        self.zoom_in_button.pack(side=tk.LEFT, padx=2, pady=2)
        self.zoom_reset_button = tk.Button(zoom_tools, text="1:1", command=self.zoom_reset, width=4)
        self.zoom_reset_button.pack(side=tk.LEFT, padx=(2, 8), pady=2)

        self.show_grid = tk.BooleanVar(value=False)
        self.grid_check = tk.Checkbutton(
            zoom_tools,
            text="Grid",
            variable=self.show_grid,
            command=self.toggle_grid,
            bg="#f7f9fc",
            activebackground="#f7f9fc",
            fg="#243447",
            font=("Segoe UI", 9),
            cursor="hand2",
        )
        self.grid_check.pack(side=tk.LEFT, padx=(0, 2), pady=2)

        summary_card = tk.Frame(
            app_shell,
            bg="#ffffff",
            highlightthickness=1,
            highlightbackground="#d8e1ed",
            padx=14,
            pady=10,
        )
        summary_card.pack(fill=tk.X, pady=(0, 12))
        self.summary_label = tk.Label(
            summary_card,
            text="",
            bg="#ffffff",
            fg="#17324d",
            anchor=tk.W,
            font=("Segoe UI Semibold", 10),
        )
        self.summary_label.pack(side=tk.TOP, fill=tk.X)
        self.mode_hint_label = tk.Label(
            summary_card,
            text="",
            bg="#ffffff",
            fg="#607186",
            anchor=tk.W,
            font=("Segoe UI", 9),
            wraplength=1200,
            justify=tk.LEFT,
        )
        self.mode_hint_label.pack(side=tk.TOP, fill=tk.X, pady=(4, 0))

        content_frame = tk.Frame(app_shell, bg="#f3f6fb")
        content_frame.pack(fill=tk.BOTH, expand=True)

        palette_shell = tk.Frame(
            content_frame,
            bg="#ffffff",
            width=198,
            highlightthickness=1,
            highlightbackground="#d8e1ed",
        )
        palette_shell.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12))
        palette_shell.pack_propagate(False)
        tk.Label(
            palette_shell,
            text="Tools",
            bg="#ffffff",
            fg="#132238",
            font=("Segoe UI Semibold", 11),
        ).pack(anchor=tk.W, padx=14, pady=(14, 2))
        tk.Label(
            palette_shell,
            text="Pick shapes or relationships, then place them on the canvas.",
            bg="#ffffff",
            fg="#647488",
            font=("Segoe UI", 8),
            wraplength=166,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, padx=14, pady=(0, 10))

        self.shape_palette = tk.Frame(palette_shell, bg="#ffffff", bd=0, highlightthickness=0)
        self.shape_palette.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.create_shape_palette()

        center_column = tk.Frame(content_frame, bg="#f3f6fb")
        center_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        canvas_card = tk.Frame(
            center_column,
            bg="#ffffff",
            highlightthickness=1,
            highlightbackground="#d8e1ed",
        )
        canvas_card.pack(fill=tk.BOTH, expand=True)

        canvas_header = tk.Frame(canvas_card, bg="#ffffff")
        canvas_header.pack(fill=tk.X, padx=14, pady=(14, 8))
        self.canvas_title_label = tk.Label(
            canvas_header,
            text="Canvas",
            bg="#ffffff",
            fg="#132238",
            font=("Segoe UI Semibold", 12),
        )
        self.canvas_title_label.pack(side=tk.LEFT)
        self.canvas_meta_label = tk.Label(
            canvas_header,
            text="",
            bg="#ffffff",
            fg="#5f7084",
            font=("Segoe UI", 9),
        )
        self.canvas_meta_label.pack(side=tk.RIGHT)

        self.info_banner = tk.Label(
            canvas_card,
            text="",
            bg="#eef5ff",
            fg="#1e3a5f",
            anchor=tk.W,
            padx=12,
            pady=9,
            relief=tk.FLAT,
            bd=0,
        )
        self.info_banner.pack(fill=tk.X, padx=14)

        canvas_frame = tk.Frame(canvas_card, bg="#ffffff")
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=14, pady=14)
        
        self.canvas = tk.Canvas(canvas_frame, bg="#fbfdff", highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        v_scrollbar = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.on_v_scroll)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=self.on_canvas_y_scroll)

        h_scrollbar = tk.Scrollbar(canvas_card, orient=tk.HORIZONTAL, command=self.on_h_scroll)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X, padx=14, pady=(0, 14))
        self.canvas.configure(xscrollcommand=self.on_canvas_x_scroll)

        self.v_scrollbar = v_scrollbar
        self.h_scrollbar = h_scrollbar

        preview_panel = tk.Frame(
            content_frame,
            bg="#ffffff",
            width=350,
            highlightthickness=1,
            highlightbackground="#d8e1ed",
        )
        preview_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(12, 0))
        preview_panel.pack_propagate(False)

        tk.Label(
            preview_panel,
            text="Live Mermaid",
            bg="#ffffff",
            fg="#132238",
            font=("Segoe UI Semibold", 11),
        ).pack(anchor=tk.W, padx=14, pady=(14, 2))
        tk.Label(
            preview_panel,
            text="The official Mermaid Live Editor keeps code next to preview. This pane mirrors that workflow while you edit visually.",
            bg="#ffffff",
            fg="#647488",
            font=("Segoe UI", 8),
            wraplength=310,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, padx=14, pady=(0, 10))

        action_row = tk.Frame(preview_panel, bg="#ffffff")
        action_row.pack(fill=tk.X, padx=14, pady=(0, 10))
        self.copy_code_button = tk.Button(action_row, text="Copy Code", command=self.copy_mermaid_code, width=11)
        self.copy_code_button.pack(side=tk.LEFT, padx=(0, 6))
        self.refresh_code_button = tk.Button(action_row, text="Refresh", command=self.refresh_code_preview, width=9)
        self.refresh_code_button.pack(side=tk.LEFT)

        self.code_meta_label = tk.Label(
            preview_panel,
            text="",
            bg="#ffffff",
            fg="#4c647d",
            font=("Segoe UI", 8),
        )
        self.code_meta_label.pack(anchor=tk.W, padx=14, pady=(0, 6))

        code_frame = tk.Frame(preview_panel, bg="#ffffff")
        code_frame.pack(fill=tk.BOTH, expand=True, padx=14)
        code_scroll = tk.Scrollbar(code_frame, orient=tk.VERTICAL)
        code_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        code_x_scroll = tk.Scrollbar(code_frame, orient=tk.HORIZONTAL)
        code_x_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.code_preview = tk.Text(
            code_frame,
            wrap=tk.NONE,
            state=tk.DISABLED,
            bg="#0f1724",
            fg="#dfe8f3",
            insertbackground="#dfe8f3",
            font=("Consolas", 10),
            padx=10,
            pady=10,
            relief=tk.FLAT,
            bd=0,
            yscrollcommand=code_scroll.set,
            xscrollcommand=code_x_scroll.set,
        )
        self.code_preview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        code_scroll.config(command=self.code_preview.yview)
        code_x_scroll.config(command=self.code_preview.xview)

        samples_panel = tk.Frame(
            preview_panel,
            bg="#f7f9fc",
            highlightthickness=1,
            highlightbackground="#dfe7f2",
            padx=12,
            pady=12,
        )
        samples_panel.pack(fill=tk.X, padx=14, pady=(0, 10), before=code_frame)
        tk.Label(
            samples_panel,
            text="Sample diagrams",
            bg="#f7f9fc",
            fg="#132238",
            font=("Segoe UI Semibold", 10),
        ).pack(anchor=tk.W)
        tk.Label(
            samples_panel,
            text="Mermaid Live Editor ships sample diagrams. These local files give this desktop tool the same fast starting point.",
            bg="#f7f9fc",
            fg="#647488",
            font=("Segoe UI", 8),
            wraplength=286,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(4, 8))
        self.sample_map = {
            "Class sample": "sample_class_diagram.md",
            "Flowchart sample": "sample_flowchart.md",
            "Sequence sample": "sample_sequence_diagram.md",
            "State sample": "sample_state_diagram.md",
            "ER sample": "sample_er_diagram.md",
        }
        sample_picker_row = tk.Frame(samples_panel, bg="#f7f9fc")
        sample_picker_row.pack(fill=tk.X)
        self.sample_choice_var = tk.StringVar(value="Class sample")
        self.sample_combo = ttk.Combobox(
            sample_picker_row,
            textvariable=self.sample_choice_var,
            values=list(self.sample_map.keys()),
            state="readonly",
            width=18,
            style="Friendly.TCombobox",
        )
        self.sample_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.sample_load_button = tk.Button(
            sample_picker_row,
            text="Load",
            command=self.load_selected_sample,
            width=8,
        )
        self.sample_load_button.pack(side=tk.RIGHT)
        
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
        self.canvas.bind("<Configure>", self.on_canvas_configure)  # Redraw grid on resize/scroll
        
        # Status bar
        self.status_bar = tk.Label(
            app_shell,
            text="Ready",
            bd=0,
            relief=tk.FLAT,
            anchor=tk.W,
            bg="#e8eef7",
            fg="#30465f",
            padx=12,
            pady=7,
            font=("Segoe UI", 9),
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X, pady=(12, 0))
        
        # Bind keyboard events
        self.root.bind("<Key>", self.on_key_press)
        self.root.focus_set()  # Make sure root can receive key events
        self.current_status_message = "Ready"
        self.apply_button_styles()
        self.refresh_ui_feedback()

    def create_control_group(self, parent, title):
        frame = tk.Frame(
            parent,
            bg="#f7f9fc",
            highlightthickness=1,
            highlightbackground="#dfe7f2",
            padx=10,
            pady=8,
        )
        frame.pack(side=tk.LEFT, padx=(0, 10))
        tk.Label(
            frame,
            text=title,
            bg="#f7f9fc",
            fg="#617386",
            font=("Segoe UI", 8, "bold"),
        ).pack(anchor=tk.W, pady=(0, 6))
        body = tk.Frame(frame, bg="#f7f9fc")
        body.pack(anchor=tk.W)
        return body
    
    def create_shape_palette(self):
        """Create the shape palette with visual buttons"""
        # Container for palette content that can be switched
        self.palette_content = tk.Frame(self.shape_palette, bg="#ffffff")
        self.palette_content.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        # Initially create flowchart palette (will be hidden)
        self.create_flowchart_palette()

    def configure_ttk_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "Friendly.TCombobox",
            fieldbackground="#ffffff",
            background="#ffffff",
            bordercolor="#c6d3e1",
            lightcolor="#c6d3e1",
            darkcolor="#c6d3e1",
            arrowsize=14,
            padding=6,
            foreground="#132238",
            insertcolor="#132238",
        )
        style.map(
            "Friendly.TCombobox",
            fieldbackground=[("readonly", "#ffffff")],
            background=[("readonly", "#ffffff")],
            foreground=[("readonly", "#132238")],
        )

    def apply_button_styles(self):
        button_specs = [
            (self.new_button, "subtle"),
            (self.open_button, "subtle"),
            (self.save_button, "primary"),
            (self.add_button, "primary"),
            (self.delete_button, "warning"),
            (self.layout_button, "accent"),
            (self.rel_button, "neutral"),
            (self.zoom_out_button, "subtle"),
            (self.zoom_in_button, "subtle"),
            (self.zoom_reset_button, "subtle"),
            (self.copy_code_button, "neutral"),
            (self.refresh_code_button, "subtle"),
            (self.sample_load_button, "ghost"),
        ]
        for button, variant in button_specs:
            self.style_button(button, variant)

    def style_button(self, button, variant="neutral", compact=False):
        palette = {
            "primary": ("#2f6fed", "#265ac0", "#2f6fed", "#ffffff"),
            "accent": ("#d6f5ea", "#c0eadb", "#7bc8a4", "#1b4332"),
            "warning": ("#fde6b1", "#f8d777", "#efc14a", "#5f4300"),
            "neutral": ("#e8eef7", "#d7e2f0", "#c3d3e6", "#17324d"),
            "subtle": ("#ffffff", "#f0f4f9", "#d1ddea", "#17324d"),
            "ghost": ("#f7f9fc", "#eef3f8", "#d8e1ed", "#17324d"),
        }
        background, active_background, border, foreground = palette.get(variant, palette["neutral"])
        button.config(
            relief=tk.FLAT,
            bd=0,
            padx=10 if compact else 12,
            pady=6 if compact else 7,
            bg=background,
            fg=foreground,
            activebackground=active_background,
            activeforeground=foreground,
            highlightthickness=1,
            highlightbackground=border,
            highlightcolor=border,
            font=("Segoe UI", 8 if compact else 9, "bold"),
            cursor="hand2",
        )

    def refresh_code_preview(self):
        if not hasattr(self, "code_preview"):
            return

        try:
            mermaid_code = self.generate_mermaid()
            line_count = len(mermaid_code.splitlines())
            preview_text = mermaid_code
            if hasattr(self, "code_meta_label"):
                self.code_meta_label.config(
                    text=f"{self.get_diagram_display_name()} · {line_count} line{'s' if line_count != 1 else ''}"
                )
        except Exception as exc:
            preview_text = f"# Mermaid preview unavailable\n# {exc}"
            if hasattr(self, "code_meta_label"):
                self.code_meta_label.config(text="Preview unavailable")

        self.code_preview.config(state=tk.NORMAL)
        self.code_preview.delete("1.0", tk.END)
        self.code_preview.insert("1.0", preview_text)
        self.code_preview.config(state=tk.DISABLED)

    def copy_mermaid_code(self):
        try:
            mermaid_code = self.generate_mermaid()
        except Exception as exc:
            messagebox.showerror("Copy Mermaid Code", f"Could not generate Mermaid code: {exc}")
            return

        self.root.clipboard_clear()
        self.root.clipboard_append(mermaid_code)
        self.update_status("Copied Mermaid code to clipboard")

    def load_sample_diagram(self, sample_file):
        sample_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), sample_file)
        if not os.path.exists(sample_path):
            messagebox.showerror("Sample Diagram", f"Could not find sample file:\n{sample_file}")
            return
        self.load_diagram_from_file(sample_path, prompt_for_unsaved=True, show_errors=True)

    def load_selected_sample(self):
        if not hasattr(self, "sample_map"):
            return
        sample_file = self.sample_map.get(self.sample_choice_var.get())
        if sample_file:
            self.load_sample_diagram(sample_file)

    def create_palette_section_header(self, title, subtitle=None):
        tk.Label(
            self.palette_content,
            text=title,
            bg="#ffffff",
            fg="#132238",
            font=("Segoe UI Semibold", 11),
        ).pack(pady=(2, 4))
        if subtitle:
            tk.Label(
                self.palette_content,
                text=subtitle,
                bg="#ffffff",
                fg="#647488",
                font=("Segoe UI", 8),
                wraplength=138,
                justify=tk.LEFT,
            ).pack(pady=(0, 8))

    def create_palette_card(self, width=116, height=56):
        frame = tk.Frame(self.palette_content, bg="#ffffff")
        frame.pack(pady=4, padx=2, fill=tk.X)
        canvas = tk.Canvas(
            frame,
            width=width,
            height=height,
            bg="#f8fbff",
            highlightthickness=1,
            highlightbackground="#d8e1ed",
            relief=tk.FLAT,
            bd=0,
        )
        canvas.pack()
        canvas.config(cursor="hand2")
        return frame, canvas

    def add_palette_item_label(self, parent, label):
        tk.Label(parent, text=label, bg="#ffffff", fg="#243447", font=("Segoe UI", 8)).pack(pady=(4, 0))

    def update_palette_hint(self, text):
        if hasattr(self, "palette_hint_label") and self.palette_hint_label.winfo_exists():
            self.palette_hint_label.destroy()
        self.palette_hint_label = tk.Label(
            self.palette_content,
            text=text,
            bg="#ffffff",
            fg="#6c7a89",
            font=("Segoe UI", 8),
            wraplength=136,
            justify=tk.LEFT,
        )
        self.palette_hint_label.pack(side=tk.BOTTOM, pady=(10, 2))
        
    def create_flowchart_palette(self):
        """Create flowchart shape palette"""
        # Clear existing content
        for widget in self.palette_content.winfo_children():
            widget.destroy()
        
        self.create_palette_section_header("Flowchart", "Pick a shape, then click the canvas to arrange the flow.")
        tk.Label(self.palette_content, text="Shapes", bg="#ffffff", fg="#576574", font=("Segoe UI", 9, "bold")).pack(pady=(2, 4))
        
        # Create canvas buttons for each shape
        shapes = [
            ("rectangle", "Rectangle", "lightblue"),
            ("rounded", "Rounded", "lightgreen"),
            ("diamond", "Diamond", "lightyellow"),
            ("circle", "Circle", "lightcoral")
        ]
        
        for shape_type, label, color in shapes:
            frame, icon_canvas = self.create_palette_card(height=44)
            
            # Draw the shape icon
            if shape_type == "rectangle":
                icon_canvas.create_rectangle(18, 10, 98, 34, fill=color, outline="black", width=2)
            elif shape_type == "rounded":
                icon_canvas.create_rectangle(18, 10, 98, 34, fill=color, outline="black", width=2)
                icon_canvas.create_oval(16, 8, 24, 16, fill=color, outline="black", width=1)
                icon_canvas.create_oval(92, 8, 100, 16, fill=color, outline="black", width=1)
            elif shape_type == "diamond":
                icon_canvas.create_polygon(58, 8, 102, 22, 58, 36, 14, 22, fill=color, outline="black", width=2)
            elif shape_type == "circle":
                icon_canvas.create_oval(28, 8, 88, 36, fill=color, outline="black", width=2)
            
            self.add_palette_item_label(frame, label)
            
            # Bind click event
            icon_canvas.bind("<Button-1>", lambda e, s=shape_type: self.add_shape_from_palette(s))
        self.update_palette_hint("Tip: right-click empty space to add a default node quickly.")
    
    def create_uml_palette(self):
        """Create UML class diagram palette"""
        # Clear existing content
        for widget in self.palette_content.winfo_children():
            widget.destroy()
        
        self.create_palette_section_header("UML Class", "Add classes and pick a relationship type before drawing links.")
        
        # Add Class button
        class_frame, class_canvas = self.create_palette_card(height=62)
        
        # Draw class icon
        class_canvas.create_rectangle(18, 6, 98, 46, fill="lightyellow", outline="black", width=2)
        class_canvas.create_line(18, 20, 98, 20, fill="black", width=1)
        class_canvas.create_text(58, 13, text="Class", font=("Arial", 8, "bold"))
        class_canvas.create_text(58, 33, text="+ attr\n+ method()", font=("Arial", 6))
        
        self.add_palette_item_label(class_frame, "Class")
        class_canvas.bind("<Button-1>", lambda e: self.add_class())
        
        # Relationships section
        tk.Label(self.palette_content, text="Relationships", bg="#ffffff", fg="#576574", font=("Segoe UI", 9, "bold")).pack(pady=(10, 4))
        
        relationships = [
            ("association", "Association", "black", "solid", None),
            ("inheritance", "Inheritance", "black", "solid", "triangle"),
            ("composition", "Composition", "black", "solid", "diamond_filled"),
            ("aggregation", "Aggregation", "black", "solid", "diamond_empty"),
            ("dependency", "Dependency", "black", "dash", "arrow"),
            ("realization", "Realization", "black", "dash", "triangle")
        ]
        
        for rel_type, label, color, line_style, arrow_type in relationships:
            frame, icon_canvas = self.create_palette_card(height=28)
            
            # Draw the relationship line
            if line_style == "dash":
                icon_canvas.create_line(14, 14, 102, 14, fill=color, width=2, dash=(4, 2))
            else:
                icon_canvas.create_line(14, 14, 102, 14, fill=color, width=2)
            
            # Draw arrow/symbol at the end
            if arrow_type == "triangle":
                # Inheritance arrow (empty triangle)
                icon_canvas.create_polygon(102, 14, 92, 8, 92, 20, fill="white", outline=color, width=2)
            elif arrow_type == "diamond_filled":
                # Composition (filled diamond)
                icon_canvas.create_polygon(102, 14, 95, 8, 88, 14, 95, 20, fill=color, outline=color, width=1)
            elif arrow_type == "diamond_empty":
                # Aggregation (empty diamond)
                icon_canvas.create_polygon(102, 14, 95, 8, 88, 14, 95, 20, fill="white", outline=color, width=2)
            elif arrow_type == "arrow":
                # Dependency arrow
                icon_canvas.create_line(102, 14, 92, 8, fill=color, width=2)
                icon_canvas.create_line(102, 14, 92, 20, fill=color, width=2)
            
            self.add_palette_item_label(frame, label)
            
            # Bind click event
            icon_canvas.bind("<Button-1>", lambda e, r=rel_type: self.select_relationship_from_palette(r))
        self.update_palette_hint("Tip: click a relationship card to arm drawing mode, then click source and target classes.")
    
    def select_relationship_from_palette(self, rel_type):
        """Select a relationship type and enter relationship mode, or change selected relationship type"""
        if self.replace_selected_connection_type(rel_type):
            self.update_status(f"Changed selected connector to {rel_type}")
            return

        self.rel_type_var.set(rel_type)
        if not self.relationship_mode:
            self.toggle_relationship_mode()
        self.update_status(f"Click two elements to create a {rel_type} connector")

    def on_relationship_type_changed(self, event=None):
        connector_type = self.rel_type_var.get()
        if self.relationship_mode:
            self.update_status(f"Connector mode updated: next {self.get_connector_name()} will use {connector_type}")
        else:
            self.update_status(f"Selected {connector_type} {self.get_connector_name()} type")
    
    def create_sequence_palette(self):
        """Create sequence diagram palette"""
        for widget in self.palette_content.winfo_children():
            widget.destroy()
        
        self.create_palette_section_header("Sequence", "Add participants, then choose the kind of message to draw.")
        
        # Add Actor button
        frame, canvas = self.create_palette_card(height=64)
        
        # Draw actor icon
        canvas.create_rectangle(28, 6, 88, 28, fill="lightblue", outline="black", width=2)
        canvas.create_text(58, 17, text="Actor", font=("Arial", 8, "bold"))
        canvas.create_line(58, 28, 58, 58, fill="gray", width=1, dash=(3, 3))
        
        self.add_palette_item_label(frame, "Actor")
        canvas.bind("<Button-1>", lambda e: self.add_sequence_actor())
        
        # Message types
        tk.Label(self.palette_content, text="Messages", bg="#ffffff", fg="#576574", font=("Segoe UI", 9, "bold")).pack(pady=(10, 4))
        
        messages = [
            ("sync", "Sync Call", "solid", "arrow"),
            ("async", "Async Call", "solid", "open"),
            ("return", "Return", "dash", "open")
        ]
        
        for msg_type, label, line_style, arrow in messages:
            frame, canvas = self.create_palette_card(height=26)
            
            if line_style == "dash":
                canvas.create_line(12, 13, 102, 13, fill="black", width=1, dash=(4, 2))
            elif line_style == "solid":
                canvas.create_line(12, 13, 102, 13, fill="black", width=2)
            
            if arrow == "arrow":
                canvas.create_polygon(102, 13, 92, 8, 92, 18, fill="black")
            elif arrow == "open":
                canvas.create_line(102, 13, 92, 8, fill="black", width=2)
                canvas.create_line(102, 13, 92, 18, fill="black", width=2)
            
            self.add_palette_item_label(frame, label)
            canvas.bind("<Button-1>", lambda e, t=msg_type: self.select_relationship_from_palette(t))
        self.update_palette_hint("Tip: sequence actors only move horizontally so messages stay aligned.")
    
    def create_state_palette(self):
        """Create state diagram palette"""
        for widget in self.palette_content.winfo_children():
            widget.destroy()
        
        self.create_palette_section_header("State", "Add states and transitions, then drag them into a readable flow.")
        
        # Add State button
        frame, canvas = self.create_palette_card(height=44)
        
        # Draw state icon (rounded rectangle)
        canvas.create_rectangle(16, 10, 100, 34, fill="lightgreen", outline="black", width=2)
        canvas.create_text(58, 22, text="State", font=("Arial", 8, "bold"))
        
        self.add_palette_item_label(frame, "State")
        canvas.bind("<Button-1>", lambda e: self.add_state_node())
        
        # Start/End states
        frame2, canvas2 = self.create_palette_card(height=44)
        
        # Draw start state (filled circle)
        canvas2.create_oval(22, 14, 40, 32, fill="black", outline="black")
        # Draw end state (double circle)
        canvas2.create_oval(72, 14, 90, 32, fill="white", outline="black", width=2)
        canvas2.create_oval(75, 17, 87, 29, fill="black", outline="black")
        
        self.add_palette_item_label(frame2, "Start / End")
        
        # Transitions
        tk.Label(self.palette_content, text="Transitions", bg="#ffffff", fg="#576574", font=("Segoe UI", 9, "bold")).pack(pady=(10, 4))
        
        frame3, canvas3 = self.create_palette_card(height=26)
        
        canvas3.create_line(12, 13, 102, 13, fill="black", width=2)
        canvas3.create_polygon(102, 13, 92, 8, 92, 18, fill="black")
        
        self.add_palette_item_label(frame3, "Transition")
        canvas3.bind("<Button-1>", lambda e: self.select_relationship_from_palette("transition"))
        self.update_palette_hint("Tip: labels on reverse transitions now separate automatically.")
    
    def create_er_palette(self):
        """Create ER diagram palette"""
        for widget in self.palette_content.winfo_children():
            widget.destroy()
        
        self.create_palette_section_header("ER Diagram", "Add entities first, then connect them with cardinalities.")
        
        # Add Entity button
        frame, canvas = self.create_palette_card(height=56)
        
        # Draw entity icon
        canvas.create_rectangle(18, 6, 98, 44, fill="lightyellow", outline="black", width=2)
        canvas.create_text(58, 16, text="Entity", font=("Arial", 8, "bold"))
        canvas.create_line(18, 26, 98, 26, fill="black", width=1)
        canvas.create_text(58, 36, text="id\nname", font=("Arial", 6))
        
        self.add_palette_item_label(frame, "Entity")
        canvas.bind("<Button-1>", lambda e: self.add_er_entity())
        
        # Relationships
        tk.Label(self.palette_content, text="Relationships", bg="#ffffff", fg="#576574", font=("Segoe UI", 9, "bold")).pack(pady=(10, 4))
        
        relationships = [
            ("one-to-one", "One to One", "||--||"),
            ("one-to-many", "One to Many", "||--o{"),
            ("many-to-many", "Many to Many", "}o--o{")
        ]
        
        for rel_type, label, symbol in relationships:
            frame, canvas = self.create_palette_card(height=26)
            
            canvas.create_line(12, 13, 102, 13, fill="black", width=2)
            canvas.create_text(57, 13, text=symbol, font=("Arial", 8))
            
            self.add_palette_item_label(frame, label)
            canvas.bind("<Button-1>", lambda e, r=rel_type: self.select_relationship_from_palette(r))
        self.update_palette_hint("Tip: ER cardinalities are pushed outside entity boxes for readability.")
        
    def add_shape_from_palette(self, shape_type):
        """Add a flowchart node with the specified shape"""
        if self.diagram_type != "flowchart":
            return
        
        # Add node at a default position (user can drag it)
        x = 200 + (len(self.flowchart_nodes) % 3) * 150
        y = 200 + (len(self.flowchart_nodes) // 3) * 120
        
        node = FlowchartNode(self.canvas, x, y, f"node{len(self.flowchart_nodes) + 1}", 
                            f"Node {len(self.flowchart_nodes) + 1}", shape_type, self)
        self.flowchart_nodes.append(node)
        
        # Auto-select the new node
        for n in self.flowchart_nodes:
            n.deselect()
        node.select()
        self.selected_node = node
        
        self.update_scroll_region()
        self.ensure_grid_behind()
        self.mark_as_changed()
        self.update_status(f"Added {shape_type} node")
    
    def add_sequence_actor(self):
        """Add a sequence diagram actor"""
        if self.diagram_type != "sequenceDiagram":
            self.update_status("Actors can only be added in sequence diagrams")
            return

        x = 100 + len(self.sequence_actors) * 150
        y = 50
        actor = SequenceActor(self.canvas, x, y, f"Actor{len(self.sequence_actors) + 1}", self)
        self.sequence_actors.append(actor)
        self.update_scroll_region()
        self.mark_as_changed()
        self.update_status("Added actor")
    
    def add_state_node(self):
        """Add a state diagram node"""
        if self.diagram_type != "stateDiagram":
            self.update_status("States can only be added in state diagrams")
            return

        x = 150 + (len(self.state_nodes) % 3) * 200
        y = 150 + (len(self.state_nodes) // 3) * 120
        state = StateNode(self.canvas, x, y, f"State{len(self.state_nodes) + 1}", self)
        self.state_nodes.append(state)
        self.update_scroll_region()
        self.mark_as_changed()
        self.update_status("Added state")
    
    def add_er_entity(self):
        """Add an ER diagram entity"""
        if self.diagram_type != "erDiagram":
            self.update_status("Entities can only be added in ER diagrams")
            return

        x = 150 + (len(self.er_entities) % 3) * 200
        y = 150 + (len(self.er_entities) // 3) * 150
        entity = EREntity(self.canvas, x, y, f"Entity{len(self.er_entities) + 1}", self)
        self.er_entities.append(entity)
        self.update_scroll_region()
        self.mark_as_changed()
        self.update_status("Added entity")
        
    def get_diagram_display_name(self):
        names = {
            "classDiagram": "Class Diagram",
            "flowchart": "Flowchart",
            "sequenceDiagram": "Sequence Diagram",
            "stateDiagram": "State Diagram",
            "erDiagram": "ER Diagram",
        }
        return names.get(self.diagram_type, self.diagram_type)

    def get_short_diagram_name(self):
        names = {
            "classDiagram": "Class",
            "flowchart": "Flow",
            "sequenceDiagram": "Sequence",
            "stateDiagram": "State",
            "erDiagram": "ER",
        }
        return names.get(self.diagram_type, self.diagram_type)

    def get_primary_element_name(self):
        names = {
            "classDiagram": "class",
            "flowchart": "node",
            "sequenceDiagram": "actor",
            "stateDiagram": "state",
            "erDiagram": "entity",
        }
        return names.get(self.diagram_type, "element")

    def get_primary_element_plural(self):
        names = {
            "classDiagram": "classes",
            "flowchart": "nodes",
            "sequenceDiagram": "actors",
            "stateDiagram": "states",
            "erDiagram": "entities",
        }
        return names.get(self.diagram_type, "elements")

    def get_connector_name(self):
        names = {
            "classDiagram": "relationship",
            "flowchart": "link",
            "sequenceDiagram": "message",
            "stateDiagram": "transition",
            "erDiagram": "relationship",
        }
        return names.get(self.diagram_type, "connector")

    def get_short_connector_name(self):
        names = {
            "classDiagram": "rels",
            "flowchart": "links",
            "sequenceDiagram": "msgs",
            "stateDiagram": "transitions",
            "erDiagram": "rels",
        }
        return names.get(self.diagram_type, "items")

    def get_relationship_button_label(self):
        base_action = {
            "classDiagram": "Draw Relation",
            "flowchart": "Draw Link",
            "sequenceDiagram": "Draw Message",
            "stateDiagram": "Draw Transition",
            "erDiagram": "Draw Relation",
        }.get(self.diagram_type, "Draw")
        return "Cancel" if self.relationship_mode else base_action

    def get_mode_hint_text(self):
        if self.relationship_mode:
            connector_type = self.rel_type_var.get()
            return f"Connector mode: pick source, then target, to create a {connector_type} {self.get_connector_name()}."
        return (
            f"Right-click empty space to add a {self.get_primary_element_name()}. Drag to reposition. Delete removes the current selection."
        )

    def refresh_ui_feedback(self):
        if hasattr(self, 'summary_label'):
            self.summary_label.config(
                text=(
                    f"{self.get_diagram_display_name()}  |  "
                    f"{len(self.get_active_node_collection())} {self.get_primary_element_plural()}  |  "
                    f"{len(self.get_active_connection_collection())} {self.get_short_connector_name()}  |  "
                    f"Zoom {int(self.zoom_level * 100)}%"
                )
            )
        if hasattr(self, 'mode_hint_label'):
            self.mode_hint_label.config(text=self.get_mode_hint_text())
        if hasattr(self, 'info_banner'):
            shortcut_hint = "Esc cancels connector mode" if self.relationship_mode else "Right-click empty space to add an element quickly"
            self.info_banner.config(text=f"{self.current_status_message}   |   {shortcut_hint}")
        if hasattr(self, 'document_label'):
            current_name = os.path.basename(self.current_file) if self.current_file else "Untitled diagram"
            self.document_label.config(text=current_name)
        if hasattr(self, 'document_meta_label'):
            save_state = "Unsaved changes" if self.has_unsaved_changes else "Saved"
            self.document_meta_label.config(text=f"{save_state} · {self.get_diagram_display_name()}")
        if hasattr(self, 'canvas_title_label'):
            self.canvas_title_label.config(text=f"{self.get_diagram_display_name()} Canvas")
        if hasattr(self, 'canvas_meta_label'):
            location = os.path.basename(self.current_file) if self.current_file else "Local workspace"
            self.canvas_meta_label.config(text=location)
        if hasattr(self, 'rel_button'):
            self.rel_button.config(
                text=self.get_relationship_button_label(),
                relief=tk.SUNKEN if self.relationship_mode else tk.RAISED,
                bg="#cfe7d8" if self.relationship_mode else "#e8eef7",
                activebackground="#bdddc9" if self.relationship_mode else "#d7e2f0",
            )
        self.refresh_code_preview()

    def update_status(self, message):
        """Update status bar message"""
        self.current_status_message = message
        if hasattr(self, 'status_bar'):
            self.status_bar.config(text=message)
        self.refresh_ui_feedback()

    def log_debug(self, message):
        if self.debug_logging:
            print(f"Debug: {message}")

    def log_warning(self, message):
        print(f"Warning: {message}")

    def get_active_node_collection(self):
        if self.diagram_type == "flowchart":
            return self.flowchart_nodes
        if self.diagram_type == "sequenceDiagram":
            return self.sequence_actors
        if self.diagram_type == "stateDiagram":
            return self.state_nodes
        if self.diagram_type == "erDiagram":
            return self.er_entities
        return self.classes

    def get_active_connection_collection(self):
        if self.diagram_type == "flowchart":
            return self.flowchart_connections
        if self.diagram_type == "sequenceDiagram":
            return self.sequence_messages
        if self.diagram_type == "stateDiagram":
            return self.state_transitions
        if self.diagram_type == "erDiagram":
            return self.er_relationships
        return self.relationships

    def get_all_connections(self):
        return self.relationships + self.flowchart_connections + self.sequence_messages + self.state_transitions + self.er_relationships

    def deselect_all_visuals(self):
        for class_box in self.classes:
            class_box.deselect()
        for node in self.flowchart_nodes:
            node.deselect()
        for actor in self.sequence_actors:
            actor.deselect()
        for state in self.state_nodes:
            state.deselect()
        for entity in self.er_entities:
            entity.deselect()
        for connection in self.get_all_connections():
            if getattr(connection, "selected", False):
                connection.deselect()
        self.selected_class = None
        self.selected_node = None
        self.selected_item = None

    def find_active_node_at(self, canvas_x, canvas_y):
        for node in self.get_active_node_collection():
            zoom_level = self.zoom_level if hasattr(self, 'zoom_level') else 1.0
            if self.diagram_type == "classDiagram":
                width = getattr(node, 'width', 0)
                height = getattr(node, 'height', 0)
            else:
                width = getattr(node, 'width', 0) * zoom_level
                height = getattr(node, 'height', 0) * zoom_level
            if node.x <= canvas_x <= node.x + width and node.y <= canvas_y <= node.y + height:
                return node
        return None

    def create_mode_connection(self, source_node, target_node):
        connection_type = self.rel_type_var.get()

        if self.diagram_type == "flowchart":
            label = simpledialog.askstring("Flowchart Label", "Connection label:", initialvalue="")
            connection = FlowchartConnection(self.canvas, source_node, target_node, connection_type, label or "", self)
            self.flowchart_connections.append(connection)
        elif self.diagram_type == "sequenceDiagram":
            label = simpledialog.askstring("Message Label", "Message label:", initialvalue="message")
            connection = SequenceMessage(self.canvas, source_node, target_node, connection_type, label or "message", len(self.sequence_messages), self)
            self.sequence_messages.append(connection)
            self.reindex_sequence_messages()
        elif self.diagram_type == "stateDiagram":
            label = simpledialog.askstring("Transition Label", "Transition label:", initialvalue="")
            connection = StateTransition(self.canvas, source_node, target_node, label or "", self)
            self.state_transitions.append(connection)
        elif self.diagram_type == "erDiagram":
            label = simpledialog.askstring("Relationship Label", "Relationship label:", initialvalue="")
            connection = ERRelationship(self.canvas, source_node, target_node, connection_type, label or "", self)
            self.er_relationships.append(connection)
        else:
            connection = Relationship(self.canvas, source_node, target_node, connection_type, self)
            self.relationships.append(connection)

        self.ensure_grid_behind()
        self.mark_as_changed()

    def replace_selected_connection_type(self, new_type):
        for connection in self.get_active_connection_collection():
            if getattr(connection, "selected", False):
                if hasattr(connection, "rel_type"):
                    connection.rel_type = new_type
                elif hasattr(connection, "conn_type"):
                    connection.conn_type = new_type
                elif hasattr(connection, "msg_type"):
                    connection.msg_type = new_type
                connection.update_position()
                self.mark_as_changed()
                return True
        return False

    def reindex_sequence_messages(self):
        for index, message in enumerate(self.sequence_messages):
            message.index = index
            message.update_position()
    
    def update_relationships(self):
        """Update all connector positions when elements move"""
        for rel in self.relationships:
            rel.update_position()
        for rel in self.flowchart_connections:
            rel.update_position()
        for rel in self.sequence_messages:
            rel.update_position()
        for rel in self.state_transitions:
            rel.update_position()
        for rel in self.er_relationships:
            rel.update_position()
        # Update scroll region after relationships change
        self.update_scroll_region()
        # Ensure grid stays behind
        self.ensure_grid_behind()
    
    def on_key_press(self, event):
        """Handle keyboard events"""
        if event.keysym == "Delete":
            self.delete_selected()
        elif event.keysym == "Escape":
            self.deselect_all_visuals()
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
    
    def on_canvas_configure(self, event):
        """Handle canvas configure event (resize, scroll)"""
        pass  # Grid scrolls automatically, no need to redraw
    
    def on_v_scroll(self, *args):
        """Handle vertical scrollbar movement"""
        self.canvas.yview(*args)
    
    def on_h_scroll(self, *args):
        """Handle horizontal scrollbar movement"""
        self.canvas.xview(*args)
    
    def on_canvas_y_scroll(self, *args):
        """Handle canvas y-scroll update"""
        self.v_scrollbar.set(*args)
    
    def on_canvas_x_scroll(self, *args):
        """Handle canvas x-scroll update"""
        self.h_scrollbar.set(*args)
    
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

        for collection in [self.flowchart_nodes, self.sequence_actors, self.state_nodes, self.er_entities]:
            for node in collection:
                node.x = center_x + (node.x - center_x) * scale_factor
                node.y = center_y + (node.y - center_y) * scale_factor
        
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
        
        # Recreate flowchart node visuals
        for node in self.flowchart_nodes:
            was_selected = node.selected
            node.selected = False
            node.create_visual()
            if was_selected:
                node.select()
        
        # Recreate sequence actor visuals
        for actor in self.sequence_actors:
            was_selected = actor.selected
            actor.selected = False
            actor.create_visual()
            if was_selected:
                actor.select()
        
        # Recreate state node visuals
        for state in self.state_nodes:
            was_selected = state.selected
            state.selected = False
            state.create_visual()
            if was_selected:
                state.select()
        
        # Recreate ER entity visuals
        for entity in self.er_entities:
            was_selected = entity.selected
            entity.selected = False
            entity.create_visual()
            if was_selected:
                entity.select()
        
        # Recreate relationship visuals
        for rel in self.relationships:
            was_selected = rel.selected
            rel.update_position()
            if was_selected:
                rel.select()
        for rel in self.flowchart_connections:
            was_selected = rel.selected
            rel.update_position()
            if was_selected:
                rel.select()
        for rel in self.sequence_messages:
            was_selected = rel.selected
            rel.update_position()
            if was_selected:
                rel.select()
        for rel in self.state_transitions:
            was_selected = rel.selected
            rel.update_position()
            if was_selected:
                rel.select()
        for rel in self.er_relationships:
            was_selected = rel.selected
            rel.update_position()
            if was_selected:
                rel.select()
        
        # Redraw grid with new zoom level
        if hasattr(self, 'show_grid') and self.show_grid.get():
            self.draw_grid()
    
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

    def add_primary_element(self):
        """Add the default element for the active diagram type."""
        if self.diagram_type == "flowchart":
            self.add_flowchart_node()
        elif self.diagram_type == "sequenceDiagram":
            self.add_sequence_actor()
        elif self.diagram_type == "stateDiagram":
            self.add_state_node()
        elif self.diagram_type == "erDiagram":
            self.add_er_entity()
        else:
            self.add_class()
    
    def add_class(self):
        if self.diagram_type != "classDiagram":
            self.update_status("Classes can only be added in class diagrams")
            return
            
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
        self.ensure_grid_behind()
        self.mark_as_changed()
    
    def add_flowchart_node(self):
        if self.diagram_type != "flowchart":
            self.update_status("Flowchart nodes can only be added in flowcharts")
            return

        x = 150 + (len(self.flowchart_nodes) % 4) * 200
        y = 150 + (len(self.flowchart_nodes) // 4) * 150
        node = FlowchartNode(self.canvas, x, y, f"node{len(self.flowchart_nodes) + 1}", 
                            f"Node {len(self.flowchart_nodes) + 1}", "rectangle", self)
        self.flowchart_nodes.append(node)
        
        # Auto-select the new node
        for n in self.flowchart_nodes:
            n.deselect()
        node.select()
        self.selected_node = node
        
        self.update_scroll_region()
        self.ensure_grid_behind()
        self.mark_as_changed()

    def update_diagram_type_ui(self):
        """Update type-specific UI so each diagram mode only exposes valid tools."""
        self.toggle_relationship_mode(force_off=True)

        if self.diagram_type == "flowchart":
            self.add_button.config(text="Add Node")
            self.create_flowchart_palette()
            rel_values = ["arrow", "line", "dotted", "thick"]
            rel_label = "Flow:"
            rel_text = "Add Link"
            self.layout_button.config(state=tk.DISABLED)
        elif self.diagram_type == "sequenceDiagram":
            self.add_button.config(text="Add Actor")
            self.create_sequence_palette()
            rel_values = ["sync", "async", "return"]
            rel_label = "Message:"
            rel_text = "Add Message"
            self.layout_button.config(state=tk.DISABLED)
        elif self.diagram_type == "stateDiagram":
            self.add_button.config(text="Add State")
            self.create_state_palette()
            rel_values = ["transition"]
            rel_label = "State:"
            rel_text = "Add Transition"
            self.layout_button.config(state=tk.DISABLED)
        elif self.diagram_type == "erDiagram":
            self.add_button.config(text="Add Entity")
            self.create_er_palette()
            rel_values = ["one-to-one", "one-to-many", "many-to-many"]
            rel_label = "ER:"
            rel_text = "Add Relation"
            self.layout_button.config(state=tk.DISABLED)
        else:
            self.add_button.config(text="Add Class")
            self.create_uml_palette()
            rel_values = ["association", "inheritance", "composition", "aggregation", "dependency", "realization"]
            rel_label = "Class:"
            rel_text = "Add Relationship"
            self.layout_button.config(state=tk.NORMAL)

        if not self.shape_palette.winfo_manager():
            self.shape_palette.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.connection_label.config(text=rel_label)
        self.rel_combo.config(values=rel_values, state="readonly")
        self.rel_type_var.set(rel_values[0])
        if hasattr(self, "sample_choice_var"):
            preferred_sample = {
                "classDiagram": "Class sample",
                "flowchart": "Flowchart sample",
                "sequenceDiagram": "Sequence sample",
                "stateDiagram": "State sample",
                "erDiagram": "ER sample",
            }.get(self.diagram_type)
            if preferred_sample:
                self.sample_choice_var.set(preferred_sample)
        self.rel_button.config(state=tk.NORMAL)
        self.refresh_ui_feedback()
        self.update_window_title()
    
    def on_diagram_type_changed(self, event=None):
        new_type = self.diagram_type_var.get()
        if new_type != self.diagram_type:
            # Ask for confirmation if there are unsaved changes
            if self.has_unsaved_changes:
                if not messagebox.askyesno("Change Diagram Type", 
                    "Changing diagram type will clear the current diagram. Continue?"):
                    self.diagram_type_var.set(self.diagram_type)
                    return
            
            self.diagram_type = new_type
            self.new_diagram()
            self.update_diagram_type_ui()
        
    def canvas_click(self, event):
        # Convert to canvas coordinates (accounts for scrolling and zoom)
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        if self.relationship_mode:
            clicked_node = self.find_active_node_at(canvas_x, canvas_y)

            if clicked_node:
                if self.relationship_start is None:
                    self.relationship_start = clicked_node
                    clicked_node.select()
                else:
                    if clicked_node != self.relationship_start:
                        self.create_mode_connection(self.relationship_start, clicked_node)
                    
                    # Reset relationship mode
                    if self.relationship_start:
                        self.relationship_start.deselect()
                    self.relationship_start = None
                    self.relationship_mode = False
                    self.refresh_ui_feedback()
                    self.update_status(f"Added {self.get_connector_name()}")
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
                # Clicked on a relationship - select it
                self.is_panning = False
                
                # Deselect all classes
                for class_box in self.classes:
                    class_box.deselect()
                
                # Deselect all other relationships
                for rel in self.relationships:
                    rel.deselect()
                
                # Select the clicked relationship
                clicked_relationship.select()
                self.selected_class = None
                self.update_status(f"Selected {clicked_relationship.rel_type} relationship - click a relationship type in the palette to change it")
                
            else:
                # Clicked on empty space - check if really empty
                # Convert event coordinates to canvas coordinates
                canvas_x = self.canvas.canvasx(event.x)
                canvas_y = self.canvas.canvasy(event.y)
                
                # Double-check no element at this position (using canvas coordinates)
                really_empty = True
                
                # Check classes
                for class_box in self.classes:
                    if (class_box.x <= canvas_x <= class_box.x + class_box.width and
                        class_box.y <= canvas_y <= class_box.y + class_box.height):
                        really_empty = False
                        break
                
                # Check flowchart nodes
                if really_empty:
                    for node in self.flowchart_nodes:
                        if (node.x <= canvas_x <= node.x + node.width and
                            node.y <= canvas_y <= node.y + node.height):
                            really_empty = False
                            break
                
                # Check sequence actors
                if really_empty:
                    for actor in self.sequence_actors:
                        if (actor.x <= canvas_x <= actor.x + actor.width and
                            actor.y <= canvas_y <= actor.y + actor.height):
                            really_empty = False
                            break
                
                # Check state nodes
                if really_empty:
                    for state in self.state_nodes:
                        if (state.x <= canvas_x <= state.x + state.width and
                            state.y <= canvas_y <= state.y + state.height):
                            really_empty = False
                            break
                
                # Check ER entities
                if really_empty:
                    for entity in self.er_entities:
                        if (entity.x <= canvas_x <= entity.x + entity.width and
                            entity.y <= canvas_y <= entity.y + entity.height):
                            really_empty = False
                            break
                
                if really_empty:
                    # Start panning - store initial position
                    self.is_panning = True
                    self.pan_start_x = event.x
                    self.pan_start_y = event.y
                    
                    # Change cursor to indicate panning mode
                    self.canvas.config(cursor="fleur")  # Four-way arrow cursor
                    
                    # Deselect all elements
                    for class_box in self.classes:
                        class_box.deselect()
                    for node in self.flowchart_nodes:
                        node.deselect()
                    for actor in self.sequence_actors:
                        actor.deselect()
                    for state in self.state_nodes:
                        state.deselect()
                    for entity in self.er_entities:
                        entity.deselect()
                    
                    # Deselect all relationships
                    for rel in self.relationships:
                        rel.deselect()
                    
                    self.selected_class = None
                    self.selected_node = None
                    self.selected_item = None
                    self.update_status("Pan mode - drag to move diagram")
                else:
                    self.is_panning = False
    
    def canvas_drag(self, event):
        """Handle canvas drag for panning"""
        # Don't pan if a class is selected (it's being dragged individually)
        if self.selected_class is not None or self.selected_node is not None or self.selected_item is not None:
            return
            
        if self.is_panning:
            # Calculate movement delta
            dx = event.x - self.pan_start_x
            dy = event.y - self.pan_start_y
            
            # Get scrollregion
            scrollregion = self.canvas.cget("scrollregion").split()
            if len(scrollregion) == 4:
                x1, y1, x2, y2 = map(float, scrollregion)
                width = x2 - x1
                height = y2 - y1
                
                # Get canvas dimensions
                canvas_width = self.canvas.winfo_width()
                canvas_height = self.canvas.winfo_height()
                
                # Calculate scroll amount as fraction of scrollable area
                if width > canvas_width:
                    scroll_x = -dx / (width - canvas_width)
                    current_x = self.canvas.xview()[0]
                    self.canvas.xview_moveto(max(0, min(1, current_x + scroll_x)))
                
                if height > canvas_height:
                    scroll_y = -dy / (height - canvas_height)
                    current_y = self.canvas.yview()[0]
                    self.canvas.yview_moveto(max(0, min(1, current_y + scroll_y)))
            
            # Update start position for next drag event
            self.pan_start_x = event.x
            self.pan_start_y = event.y
        # If not panning, the drag event will be handled by individual class objects
    
    def canvas_release(self, event):
        """Handle mouse button release"""
        if self.is_panning:
            self.is_panning = False
            # Reset cursor to default
            self.canvas.config(cursor="")
            self.update_status("Ready")
    
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
        """Handle right-click quick-create for the active diagram type."""
        if self.relationship_mode:
            return

        # Convert to canvas coordinates
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        clicked_node = self.find_active_node_at(canvas_x, canvas_y)

        if not clicked_node:
            self.add_primary_element_at_position(canvas_x, canvas_y)
            
    def add_class_at_position(self, x, y):
        if self.diagram_type != "classDiagram":
            return

        class_box = ClassBox(self.canvas, x, y, f"Class{len(self.classes) + 1}", self)
        self.classes.append(class_box)
        
        # Auto-select the new class
        for cls in self.classes:
            cls.deselect()
        class_box.select()
        self.selected_class = class_box
        
        self.update_scroll_region()
        self.ensure_grid_behind()
        self.mark_as_changed()

    def add_primary_element_at_position(self, x, y):
        if self.diagram_type == "flowchart":
            node = FlowchartNode(self.canvas, x, y, f"node{len(self.flowchart_nodes) + 1}", f"Node {len(self.flowchart_nodes) + 1}", "rectangle", self)
            self.flowchart_nodes.append(node)
            self.selected_node = node
            node.select()
        elif self.diagram_type == "sequenceDiagram":
            actor = SequenceActor(self.canvas, x, y, f"Actor{len(self.sequence_actors) + 1}", self)
            self.sequence_actors.append(actor)
            self.selected_item = actor
            actor.select()
        elif self.diagram_type == "stateDiagram":
            state = StateNode(self.canvas, x, y, f"State{len(self.state_nodes) + 1}", self)
            self.state_nodes.append(state)
            self.selected_item = state
            state.select()
        elif self.diagram_type == "erDiagram":
            entity = EREntity(self.canvas, x, y, f"Entity{len(self.er_entities) + 1}", self)
            self.er_entities.append(entity)
            self.selected_item = entity
            entity.select()
        else:
            self.add_class_at_position(x, y)
            return

        self.update_scroll_region()
        self.mark_as_changed()
        
    def delete_selected(self):
        deleted_any = False
        # Delete selected classes
        to_remove = []
        for class_box in self.classes:
            if class_box.selected:
                to_remove.append(class_box)
        
        # Delete selected flowchart nodes
        nodes_to_remove = []
        for node in self.flowchart_nodes:
            if node.selected:
                nodes_to_remove.append(node)
        
        # Delete selected sequence actors
        actors_to_remove = []
        for actor in self.sequence_actors:
            if actor.selected:
                actors_to_remove.append(actor)
        
        # Delete selected state nodes
        states_to_remove = []
        for state in self.state_nodes:
            if state.selected:
                states_to_remove.append(state)
        
        # Delete selected ER entities
        entities_to_remove = []
        for entity in self.er_entities:
            if entity.selected:
                entities_to_remove.append(entity)
                
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
            deleted_any = True
        
        for node in nodes_to_remove:
            for conn in list(self.flowchart_connections):
                if conn.from_node == node or conn.to_node == node:
                    conn.delete()
                    self.flowchart_connections.remove(conn)
            node.delete()
            self.flowchart_nodes.remove(node)
            deleted_any = True
        
        for actor in actors_to_remove:
            for conn in list(self.sequence_messages):
                if conn.from_actor == actor or conn.to_actor == actor:
                    conn.delete()
                    self.sequence_messages.remove(conn)
            actor.delete()
            self.sequence_actors.remove(actor)
            deleted_any = True
        
        for state in states_to_remove:
            for conn in list(self.state_transitions):
                if conn.from_state == state or conn.to_state == state:
                    conn.delete()
                    self.state_transitions.remove(conn)
            state.delete()
            self.state_nodes.remove(state)
            deleted_any = True
        
        for entity in entities_to_remove:
            for conn in list(self.er_relationships):
                if conn.from_entity == entity or conn.to_entity == entity:
                    conn.delete()
                    self.er_relationships.remove(conn)
            entity.delete()
            self.er_entities.remove(entity)
            deleted_any = True
            
        # Delete selected relationships
        rel_to_remove = []
        for rel in self.relationships:
            if rel.selected:
                rel_to_remove.append(rel)
                
        for rel in rel_to_remove:
            rel.delete()
            self.relationships.remove(rel)
            deleted_any = True

        for rel in list(self.flowchart_connections):
            if rel.selected:
                rel.delete()
                self.flowchart_connections.remove(rel)
                deleted_any = True

        for rel in list(self.sequence_messages):
            if rel.selected:
                rel.delete()
                self.sequence_messages.remove(rel)
                deleted_any = True
        if deleted_any and self.sequence_messages:
            self.reindex_sequence_messages()

        for rel in list(self.state_transitions):
            if rel.selected:
                rel.delete()
                self.state_transitions.remove(rel)
                deleted_any = True

        for rel in list(self.er_relationships):
            if rel.selected:
                rel.delete()
                self.er_relationships.remove(rel)
                deleted_any = True

        # Mark as changed if anything was deleted
        if deleted_any:
            self.mark_as_changed()
            self.deselect_all_visuals()
            self.update_scroll_region()
            self.ensure_grid_behind()
            
    def toggle_relationship_mode(self, force_off=False):
        if self.relationship_mode or force_off:
            self.relationship_mode = False
            if self.relationship_start:
                self.relationship_start.deselect()
            self.relationship_start = None
            self.refresh_ui_feedback()
        else:
            self.relationship_mode = True
            self.refresh_ui_feedback()
            self.update_status(f"Click two elements to create a {self.rel_type_var.get()} connector")
            
    def update_scroll_region(self):
        """Update canvas scroll region to include all elements with padding"""
        # Get bounding box of all items on canvas, excluding grid
        # Delete grid temporarily to get accurate bbox
        grid_items_coords = []
        grid_items = list(self.canvas.find_withtag("grid"))
        
        # Store grid line coordinates and delete them
        for item in grid_items:
            try:
                coords = self.canvas.coords(item)
                fill = self.canvas.itemcget(item, "fill")
                grid_items_coords.append((coords, fill))
                self.canvas.delete(item)
            except:
                pass
        
        bbox = self.canvas.bbox("all")
        
        # Recreate grid lines
        for coords, fill in grid_items_coords:
            if len(coords) == 4:
                self.canvas.create_line(coords[0], coords[1], coords[2], coords[3], 
                                       fill=fill, tags="grid", state="normal")
        
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
        
        # Only redraw grid if scroll region significantly changed
        # (Don't redraw during dragging to avoid visual glitches)
        if hasattr(self, 'show_grid') and self.show_grid.get():
            # Check if we need to expand the grid
            if hasattr(self, '_last_grid_region'):
                old_x1, old_y1, old_x2, old_y2 = self._last_grid_region
                if bbox:
                    new_x1, new_y1, new_x2, new_y2 = bbox
                    # Only redraw if the new region is significantly larger
                    if (new_x1 < old_x1 - 200 or new_y1 < old_y1 - 200 or 
                        new_x2 > old_x2 + 200 or new_y2 > old_y2 + 200):
                        self.draw_grid()
                        self._last_grid_region = bbox
                        self.canvas.after_idle(self.ensure_grid_behind)
            else:
                # First time, draw the grid
                self.draw_grid()
                if bbox:
                    self._last_grid_region = bbox
                self.canvas.after_idle(self.ensure_grid_behind)
        
        # Ensure grid stays behind after scroll region update
        if grid_items_coords:
            self.canvas.after_idle(self.ensure_grid_behind)
    
    def toggle_grid(self):
        """Toggle grid visibility"""
        if self.show_grid.get():
            self.draw_grid()
            # Store the current bbox for future comparisons
            bbox = self.canvas.bbox("all")
            if bbox:
                self._last_grid_region = bbox
            self.canvas.after_idle(self.ensure_grid_behind)
        else:
            self.hide_grid()
            # Clear the stored region
            if hasattr(self, '_last_grid_region'):
                delattr(self, '_last_grid_region')
    
    def draw_grid(self):
        """Draw grid on canvas (draws once, scrolls automatically)"""
        # Remove existing grid
        self.canvas.delete("grid")
        
        # Get scroll region
        scroll_region = self.canvas.cget("scrollregion").split()
        if len(scroll_region) == 4:
            x1, y1, x2, y2 = map(float, scroll_region)
        else:
            x1, y1, x2, y2 = 0, 0, 2000, 2000
        
        # Grid spacing (scaled by zoom level)
        base_spacing = 50
        spacing = base_spacing * self.zoom_level
        
        # Ensure minimum spacing
        if spacing < 10:
            spacing = 10
        
        # Grid color
        grid_color = "#e0e0e0"
        
        # Draw vertical lines across entire scroll region
        x = int(x1 / spacing) * spacing
        while x <= x2:
            self.canvas.create_line(x, y1, x, y2, fill=grid_color, tags="grid", state="normal")
            x += spacing
        
        # Draw horizontal lines across entire scroll region
        y = int(y1 / spacing) * spacing
        while y <= y2:
            self.canvas.create_line(x1, y, x2, y, fill=grid_color, tags="grid", state="normal")
            y += spacing
        
        # Lower grid to the very bottom immediately (only if grid items exist)
        if self.canvas.find_withtag("grid"):
            self.canvas.tag_lower("grid")
            # Schedule another lowering after idle to ensure it stays behind
            self.canvas.after_idle(lambda: self.canvas.tag_lower("grid") if self.canvas.find_withtag("grid") else None)
    
    def hide_grid(self):
        """Hide grid from canvas"""
        self.canvas.delete("grid")
    
    def ensure_grid_behind(self):
        """Ensure grid stays behind all other elements"""
        if hasattr(self, 'show_grid') and self.show_grid.get():
            # Only lower if grid items exist
            if self.canvas.find_withtag("grid"):
                self.canvas.tag_lower("grid")
        
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
        filename = filedialog.askopenfilename(
            filetypes=[("Markdown files", "*.md"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            self.load_diagram_from_file(filename, prompt_for_unsaved=True, show_errors=True)

    def new_diagram(self):
        """Create a new diagram"""
        if self.has_unsaved_changes:
            response = messagebox.askyesnocancel(
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save before creating a new diagram?"
            )

            if response is None:
                return
            if response:
                self.save_mermaid()
                if self.has_unsaved_changes:
                    return

        self.clear_diagram()
        if self.zoom_level != 1.0:
            self.set_zoom_level(1.0)
        else:
            if hasattr(self, 'zoom_label'):
                self.zoom_label.config(text="100%")
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)
        self.current_file = None
        self.mark_as_saved()
        self.update_status("New diagram created")

    def clear_diagram(self):
        """Remove all diagram elements without prompting the user."""
        for class_box in self.classes:
            class_box.delete()
        for node in self.flowchart_nodes:
            node.delete()
        for actor in self.sequence_actors:
            actor.delete()
        for state in self.state_nodes:
            state.delete()
        for entity in self.er_entities:
            entity.delete()
        for rel in self.relationships:
            rel.delete()
        for rel in self.flowchart_connections:
            rel.delete()
        for rel in self.sequence_messages:
            rel.delete()
        for rel in self.state_transitions:
            rel.delete()
        for rel in self.er_relationships:
            rel.delete()
        self.classes.clear()
        self.flowchart_nodes.clear()
        self.flowchart_connections.clear()
        self.sequence_actors.clear()
        self.sequence_messages.clear()
        self.state_nodes.clear()
        self.state_transitions.clear()
        self.er_entities.clear()
        self.er_relationships.clear()
        self.relationships.clear()
        self.selected_class = None
        self.selected_node = None
        self.selected_item = None
        self.relationship_start = None
        self.relationship_mode = False
        if hasattr(self, 'rel_button'):
            self.rel_button.config(relief=tk.RAISED)
        self.refresh_ui_feedback()
        self.update_scroll_region()
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)

    def extract_mermaid_code(self, content):
        """Extract Mermaid code from markdown code blocks or plain text"""
        # Try to find mermaid code block first
        mermaid_block_pattern = r'```mermaid\s*\n(.*?)\n```'
        match = re.search(mermaid_block_pattern, content, re.DOTALL | re.IGNORECASE)
        
        if match:
            return match.group(1).strip()
        
        # If no code block, check if the entire content is mermaid
        if any(diagram_type in content for diagram_type in ("classDiagram", "flowchart", "graph", "sequenceDiagram", "stateDiagram", "erDiagram")):
            return content.strip()
        
        return None
    
    def detect_mermaid_diagram_type(self, mermaid_code):
        """Detect the Mermaid diagram type without mutating the current canvas."""
        lines = [line.strip() for line in mermaid_code.split('\n') if line.strip()]

        if any(line.startswith('flowchart') or line.startswith('graph') for line in lines):
            return "flowchart"
        if any('sequenceDiagram' in line for line in lines):
            return "sequenceDiagram"
        if any('stateDiagram' in line for line in lines):
            return "stateDiagram"
        if any('erDiagram' in line for line in lines):
            return "erDiagram"
        if any('classDiagram' in line for line in lines):
            return "classDiagram"
        raise ValueError("Not a valid Mermaid diagram")

    def parse_mermaid(self, mermaid_code, apply_auto_layout=True):
        """Parse Mermaid diagram code and create visual elements"""
        diagram_type = self.detect_mermaid_diagram_type(mermaid_code)
        self.clear_diagram()
        self.diagram_type = diagram_type
        self.diagram_type_var.set(diagram_type)
        self.update_diagram_type_ui()

        if diagram_type == "flowchart":
            return self.parse_flowchart(mermaid_code)
        if diagram_type == "sequenceDiagram":
            return self.parse_sequence_diagram(mermaid_code)
        if diagram_type == "stateDiagram":
            return self.parse_state_diagram(mermaid_code)
        if diagram_type == "erDiagram":
            return self.parse_er_diagram(mermaid_code)
        return self.parse_class_diagram(mermaid_code, apply_auto_layout)
    
    def parse_flowchart(self, mermaid_code):
        """Parse flowchart code."""
        lines = [line.strip() for line in mermaid_code.split('\n') if line.strip()]
        
        nodes_data = {}
        connections = []
        
        for line in lines:
            if line.startswith('flowchart') or line.startswith('graph'):
                continue
            
            circle_match = re.match(r'(\w+)\(\((.+)\)\)', line)
            if circle_match:
                node_id, text = circle_match.groups()
                nodes_data[node_id] = {'text': text, 'shape': 'circle'}
                continue

            # Parse node definitions: nodeId[text] or nodeId(text) or nodeId{text}
            node_match = re.match(r'(\w+)([\[\(\{])([^\]\)\}]+)([\]\)\}])', line)
            if node_match:
                node_id, open_br, text, close_br = node_match.groups()
                shape = "rectangle"
                if open_br == '(' and close_br == ')':
                    shape = "rounded"
                elif open_br == '{' and close_br == '}':
                    shape = "diamond"
                nodes_data[node_id] = {'text': text, 'shape': shape}
                continue
            
            # Parse connections: A --> B or A --- B, optionally with a label
            conn_match = re.match(r'(\w+)\s*(-->|---|-\.->|==>)(?:\|([^|]+)\|)?\s*(\w+)', line)
            if conn_match:
                from_node, conn_type, label, to_node = conn_match.groups()
                flow_type_map = {
                    "-->": "arrow",
                    "---": "line",
                    "-.->": "dotted",
                    "==>": "thick"
                }
                connections.append((from_node, to_node, flow_type_map.get(conn_type, "arrow"), label or ""))
                # Ensure nodes exist
                if from_node not in nodes_data:
                    nodes_data[from_node] = {'text': from_node, 'shape': 'rectangle'}
                if to_node not in nodes_data:
                    nodes_data[to_node] = {'text': to_node, 'shape': 'rectangle'}
        
        # Create nodes
        x, y = 150, 150
        for i, (node_id, data) in enumerate(nodes_data.items()):
            node = FlowchartNode(self.canvas, x, y, node_id, data['text'], data['shape'], self)
            self.flowchart_nodes.append(node)
            x += 200
            if (i + 1) % 4 == 0:
                x = 150
                y += 150
        
        node_lookup = {node.node_id: node for node in self.flowchart_nodes}
        for from_node, to_node, conn_type, label in connections:
            if from_node in node_lookup and to_node in node_lookup:
                self.flowchart_connections.append(
                    FlowchartConnection(self.canvas, node_lookup[from_node], node_lookup[to_node], conn_type, label, self)
                )
        
        self.update_scroll_region()
        self.update_status(f"Loaded flowchart with {len(self.flowchart_nodes)} nodes")

    def parse_sequence_diagram(self, mermaid_code):
        lines = [line.strip() for line in mermaid_code.split('\n') if line.strip()]
        actor_lookup = {}
        message_rows = []

        for line in lines:
            if line.startswith("sequenceDiagram"):
                continue
            participant_match = re.match(r'(participant|actor)\s+([A-Za-z0-9_]+)(?:\s+as\s+(.+))?', line)
            if participant_match:
                _, actor_id, display_name = participant_match.groups()
                actor_lookup[actor_id] = {"name": (display_name or actor_id).strip()}
                continue

            msg_match = re.match(r'([A-Za-z0-9_]+)\s*(-{1,2}>>|\-{1,2}>|-->>)\s*([A-Za-z0-9_]+)\s*:\s*(.+)', line)
            if msg_match:
                source, arrow, target, label = msg_match.groups()
                msg_type = "sync"
                if arrow == "->>":
                    msg_type = "sync"
                elif arrow == "-->>":
                    msg_type = "return"
                else:
                    msg_type = "async"
                message_rows.append((source, target, msg_type, label.strip()))
                actor_lookup.setdefault(source, {"name": source})
                actor_lookup.setdefault(target, {"name": target})

        x = 100
        for actor_id, data in actor_lookup.items():
            actor = SequenceActor(self.canvas, x, 60, data["name"], self)
            actor.actor_id = actor_id
            self.sequence_actors.append(actor)
            x += 180

        actor_objects = {getattr(actor, "actor_id", actor.name): actor for actor in self.sequence_actors}
        for index, (source, target, msg_type, label) in enumerate(message_rows):
            if source in actor_objects and target in actor_objects:
                self.sequence_messages.append(
                    SequenceMessage(self.canvas, actor_objects[source], actor_objects[target], msg_type, label, index, self)
                )

        self.update_scroll_region()
        self.update_status(f"Loaded sequence diagram with {len(self.sequence_actors)} participants")

    def parse_state_diagram(self, mermaid_code):
        lines = [line.strip() for line in mermaid_code.split('\n') if line.strip()]
        state_names = []
        transitions = []

        for line in lines:
            if line.startswith("stateDiagram"):
                continue
            state_match = re.match(r'state\s+([A-Za-z0-9_]+)', line)
            if state_match:
                state_names.append(state_match.group(1))
                continue
            trans_match = re.match(r'([A-Za-z0-9_]+)\s*-->\s*([A-Za-z0-9_]+)(?:\s*:\s*(.+))?', line)
            if trans_match:
                source, target, label = trans_match.groups()
                transitions.append((source, target, (label or "").strip()))
                if source not in state_names:
                    state_names.append(source)
                if target not in state_names:
                    state_names.append(target)

        x, y = 150, 150
        state_lookup = {}
        for index, state_name in enumerate(state_names):
            state = StateNode(self.canvas, x, y, state_name, self)
            self.state_nodes.append(state)
            state_lookup[state_name] = state
            x += 220
            if (index + 1) % 3 == 0:
                x = 150
                y += 140

        for source, target, label in transitions:
            if source in state_lookup and target in state_lookup:
                self.state_transitions.append(StateTransition(self.canvas, state_lookup[source], state_lookup[target], label, self))

        self.update_scroll_region()
        self.update_status(f"Loaded state diagram with {len(self.state_nodes)} states")

    def parse_er_diagram(self, mermaid_code):
        lines = [line.rstrip() for line in mermaid_code.split('\n') if line.strip()]
        entity_blocks = {}
        relationships = []
        current_entity = None

        for raw_line in lines:
            line = raw_line.strip()
            if line.startswith("erDiagram"):
                continue

            entity_start = re.match(r'([A-Za-z0-9_]+)\s*\{', line)
            if entity_start:
                current_entity = entity_start.group(1)
                entity_blocks.setdefault(current_entity, [])
                continue

            if line == "}":
                current_entity = None
                continue

            if current_entity:
                entity_blocks[current_entity].append(line)
                continue

            rel_match = re.match(r'([A-Za-z0-9_]+)\s+(\|\|--\|\||\|\|--o\{|\}o--o\{)\s+([A-Za-z0-9_]+)(?:\s*:\s*(.+))?', line)
            if rel_match:
                left, symbol, right, label = rel_match.groups()
                rel_type_map = {
                    "||--||": "one-to-one",
                    "||--o{": "one-to-many",
                    "}o--o{": "many-to-many"
                }
                relationships.append((left, right, rel_type_map.get(symbol, "one-to-many"), (label or "").strip()))
                entity_blocks.setdefault(left, [])
                entity_blocks.setdefault(right, [])

        x, y = 150, 150
        entity_lookup = {}
        for index, (entity_name, attrs) in enumerate(entity_blocks.items()):
            entity = EREntity(self.canvas, x, y, entity_name, self)
            entity.attributes = attrs
            self.er_entities.append(entity)
            entity_lookup[entity_name] = entity
            x += 240
            if (index + 1) % 3 == 0:
                x = 150
                y += 170

        for left, right, rel_type, label in relationships:
            if left in entity_lookup and right in entity_lookup:
                self.er_relationships.append(ERRelationship(self.canvas, entity_lookup[left], entity_lookup[right], rel_type, label, self))

        self.update_scroll_region()
        self.update_status(f"Loaded ER diagram with {len(self.er_entities)} entities")
    
    def parse_class_diagram(self, mermaid_code, apply_auto_layout=True):
        """Parse Mermaid class diagram code and create visual elements"""
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
        self.ensure_grid_behind()
    
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
        if self.diagram_type == "flowchart":
            return self.generate_flowchart()
        if self.diagram_type == "sequenceDiagram":
            return self.generate_sequence_diagram()
        if self.diagram_type == "stateDiagram":
            return self.generate_state_diagram()
        if self.diagram_type == "erDiagram":
            return self.generate_er_diagram()
        else:
            return self.generate_class_diagram()
    
    def generate_flowchart(self):
        lines = ["flowchart TD"]
        
        # Add nodes
        for node in self.flowchart_nodes:
            if node.shape == "rectangle":
                lines.append(f"    {node.node_id}[{node.text}]")
            elif node.shape == "rounded":
                lines.append(f"    {node.node_id}({node.text})")
            elif node.shape == "diamond":
                lines.append(f"    {node.node_id}{{{node.text}}}")
            elif node.shape == "circle":
                lines.append(f"    {node.node_id}(({node.text}))")
        
        flow_symbol_map = {
            "arrow": "-->",
            "line": "---",
            "dotted": "-.->",
            "thick": "==>"
        }
        for connection in self.flowchart_connections:
            symbol = flow_symbol_map.get(connection.conn_type, "-->")
            line = f"    {connection.from_node.node_id} {symbol}"
            if connection.label:
                line += f"|{connection.label}|"
            line += f" {connection.to_node.node_id}"
            lines.append(line)
        
        return '\n'.join(lines)

    def generate_sequence_diagram(self):
        lines = ["sequenceDiagram"]
        for actor in self.sequence_actors:
            actor_name = actor.name.replace("\n", " ").strip() or "Actor"
            actor_id = getattr(actor, "actor_id", actor_name.replace(" ", "_"))
            lines.append(f"    participant {actor_id} as {actor_name}")
        arrow_map = {
            "sync": "->>",
            "async": "-->",
            "return": "-->>",
            "note": "--"
        }
        for message in self.sequence_messages:
            source = getattr(message.from_actor, "actor_id", message.from_actor.name.replace(" ", "_"))
            target = getattr(message.to_actor, "actor_id", message.to_actor.name.replace(" ", "_"))
            symbol = arrow_map.get(message.msg_type, "->>")
            lines.append(f"    {source} {symbol} {target} : {message.label}")
        return '\n'.join(lines)

    def generate_state_diagram(self):
        lines = ["stateDiagram-v2"]
        for state in self.state_nodes:
            state_name = state.name.replace("\n", " ").strip() or "State"
            lines.append(f"    state {state_name}")
        for transition in self.state_transitions:
            line = f"    {transition.from_state.name} --> {transition.to_state.name}"
            if transition.label:
                line += f" : {transition.label}"
            lines.append(line)
        return '\n'.join(lines)

    def generate_er_diagram(self):
        lines = ["erDiagram"]
        for entity in self.er_entities:
            entity_name = entity.name.replace(" ", "_").upper() or "ENTITY"
            lines.append(f"    {entity_name} {{")
            for attr in entity.attributes:
                lines.append(f"        {attr}")
            lines.append("    }")
        symbol_map = {
            "one-to-one": "||--||",
            "one-to-many": "||--o{",
            "many-to-many": "}o--o{"
        }
        for relation in self.er_relationships:
            left = relation.from_entity.name.replace(" ", "_").upper()
            right = relation.to_entity.name.replace(" ", "_").upper()
            line = f"    {left} {symbol_map.get(relation.rel_type, '||--o{')} {right}"
            if relation.label:
                line += f" : {relation.label}"
            lines.append(line)
        return '\n'.join(lines)
    
    def generate_class_diagram(self):
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
            
            if rel.rel_type == "inheritance":
                rel_line = f"    {to_name}"
                if rel.to_multiplicity:
                    rel_line += f" \"{rel.to_multiplicity}\""
                rel_line += " <|--"
                if rel.from_multiplicity:
                    rel_line += f" \"{rel.from_multiplicity}\""
                rel_line += f" {from_name}"
            elif rel.rel_type == "realization":
                rel_line = f"    {to_name}"
                if rel.to_multiplicity:
                    rel_line += f" \"{rel.to_multiplicity}\""
                rel_line += " <|.."
                if rel.from_multiplicity:
                    rel_line += f" \"{rel.from_multiplicity}\""
                rel_line += f" {from_name}"
            else:
                # Build relationship line with multiplicities and labels
                rel_line = f"    {from_name}"
                
                # Add from multiplicity
                if rel.from_multiplicity:
                    rel_line += f" \"{rel.from_multiplicity}\""
                
                # Add relationship symbol
                if rel.rel_type == "composition":
                    rel_line += " *--"
                elif rel.rel_type == "aggregation":
                    rel_line += " o--"
                elif rel.rel_type == "dependency":
                    rel_line += " <.."
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
    
    def _read_text_file(self, filename):
        """Read a diagram file using a small set of fallback encodings."""
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']

        for encoding in encodings:
            try:
                with open(filename, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue

        raise UnicodeDecodeError("text", b"", 0, 1, "Could not decode file with supported encodings")

    def load_diagram_from_file(self, filename, prompt_for_unsaved=True, show_errors=True):
        """Load a Mermaid file and restore any saved layout metadata."""
        if prompt_for_unsaved and self.has_unsaved_changes:
            response = messagebox.askyesnocancel(
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save before opening a new file?"
            )

            if response is None:
                return False
            if response:
                self.save_mermaid()
                if self.has_unsaved_changes:
                    return False

        try:
            content = self._read_text_file(filename)
            mermaid_code = self.extract_mermaid_code(content)
            if not mermaid_code:
                raise ValueError("No valid Mermaid diagram found in file")

            positions = self.load_positions(filename)
            if positions and positions.get("zoom_level", 0) > 0:
                self.set_zoom_level(positions["zoom_level"])
            else:
                self.set_zoom_level(1.0)

            self.parse_mermaid(mermaid_code, apply_auto_layout=(positions is None))

            if positions:
                self.apply_positions(positions, skip_zoom=True)
                self.update_status(f"Loaded from {os.path.basename(filename)} (with saved positions)")
            else:
                self.update_status(f"Loaded from {os.path.basename(filename)} (auto-layout applied)")

            self.current_file = filename
            self.mark_as_saved()
            self.save_last_file_path()
            return True
        except UnicodeDecodeError:
            if show_errors:
                messagebox.showerror("Error", "Could not decode file. Please ensure it's a text file.")
            return False
        except Exception as e:
            if show_errors:
                messagebox.showerror("Error", f"Failed to open file: {str(e)}")
            else:
                self.log_warning(f"Could not load diagram '{filename}': {e}")
            return False

    def save_positions(self, mermaid_file=None):
        """Save element positions to a companion JSON file (normalized to zoom 1.0)."""
        mermaid_file = mermaid_file or self.current_file
        if not mermaid_file:
            return False

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
            "flowchart_nodes": {},
            "sequence_actors": {},
            "state_nodes": {},
            "er_entities": {},
            "metadata": {
                "version": "1.3",
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
                self.log_debug(
                    f"Saving {class_name} at normalized ({normalized_x:.1f}, {normalized_y:.1f}) "
                    f"from actual ({class_box.x:.1f}, {class_box.y:.1f}) at zoom {self.zoom_level}"
                )
            except Exception as e:
                self.log_warning(f"Could not save position for class {class_box.name}: {e}")
                continue

        for node in self.flowchart_nodes:
            try:
                normalized_x = node.x / self.zoom_level if self.zoom_level > 0 else node.x
                normalized_y = node.y / self.zoom_level if self.zoom_level > 0 else node.y
                positions["flowchart_nodes"][node.node_id] = {
                    "x": float(normalized_x),
                    "y": float(normalized_y)
                }
            except Exception as e:
                self.log_warning(f"Could not save position for node {node.node_id}: {e}")
                continue

        for actor in self.sequence_actors:
            actor_id = getattr(actor, "actor_id", actor.name.replace(" ", "_"))
            positions["sequence_actors"][actor_id] = {
                "x": float(actor.x / self.zoom_level if self.zoom_level > 0 else actor.x),
                "y": float(actor.y / self.zoom_level if self.zoom_level > 0 else actor.y)
            }

        for state in self.state_nodes:
            positions["state_nodes"][state.name] = {
                "x": float(state.x / self.zoom_level if self.zoom_level > 0 else state.x),
                "y": float(state.y / self.zoom_level if self.zoom_level > 0 else state.y)
            }

        for entity in self.er_entities:
            entity_key = entity.name.replace(" ", "_").upper()
            positions["er_entities"][entity_key] = {
                "x": float(entity.x / self.zoom_level if self.zoom_level > 0 else entity.x),
                "y": float(entity.y / self.zoom_level if self.zoom_level > 0 else entity.y)
            }
        
        try:
            with open(position_file, 'w', encoding='utf-8') as f:
                json.dump(positions, f, indent=2)
            self.log_debug(f"Saved positions to {position_file}")
            return True
        except Exception as e:
            self.log_warning(f"Could not save positions file: {e}")
            # Don't show error to user - position saving is optional
            return False
    
    def load_positions(self, mermaid_file):
        """Load element positions from a companion JSON file."""
        # Create position file path
        position_file = mermaid_file + ".positions.json"
        
        self.log_debug(f"Looking for position file: {position_file}")
        
        if not os.path.exists(position_file):
            # Position file doesn't exist - this is normal for old diagrams
            self.log_debug("Position file not found")
            return None
        
        self.log_debug("Position file found, loading...")
        
        try:
            with open(position_file, 'r', encoding='utf-8') as f:
                positions = json.load(f)
            self.log_debug(f"Successfully loaded positions with {len(positions.get('classes', {}))} classes")
            return positions
        except json.JSONDecodeError as e:
            # Invalid JSON - silently ignore and use default layout
            self.log_warning(f"Could not parse position file (invalid JSON): {e}")
            return None
        except Exception as e:
            # Other errors - silently ignore
            self.log_warning(f"Could not load positions: {e}")
            return None
    
    def apply_positions(self, positions, skip_zoom=False):
        """Apply saved positions to diagram elements."""
        if not positions:
            self.log_debug("No positions to apply")
            return
        
        class_positions = positions.get("classes", {})
        node_positions = positions.get("flowchart_nodes", {})
        actor_positions = positions.get("sequence_actors", {})
        state_positions = positions.get("state_nodes", {})
        entity_positions = positions.get("er_entities", {})

        if not class_positions and not node_positions and not actor_positions and not state_positions and not entity_positions:
            self.log_warning("Position file missing supported element data")
            return

        self.log_debug(
            f"Applying positions for {len(class_positions)} classes, {len(node_positions)} flowchart nodes, "
            f"{len(actor_positions)} actors, {len(state_positions)} states and {len(entity_positions)} entities"
        )
        self.log_debug(f"Current zoom level: {self.zoom_level}")
        
        try:
            # Apply zoom level if saved (unless we already did it)
            if not skip_zoom and "zoom_level" in positions:
                saved_zoom = positions["zoom_level"]
                self.log_debug(f"Saved zoom level: {saved_zoom}")
                if saved_zoom > 0:
                    self.log_debug(f"Setting zoom level to: {saved_zoom}")
                    self.set_zoom_level(saved_zoom)
            
            # Apply positions to each class (scale from normalized to current zoom)
            applied_count = 0
            for class_box in self.classes:
                class_name = class_box.name.replace(" ", "_")
                if class_name in class_positions:
                    pos = class_positions[class_name]
                    
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
                        self.log_debug(
                            f"Moved {class_name} from ({old_x:.1f}, {old_y:.1f}) to ({class_box.x:.1f}, {class_box.y:.1f}) "
                            f"[normalized: ({pos['x']:.1f}, {pos['y']:.1f})]"
                        )
                else:
                    self.log_debug(f"No saved position for class '{class_name}'")

            applied_nodes = 0
            for node in self.flowchart_nodes:
                if node.node_id in node_positions:
                    pos = node_positions[node.node_id]
                    if "x" in pos and "y" in pos:
                        dx = (pos["x"] * self.zoom_level) - node.x
                        dy = (pos["y"] * self.zoom_level) - node.y
                        node.x += dx
                        node.y += dy
                        self.canvas.move(node.shape_item, dx, dy)
                        self.canvas.move(node.text_item, dx, dy)
                        applied_nodes += 1

            for actor in self.sequence_actors:
                actor_id = getattr(actor, "actor_id", actor.name.replace(" ", "_"))
                if actor_id in actor_positions:
                    pos = actor_positions[actor_id]
                    dx = (pos["x"] * self.zoom_level) - actor.x
                    dy = (pos["y"] * self.zoom_level) - actor.y
                    actor.x += dx
                    actor.y += dy
                    self.canvas.move(actor.box, dx, dy)
                    self.canvas.move(actor.text_item, dx, dy)
                    self.canvas.move(actor.lifeline, dx, dy)

            for state in self.state_nodes:
                if state.name in state_positions:
                    pos = state_positions[state.name]
                    dx = (pos["x"] * self.zoom_level) - state.x
                    dy = (pos["y"] * self.zoom_level) - state.y
                    state.x += dx
                    state.y += dy
                    self.canvas.move(state.box, dx, dy)
                    self.canvas.move(state.text_item, dx, dy)

            for entity in self.er_entities:
                entity_key = entity.name.replace(" ", "_").upper()
                if entity_key in entity_positions:
                    pos = entity_positions[entity_key]
                    dx = (pos["x"] * self.zoom_level) - entity.x
                    dy = (pos["y"] * self.zoom_level) - entity.y
                    entity.x += dx
                    entity.y += dy
                    self.canvas.move(entity.box, dx, dy)
                    self.canvas.move(entity.text_item, dx, dy)

            self.log_debug(
                f"Applied positions to {applied_count}/{len(self.classes)} classes and "
                f"{applied_nodes}/{len(self.flowchart_nodes)} nodes"
            )
            
            # Update relationships after moving classes
            self.update_relationships()
            self.update_scroll_region()
            self.restore_canvas_viewport(positions.get("canvas_viewport"))
        except Exception as e:
            self.log_warning(f"Error applying positions: {e}")
            # Continue anyway - diagram will use default positions

    def restore_canvas_viewport(self, viewport):
        """Restore the saved viewport after the scroll region is ready."""
        if not viewport:
            return

        xview = viewport.get("xview")
        yview = viewport.get("yview")

        def apply_view():
            if xview and len(xview) >= 1:
                self.canvas.xview_moveto(xview[0])
            if yview and len(yview) >= 1:
                self.canvas.yview_moveto(yview[0])

        self.root.after_idle(apply_view)
    
    def mark_as_changed(self):
        """Mark the diagram as having unsaved changes"""
        if not self.has_unsaved_changes:
            self.has_unsaved_changes = True
            self.update_window_title()
        self.refresh_ui_feedback()
    
    def mark_as_saved(self):
        """Mark the diagram as saved"""
        self.has_unsaved_changes = False
        self.update_window_title()
        self.refresh_ui_feedback()
    
    def update_window_title(self):
        """Update window title to show current file and unsaved changes"""
        title = f"Mermaid {self.get_diagram_display_name()} Tool"
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
                self.log_warning(f"Could not save config: {e}")
    
    def load_last_file_path(self):
        """Load the last opened file path from config"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return f.read().strip()
        except Exception as e:
            self.log_warning(f"Could not load config: {e}")
        return None
    
    def load_last_diagram(self):
        """Load the last used diagram on startup"""
        last_file = self.load_last_file_path()
        if last_file and os.path.exists(last_file):
            self.load_diagram_from_file(last_file, prompt_for_unsaved=False, show_errors=False)
    
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
                self.log_warning(f"Could not save positions on exit: {e}")
        
        # Save the last file path
        self.save_last_file_path()
        
        # Close the application
        self.root.destroy()
        
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = MermaidDiagramTool()
    app.run()
