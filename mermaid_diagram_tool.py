import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import tkinter.font as tkfont
import html
import json
import math
import re
import os
import shutil
import subprocess
import sys
import tempfile

try:
    from PIL import Image, ImageColor, ImageDraw, ImageFont
except ImportError:
    Image = None
    ImageColor = None
    ImageDraw = None
    ImageFont = None

SURFACE_BG = "#f4f7fb"
PANEL_BG = "#e9eff6"
PANEL_EDGE = "#cfdae8"
CANVAS_BG = "#fbfdff"
TEXT_PRIMARY = "#1f2d3d"
TEXT_MUTED = "#607086"
ACCENT = "#2d8cff"
SUCCESS = "#9fd46b"
WARNING = "#ffd97a"

try:
    from tksvg import SvgImage
except ImportError:
    SvgImage = None


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


def create_rounded_rectangle(canvas, x1, y1, x2, y2, radius, **kwargs):
    """Draw a rounded rectangle on a Tk canvas using a smoothed polygon."""
    radius = max(0, min(radius, abs(x2 - x1) / 2, abs(y2 - y1) / 2))
    if radius <= 1:
        return canvas.create_rectangle(x1, y1, x2, y2, **kwargs)

    points = [
        x1 + radius, y1,
        x1 + radius, y1,
        x2 - radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1 + radius,
        x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, splinesteps=16, **kwargs)


def measure_wrapped_text(canvas, text, font, target_width, minimum_width=80, max_width=320):
    """Measure wrapped text and return a practical text box size."""
    width = max(minimum_width, min(max_width, int(target_width)))
    temp_text = canvas.create_text(0, 0, text=text, font=font, width=width, justify="center")
    bbox = canvas.bbox(temp_text)
    canvas.delete(temp_text)
    if not bbox:
        return width, 20
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def unquote_mermaid_string(value):
    """Remove a single layer of Mermaid/JSON-style quotes from a value."""
    if value is None:
        return None
    text = value.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
        return text[1:-1]
    return text


def split_er_entity_reference(reference):
    """Split an ER entity reference into identifier and optional display alias."""
    text = reference.strip()
    alias_match = re.match(r'(.+?)\[(.+)\]$', text)
    if alias_match:
        entity_id = unquote_mermaid_string(alias_match.group(1).strip())
        entity_alias = unquote_mermaid_string(alias_match.group(2).strip())
        return entity_id, entity_alias
    cleaned = unquote_mermaid_string(text)
    return cleaned, None


def parse_sequence_participant_config(config_text):
    """Extract supported fields from Mermaid's inline sequence participant config."""
    parsed = {"type": None, "alias": None}
    if not config_text:
        return parsed

    type_match = re.search(r'"type"\s*:\s*"([^"]+)"', config_text)
    alias_match = re.search(r'"alias"\s*:\s*"([^"]+)"', config_text)
    if type_match:
        parsed["type"] = type_match.group(1).strip()
    if alias_match:
        parsed["alias"] = alias_match.group(1).strip()
    return parsed


SEQUENCE_BASE_ARROWS = [
    "<<-->>",
    "<<->>",
    "-->>",
    "->>",
    "--|\\",
    "-|\\",
    "--|/",
    "-|/",
    "/|--",
    "/|-",
    "\\\\--",
    "\\\\-",
    "--\\\\",
    "-\\\\",
    "--//",
    "-//",
    "//--",
    "//-",
    "--x",
    "-x",
    "--)",
    "-)",
    "-->",
    "->",
]
SEQUENCE_ARROW_PATTERN = "|".join(re.escape(symbol) for symbol in SEQUENCE_BASE_ARROWS)
SEQUENCE_MESSAGE_RE = re.compile(
    rf'([A-Za-z0-9_]+)\s*(\(\))?\s*({SEQUENCE_ARROW_PATTERN})\s*(\(\))?\s*([A-Za-z0-9_]+)\s*:\s*(.+)'
)

FLOWCHART_NODE_REFERENCE_RE = re.compile(
    r'^\s*([A-Za-z0-9_]+)(?:\(\((.+)\)\)|\((.+)\)|\[([^\]]+)\]|\{([^}]+)\})?\s*$'
)


def normalize_er_cardinality_text(value):
    """Normalize Mermaid ER cardinality syntax into a compact display value."""
    normalized = value.strip().lower()
    mapping = {
        "|o": "0..1",
        "o|": "0..1",
        "||": "1",
        "}o": "0..N",
        "o{": "0..N",
        "}|": "1..N",
        "|{": "1..N",
        "one or zero": "0..1",
        "zero or one": "0..1",
        "only one": "1",
        "1": "1",
        "one or more": "1..N",
        "one or many": "1..N",
        "many(1)": "1..N",
        "1+": "1..N",
        "zero or more": "0..N",
        "zero or many": "0..N",
        "many(0)": "0..N",
        "0+": "0..N",
    }
    return mapping.get(normalized, value.strip())


def get_runtime_base_dir():
    """Return the directory the app should use for bundled/runtime files."""
    compiled = globals().get("__compiled__")
    if compiled is not None and hasattr(compiled, "containing_dir"):
        return compiled.containing_dir
    return os.path.dirname(os.path.abspath(__file__))


def infer_er_rel_type(from_cardinality, to_cardinality):
    """Infer the editor's coarse ER relation type from endpoint cardinalities."""
    many_values = {"0..N", "1..N", "N"}
    from_is_many = from_cardinality in many_values
    to_is_many = to_cardinality in many_values
    if from_is_many and to_is_many:
        return "many-to-many"
    if not from_is_many and not to_is_many:
        return "one-to-one"
    return "one-to-many"


def parse_er_relationship_syntax(relation_text):
    """Parse Mermaid ER relationship text into visual metadata."""
    relation = relation_text.strip()

    symbolic_match = re.fullmatch(r'(\|o|\|\||\}o|\}\|)(--|\.\.)(o\||\|\||o\{|\|\{)', relation)
    if symbolic_match:
        left_card, separator, right_card = symbolic_match.groups()
        from_cardinality = normalize_er_cardinality_text(left_card)
        to_cardinality = normalize_er_cardinality_text(right_card)
        return {
            "rel_type": infer_er_rel_type(from_cardinality, to_cardinality),
            "from_cardinality": from_cardinality,
            "to_cardinality": to_cardinality,
            "identifying": separator == "--",
        }

    textual_match = re.fullmatch(r'(.+?)\s+(optionally to|to)\s+(.+)', relation, flags=re.IGNORECASE)
    if textual_match:
        left_card, connector, right_card = textual_match.groups()
        from_cardinality = normalize_er_cardinality_text(left_card)
        to_cardinality = normalize_er_cardinality_text(right_card)
        return {
            "rel_type": infer_er_rel_type(from_cardinality, to_cardinality),
            "from_cardinality": from_cardinality,
            "to_cardinality": to_cardinality,
            "identifying": connector.lower() == "to",
        }

    return None


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


def position_connection_label(
    canvas,
    text_item,
    from_point,
    to_point,
    obstacle_bboxes=None,
    preferred_side=1,
    base_offset=12,
    padding=2,
    line_item=None,
    exclude_items=None,
):
    """Place a connection label near its line while avoiding nodes and other text."""
    obstacles = [bbox for bbox in (obstacle_bboxes or []) if bbox]
    excluded = set(exclude_items or [])
    excluded.add(text_item)
    if line_item:
        excluded.add(line_item)

    for item in canvas.find_all():
        if item in excluded or "grid" in canvas.gettags(item):
            continue
        if canvas.type(item) != "text":
            continue
        bbox = canvas.bbox(item)
        if bbox:
            obstacles.append(bbox)

    place_text_near_line(
        canvas,
        text_item,
        from_point,
        to_point,
        obstacles,
        preferred_side=preferred_side,
        base_offset=base_offset,
        padding=padding,
    )

    if line_item:
        canvas.tag_raise(text_item, line_item)
    else:
        canvas.tag_raise(text_item)


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
        self.class_id = name.replace(" ", "_")
        self.display_label = name
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
                position_connection_label(
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
                    line_item=self.line,
                )
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
        
        font_size = max(8, int(10 * zoom_level))
        if self.shape == "diamond":
            base_target_width = self.width * zoom_level * 0.55
        elif self.shape == "circle":
            base_target_width = self.width * zoom_level * 0.7
        else:
            base_target_width = self.width * zoom_level * 0.8

        text_width, text_height = measure_wrapped_text(
            self.canvas,
            self.text,
            ("Arial", font_size),
            base_target_width,
            minimum_width=max(70, int(72 * zoom_level)),
            max_width=max(180, int(240 * zoom_level)),
        )
        horizontal_padding = max(26, int(32 * zoom_level))
        vertical_padding = max(18, int(22 * zoom_level))

        base_w = max(self.width * zoom_level, text_width + horizontal_padding)
        base_h = max(self.height * zoom_level, text_height + vertical_padding)
        if self.shape == "diamond":
            w = max(base_w, text_width * 1.75)
            h = max(base_h, text_height * 2.0)
        elif self.shape == "circle":
            diameter = max(base_w, base_h)
            w = diameter
            h = diameter
        else:
            w = base_w
            h = base_h

        self.width = max(80, w / zoom_level)
        self.height = max(50, h / zoom_level)

        # Draw shape based on type
        if self.shape == "rectangle":
            self.shape_item = self.canvas.create_rectangle(
                self.x, self.y, self.x + w, self.y + h,
                fill="lightblue", outline="black", width=max(1, int(2 * zoom_level))
            )
        elif self.shape == "rounded":
            self.shape_item = create_rounded_rectangle(
                self.canvas,
                self.x, self.y, self.x + w, self.y + h,
                radius=max(10, int(14 * zoom_level)),
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
        
        self.text_item = self.canvas.create_text(
            self.x + w/2, self.y + h/2,
            text=self.text,
            font=("Arial", font_size),
            tags="node_text",
            width=max(50, int(text_width)),
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
            self.create_visual()
            if self.tool:
                self.tool.update_relationships()
                self.tool.update_scroll_region()
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
        self.actor_id = name.replace(" ", "_")
        self.actor_kind = "participant"
        self.participant_type = None
        self.width = 110
        self.height = 56
        self.selected = False
        self.drag_data = {"x": 0, "y": 0}
        self.create_visual()
    
    def get_render_type(self):
        participant_type = (self.participant_type or "").strip().lower()
        if participant_type:
            return participant_type
        if self.actor_kind == "actor":
            return "actor"
        return "participant"

    def get_visual_metrics(self, zoom_level):
        render_type = self.get_render_type()
        width = self.width * zoom_level
        if render_type in {"actor", "boundary", "control", "entity"}:
            height = max(72, int(80 * zoom_level))
        elif render_type == "database":
            height = max(60, int(68 * zoom_level))
        elif render_type == "collections":
            height = max(56, int(62 * zoom_level))
        elif render_type == "queue":
            height = max(56, int(62 * zoom_level))
        else:
            height = max(40, int(46 * zoom_level))
        return width, height

    def supports_svg_icon(self):
        return (
            SvgImage is not None
            and self.get_render_type() in {"actor", "boundary", "control", "entity", "database", "collections", "queue"}
        )

    def get_svg_icon_bounds(self, x, y, w, h, zoom_level):
        render_type = self.get_render_type()
        if render_type == "actor":
            icon_w = min(w, max(42, int(50 * zoom_level)))
            icon_h = min(h, max(56, int(62 * zoom_level)))
        elif render_type in {"boundary", "control", "entity"}:
            icon_w = min(w, max(54, int(60 * zoom_level)))
            icon_h = min(h, max(50, int(56 * zoom_level)))
        elif render_type == "database":
            icon_w = min(w, max(74, int(82 * zoom_level)))
            icon_h = min(h, max(48, int(54 * zoom_level)))
        elif render_type == "collections":
            icon_w = min(w, max(74, int(82 * zoom_level)))
            icon_h = min(h, max(46, int(50 * zoom_level)))
        else:
            icon_w = min(w, max(72, int(80 * zoom_level)))
            icon_h = min(h, max(44, int(48 * zoom_level)))
        icon_x = x + max(0, (w - icon_w) / 2)
        return icon_x, y, icon_w, icon_h

    def build_sequence_participant_svg(self, render_type, width, height):
        stroke = "#111111"
        soft_fill = "#eaf5f8"
        stroke_width = max(2.0, min(width, height) * 0.06)
        common = f'stroke="{stroke}" stroke-width="{stroke_width:.2f}" stroke-linecap="round" stroke-linejoin="round"'

        if render_type == "actor":
            head_r = width * 0.16
            cx = width / 2
            head_cy = max(head_r + 2, height * 0.2)
            torso_top = head_cy + head_r
            torso_bottom = height * 0.64
            arm_y = height * 0.44
            leg_y = height * 0.94
            arm_half = width * 0.32
            leg_half = width * 0.24
            body = [
                f'<circle cx="{cx:.2f}" cy="{head_cy:.2f}" r="{head_r:.2f}" fill="none" {common} />',
                f'<line x1="{cx:.2f}" y1="{torso_top:.2f}" x2="{cx:.2f}" y2="{torso_bottom:.2f}" {common} />',
                f'<line x1="{cx - arm_half:.2f}" y1="{arm_y:.2f}" x2="{cx + arm_half:.2f}" y2="{arm_y:.2f}" {common} />',
                f'<line x1="{cx:.2f}" y1="{torso_bottom:.2f}" x2="{cx - leg_half:.2f}" y2="{leg_y:.2f}" {common} />',
                f'<line x1="{cx:.2f}" y1="{torso_bottom:.2f}" x2="{cx + leg_half:.2f}" y2="{leg_y:.2f}" {common} />',
            ]
        elif render_type == "boundary":
            radius = min(width, height) * 0.3
            cx = width * 0.58
            cy = height * 0.46
            line_x = cx - radius - width * 0.24
            body = [
                f'<line x1="{line_x:.2f}" y1="{cy - radius * 0.95:.2f}" x2="{line_x:.2f}" y2="{cy + radius * 0.95:.2f}" {common} />',
                f'<line x1="{line_x:.2f}" y1="{cy:.2f}" x2="{cx - radius * 0.42:.2f}" y2="{cy:.2f}" {common} />',
                f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{radius:.2f}" fill="none" {common} />',
            ]
        elif render_type == "control":
            radius = min(width, height) * 0.31
            cx = width / 2
            cy = height * 0.46
            ax1 = cx - radius * 0.82
            ay1 = cy - radius * 0.88
            ax2 = cx + radius * 0.9
            ay2 = cy + radius * 0.78
            arrow_x = cx + radius * 0.16
            arrow_y = cy - radius * 0.8
            body = [
                f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{radius:.2f}" fill="none" {common} />',
                f'<path d="M {ax1:.2f} {ay1:.2f} A {radius * 0.92:.2f} {radius * 0.92:.2f} 0 1 1 {ax2:.2f} {ay2:.2f}" fill="none" {common} />',
                f'<line x1="{arrow_x:.2f}" y1="{arrow_y:.2f}" x2="{arrow_x - radius * 0.36:.2f}" y2="{arrow_y + radius * 0.12:.2f}" {common} />',
                f'<line x1="{arrow_x:.2f}" y1="{arrow_y:.2f}" x2="{arrow_x - radius * 0.14:.2f}" y2="{arrow_y + radius * 0.38:.2f}" {common} />',
            ]
        elif render_type == "entity":
            radius = min(width, height) * 0.31
            cx = width / 2
            cy = height * 0.44
            underline_y = cy + radius + height * 0.12
            body = [
                f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{radius:.2f}" fill="none" {common} />',
                f'<line x1="{cx - radius:.2f}" y1="{underline_y:.2f}" x2="{cx + radius:.2f}" y2="{underline_y:.2f}" {common} />',
            ]
        elif render_type == "database":
            rx = width * 0.42
            left = (width - (rx * 2)) / 2
            right = left + (rx * 2)
            top = height * 0.12
            bottom = height * 0.88
            ellipse_h = height * 0.22
            body = [
                f'<rect x="{left:.2f}" y="{top + ellipse_h / 2:.2f}" width="{(rx * 2):.2f}" height="{(bottom - top - ellipse_h):.2f}" fill="{soft_fill}" stroke="none" />',
                f'<ellipse cx="{width / 2:.2f}" cy="{top + ellipse_h / 2:.2f}" rx="{rx:.2f}" ry="{ellipse_h / 2:.2f}" fill="{soft_fill}" {common} />',
                f'<line x1="{left:.2f}" y1="{top + ellipse_h / 2:.2f}" x2="{left:.2f}" y2="{bottom - ellipse_h / 2:.2f}" {common} />',
                f'<line x1="{right:.2f}" y1="{top + ellipse_h / 2:.2f}" x2="{right:.2f}" y2="{bottom - ellipse_h / 2:.2f}" {common} />',
                f'<path d="M {left:.2f} {bottom - ellipse_h / 2:.2f} A {rx:.2f} {ellipse_h / 2:.2f} 0 0 0 {right:.2f} {bottom - ellipse_h / 2:.2f}" fill="none" {common} />',
            ]
        elif render_type == "collections":
            pad = width * 0.08
            offset = width * 0.1
            box_w = width - pad * 2 - offset
            box_h = height * 0.64
            top = height * 0.18
            body = [
                f'<rect x="{pad + offset:.2f}" y="{top + offset * 0.45:.2f}" width="{box_w:.2f}" height="{box_h:.2f}" rx="{width * 0.04:.2f}" ry="{width * 0.04:.2f}" fill="{soft_fill}" {common} />',
                f'<rect x="{pad:.2f}" y="{top:.2f}" width="{box_w:.2f}" height="{box_h:.2f}" rx="{width * 0.04:.2f}" ry="{width * 0.04:.2f}" fill="{soft_fill}" {common} />',
            ]
        else:
            pad = width * 0.08
            rect_h = height * 0.62
            top = height * 0.18
            body = [
                f'<rect x="{pad:.2f}" y="{top:.2f}" width="{width - pad * 2:.2f}" height="{rect_h:.2f}" rx="{height * 0.18:.2f}" ry="{height * 0.18:.2f}" fill="{soft_fill}" {common} />',
            ]
            for ratio in (0.32, 0.5, 0.68):
                x = pad + (width - pad * 2) * ratio
                body.append(
                    f'<line x1="{x:.2f}" y1="{top + rect_h * 0.18:.2f}" x2="{x:.2f}" y2="{top + rect_h * 0.82:.2f}" {common} />'
                )

        body_markup = "\n        ".join(body)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{int(width)}" height="{int(height)}" '
            f'viewBox="0 0 {width:.2f} {height:.2f}">'
            f'\n        {body_markup}\n</svg>'
        )

    def draw_svg_shape(self, x, y, w, h, zoom_level):
        render_type = self.get_render_type()
        icon_x, icon_y, icon_w, icon_h = self.get_svg_icon_bounds(x, y, w, h, zoom_level)
        svg_markup = self.build_sequence_participant_svg(render_type, icon_w, icon_h)
        photo = SvgImage(
            master=self.canvas,
            data=svg_markup,
            scaletowidth=max(1, int(round(icon_w))),
        )
        self.image_refs.append(photo)
        image_item = self.register_item(
            self.canvas.create_image(icon_x, icon_y, anchor="nw", image=photo)
        )
        if self.tool:
            self.tool.canvas_svg_exports[image_item] = {
                "svg_markup": svg_markup,
                "x": icon_x,
                "y": icon_y,
                "width": icon_w,
                "height": icon_h,
                "photo": photo,
            }
        self.selection_outline_item = self.register_item(
            self.canvas.create_rectangle(
                icon_x - 4,
                icon_y - 4,
                icon_x + icon_w + 4,
                icon_y + icon_h + 4,
                outline="",
                width=max(2, int(3 * zoom_level)),
            )
        )
        self.canvas.tag_raise(self.selection_outline_item)
        self.primary_bbox = (icon_x, icon_y, icon_x + icon_w, icon_y + icon_h)
        self.box = self.selection_outline_item
        return icon_x + icon_w / 2, icon_y + icon_h / 2, icon_y + icon_h

    def delete_visual_items(self):
        if self.tool:
            for item in getattr(self, "visual_items", []):
                self.tool.canvas_svg_exports.pop(item, None)
        for item in getattr(self, "visual_items", []):
            self.canvas.delete(item)
        self.visual_items = []
        self.outline_items = []
        self.fill_outline_items = []
        self.image_refs = []
        self.selection_outline_item = None
        self.primary_bbox = None
        self.box = None
        self.text_item = None
        self.lifeline = None

    def register_item(self, item, outline=False, fill_outline=False):
        self.visual_items.append(item)
        if outline:
            self.outline_items.append(item)
        if fill_outline:
            self.fill_outline_items.append(item)
        return item

    def draw_participant_shape(self, x, y, w, h, zoom_level):
        self.box = self.register_item(
            self.canvas.create_rectangle(
                x, y, x + w, y + h,
                fill="#bfe2ee", outline="black", width=max(1, int(2 * zoom_level))
            ),
            outline=True,
        )
        self.primary_bbox = (x, y, x + w, y + h)
        return x + w / 2, y + h / 2, y + h

    def draw_collections_shape(self, x, y, w, h, zoom_level):
        offset = max(6, int(6 * zoom_level))
        back = self.register_item(
            self.canvas.create_rectangle(
                x + offset, y + offset, x + w + offset, y + h + offset,
                fill="#d9eef5", outline="black", width=max(1, int(2 * zoom_level))
            ),
            outline=True,
        )
        front = self.register_item(
            self.canvas.create_rectangle(
                x, y, x + w, y + h,
                fill="#bfe2ee", outline="black", width=max(1, int(2 * zoom_level))
            ),
            outline=True,
        )
        self.box = front
        self.primary_bbox = self.canvas.bbox(front)
        return x + w / 2, y + h / 2 + offset / 2, y + h + offset

    def draw_database_shape(self, x, y, w, h, zoom_level):
        oval_h = max(10, int(14 * zoom_level))
        self.register_item(
            self.canvas.create_rectangle(
                x, y + oval_h / 2, x + w, y + h - oval_h / 2,
                fill="#bfe2ee", outline="black", width=max(1, int(2 * zoom_level))
            ),
            outline=True,
        )
        self.register_item(
            self.canvas.create_oval(
                x, y, x + w, y + oval_h,
                fill="#d6edf5", outline="black", width=max(1, int(2 * zoom_level))
            ),
            outline=True,
        )
        self.register_item(
            self.canvas.create_arc(
                x, y + h - oval_h, x + w, y + h,
                start=180, extent=180, style=tk.ARC, outline="black", width=max(1, int(2 * zoom_level))
            ),
            fill_outline=True,
        )
        self.primary_bbox = (x, y, x + w, y + h)
        self.box = self.visual_items[0]
        return x + w / 2, y + h / 2, y + h

    def draw_queue_shape(self, x, y, w, h, zoom_level):
        arc_w = max(14, int(18 * zoom_level))
        self.register_item(
            self.canvas.create_rectangle(
                x + arc_w / 2, y, x + w - arc_w / 2, y + h,
                fill="#bfe2ee", outline="black", width=max(1, int(2 * zoom_level))
            ),
            outline=True,
        )
        self.register_item(
            self.canvas.create_arc(
                x, y, x + arc_w, y + h,
                start=90, extent=180, style=tk.ARC, outline="black", width=max(1, int(2 * zoom_level))
            ),
            fill_outline=True,
        )
        self.register_item(
            self.canvas.create_arc(
                x + w - arc_w, y, x + w, y + h,
                start=270, extent=180, style=tk.ARC, outline="black", width=max(1, int(2 * zoom_level))
            ),
            fill_outline=True,
        )
        for ratio in (0.28, 0.5, 0.72):
            line_x = x + ratio * w
            self.register_item(
                self.canvas.create_line(
                    line_x, y + h * 0.18, line_x, y + h * 0.82,
                    fill="black", width=max(1, int(1 * zoom_level))
                ),
                fill_outline=True,
            )
        self.primary_bbox = (x, y, x + w, y + h)
        self.box = self.visual_items[0]
        return x + w / 2, y + h / 2, y + h

    def draw_actor_shape(self, x, y, w, h, zoom_level):
        center_x = x + w / 2
        head_r = max(10, int(12 * zoom_level))
        head_cy = y + head_r + max(2, int(2 * zoom_level))
        torso_top = head_cy + head_r
        torso_bottom = torso_top + max(18, int(20 * zoom_level))
        arm_y = torso_top + max(6, int(8 * zoom_level))
        leg_bottom_y = torso_bottom + max(16, int(18 * zoom_level))
        limb_half = max(14, int(18 * zoom_level))

        self.register_item(
            self.canvas.create_oval(
                center_x - head_r, head_cy - head_r, center_x + head_r, head_cy + head_r,
                fill="#dff2f7", outline="black", width=max(1, int(2 * zoom_level))
            ),
            outline=True,
        )
        for coords in [
            (center_x, torso_top, center_x, torso_bottom),
            (center_x - limb_half, arm_y, center_x + limb_half, arm_y),
            (center_x, torso_bottom, center_x - limb_half + 4, leg_bottom_y),
            (center_x, torso_bottom, center_x + limb_half - 4, leg_bottom_y),
        ]:
            self.register_item(
                self.canvas.create_line(*coords, fill="black", width=max(1, int(2 * zoom_level))),
                fill_outline=True,
            )
        self.primary_bbox = (center_x - limb_half, y, center_x + limb_half, leg_bottom_y)
        return center_x, (y + leg_bottom_y) / 2, leg_bottom_y

    def draw_boundary_shape(self, x, y, w, h, zoom_level):
        center_x = x + w / 2 + max(8, int(8 * zoom_level))
        radius = max(16, int(20 * zoom_level))
        center_y = y + radius + max(4, int(4 * zoom_level))
        line_x = center_x - radius - max(12, int(18 * zoom_level))
        self.register_item(
            self.canvas.create_line(
                line_x, center_y, center_x - radius * 0.45, center_y,
                fill="black", width=max(1, int(2 * zoom_level))
            ),
            fill_outline=True,
        )
        self.register_item(
            self.canvas.create_line(
                line_x, center_y - radius * 0.9, line_x, center_y + radius * 0.9,
                fill="black", width=max(1, int(2 * zoom_level))
            ),
            fill_outline=True,
        )
        self.register_item(
            self.canvas.create_oval(
                center_x - radius, center_y - radius, center_x + radius, center_y + radius,
                fill="#dff2f7", outline="black", width=max(1, int(2 * zoom_level))
            ),
            outline=True,
        )
        self.primary_bbox = (line_x - 2, center_y - radius, center_x + radius, center_y + radius)
        return center_x, center_y, center_y + radius

    def draw_control_shape(self, x, y, w, h, zoom_level):
        center_x = x + w / 2
        radius = max(16, int(20 * zoom_level))
        center_y = y + radius + max(4, int(4 * zoom_level))
        self.register_item(
            self.canvas.create_oval(
                center_x - radius, center_y - radius, center_x + radius, center_y + radius,
                fill="#dff2f7", outline="black", width=max(1, int(2 * zoom_level))
            ),
            outline=True,
        )
        self.register_item(
            self.canvas.create_arc(
                center_x - radius * 0.8, center_y - radius * 0.9,
                center_x + radius * 0.9, center_y + radius * 0.8,
                start=40, extent=250, style=tk.ARC, outline="black", width=max(1, int(2 * zoom_level))
            ),
            fill_outline=True,
        )
        arrow_x = center_x + radius * 0.2
        arrow_y = center_y - radius * 0.78
        for coords in [
            (arrow_x, arrow_y, arrow_x - 8 * zoom_level, arrow_y + 3 * zoom_level),
            (arrow_x, arrow_y, arrow_x - 3 * zoom_level, arrow_y + 8 * zoom_level),
        ]:
            self.register_item(
                self.canvas.create_line(*coords, fill="black", width=max(1, int(2 * zoom_level))),
                fill_outline=True,
            )
        self.primary_bbox = (center_x - radius, center_y - radius, center_x + radius, center_y + radius)
        return center_x, center_y, center_y + radius

    def draw_entity_shape(self, x, y, w, h, zoom_level):
        center_x = x + w / 2
        radius = max(16, int(20 * zoom_level))
        center_y = y + radius + max(4, int(4 * zoom_level))
        self.register_item(
            self.canvas.create_oval(
                center_x - radius, center_y - radius, center_x + radius, center_y + radius,
                fill="#dff2f7", outline="black", width=max(1, int(2 * zoom_level))
            ),
            outline=True,
        )
        underline_y = center_y + radius + max(4, int(5 * zoom_level))
        self.register_item(
            self.canvas.create_line(
                center_x - radius, underline_y, center_x + radius, underline_y,
                fill="black", width=max(1, int(2 * zoom_level))
            ),
            fill_outline=True,
        )
        self.primary_bbox = (center_x - radius, center_y - radius, center_x + radius, underline_y)
        return center_x, (center_y + underline_y) / 2, underline_y

    def create_visual(self):
        zoom_level = 1.0
        if self.tool and hasattr(self.tool, 'zoom_level'):
            zoom_level = self.tool.zoom_level
        
        self.delete_visual_items()

        render_type = self.get_render_type()
        w, h = self.get_visual_metrics(zoom_level)
        label_margin = max(10, int(12 * zoom_level))
        x = self.x
        y = self.y
        center_x = x + w / 2
        shape_center_y = y + h / 2
        shape_bottom_y = y + h

        if self.supports_svg_icon():
            center_x, shape_center_y, shape_bottom_y = self.draw_svg_shape(x, y, w, h, zoom_level)
        elif render_type == "actor":
            center_x, shape_center_y, shape_bottom_y = self.draw_actor_shape(x, y, w, h, zoom_level)
        elif render_type == "boundary":
            center_x, shape_center_y, shape_bottom_y = self.draw_boundary_shape(x, y, w, h, zoom_level)
        elif render_type == "control":
            center_x, shape_center_y, shape_bottom_y = self.draw_control_shape(x, y, w, h, zoom_level)
        elif render_type == "entity":
            center_x, shape_center_y, shape_bottom_y = self.draw_entity_shape(x, y, w, h, zoom_level)
        elif render_type == "database":
            center_x, shape_center_y, shape_bottom_y = self.draw_database_shape(x, y, w, h, zoom_level)
        elif render_type == "collections":
            center_x, shape_center_y, shape_bottom_y = self.draw_collections_shape(x, y, w, h, zoom_level)
        elif render_type == "queue":
            center_x, shape_center_y, shape_bottom_y = self.draw_queue_shape(x, y, w, h, zoom_level)
        else:
            center_x, shape_center_y, shape_bottom_y = self.draw_participant_shape(x, y, w, h, zoom_level)

        font_size = max(8, int(10 * zoom_level))
        label_y = shape_bottom_y + label_margin
        self.text_item = self.register_item(
            self.canvas.create_text(
                center_x, label_y,
                text=self.name,
                font=("Arial", font_size, "bold"),
                width=get_centered_text_width(w, 0.95, minimum=60),
                justify="center"
            )
        )

        text_bbox = self.canvas.bbox(self.text_item)
        visual_bbox = self.primary_bbox or (x, y, x + w, y + h)
        if text_bbox:
            self.primary_bbox = (
                min(visual_bbox[0], text_bbox[0]),
                min(visual_bbox[1], text_bbox[1]),
                max(visual_bbox[2], text_bbox[2]),
                max(visual_bbox[3], text_bbox[3]),
            )
        else:
            self.primary_bbox = visual_bbox

        self.width = max(w / zoom_level, 80)
        self.height = max((self.primary_bbox[3] - self.primary_bbox[1]) / zoom_level, 40)

        # Draw lifeline (dashed vertical line) - scale length with zoom
        lifeline_length = 200 * zoom_level
        self.lifeline = self.register_item(
            self.canvas.create_line(
                center_x, self.primary_bbox[3], center_x, self.primary_bbox[3] + lifeline_length,
                fill="gray", width=max(1, int(1 * zoom_level)), dash=(5, 5)
            ),
            fill_outline=True,
        )

        for item in self.visual_items:
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
        for item in self.visual_items:
            self.canvas.move(item, dx, dy)
        if self.primary_bbox:
            self.primary_bbox = (
                self.primary_bbox[0] + dx,
                self.primary_bbox[1] + dy,
                self.primary_bbox[2] + dx,
                self.primary_bbox[3] + dy,
            )
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
        if getattr(self, "selection_outline_item", None):
            self.canvas.itemconfig(self.selection_outline_item, outline="red", width=max(2, int(3 * zoom_level)))
            self.canvas.tag_raise(self.selection_outline_item)
        for item in getattr(self, "outline_items", []):
            self.canvas.itemconfig(item, outline="red", width=max(2, int(3 * zoom_level)))
        for item in getattr(self, "fill_outline_items", []):
            self.canvas.itemconfig(item, fill="red", width=max(2, int(3 * zoom_level)))
    
    def deselect(self):
        self.selected = False
        zoom_level = 1.0
        if self.tool and hasattr(self.tool, 'zoom_level'):
            zoom_level = self.tool.zoom_level
        if getattr(self, "selection_outline_item", None):
            self.canvas.itemconfig(self.selection_outline_item, outline="", width=max(2, int(3 * zoom_level)))
        for item in getattr(self, "outline_items", []):
            self.canvas.itemconfig(item, outline="black", width=max(1, int(2 * zoom_level)))
        for item in getattr(self, "fill_outline_items", []):
            self.canvas.itemconfig(item, fill="black", width=max(1, int(2 * zoom_level)))

    def get_center(self):
        if self.primary_bbox:
            return (
                (self.primary_bbox[0] + self.primary_bbox[2]) / 2,
                (self.primary_bbox[1] + self.primary_bbox[3]) / 2,
            )
        zoom_level = self.tool.zoom_level if self.tool and hasattr(self.tool, 'zoom_level') else 1.0
        return (self.x + (self.width * zoom_level) / 2, self.y + (self.height * zoom_level) / 2)

    def delete(self):
        self.delete_visual_items()


class SequenceNote:
    def __init__(self, canvas, placement, actors, text, row_index=0, tool=None):
        self.canvas = canvas
        self.tool = tool
        self.placement = placement
        self.actors = actors
        self.text = text
        self.row_index = row_index
        self.box = None
        self.text_item = None
        self.fold_line = None
        self.create_visual()

    def get_anchor_points(self):
        actor_centers = [actor.get_center()[0] for actor in self.actors if actor]
        actor_tops = [actor.primary_bbox[1] for actor in self.actors if getattr(actor, "primary_bbox", None)]
        if not actor_centers:
            return 160, 120
        x = sum(actor_centers) / len(actor_centers)
        top = min(actor_tops) if actor_tops else 60
        y = top + ((self.row_index + 1) * 50)
        if self.placement == "left of":
            x -= 120
        elif self.placement == "right of":
            x += 120
        return x, y

    def create_visual(self):
        zoom_level = self.tool.zoom_level if self.tool and hasattr(self.tool, 'zoom_level') else 1.0
        self.delete()
        x, y = self.get_anchor_points()
        font = ("Arial", max(8, int(9 * zoom_level)))
        note_width = max(120, int(140 * zoom_level))
        text_width, text_height = measure_wrapped_text(
            self.canvas,
            self.text,
            font,
            note_width * 0.82,
            minimum_width=max(90, int(100 * zoom_level)),
            max_width=max(180, int(220 * zoom_level)),
        )
        w = max(note_width, text_width + max(20, int(22 * zoom_level)))
        h = max(int(46 * zoom_level), text_height + max(16, int(18 * zoom_level)))
        left = x - (w / 2)
        top = y - h - max(18, int(20 * zoom_level))
        fold = max(12, int(14 * zoom_level))
        self.box = self.canvas.create_polygon(
            left, top,
            left + w - fold, top,
            left + w, top + fold,
            left + w, top + h,
            left, top + h,
            fill="#fff4c2",
            outline="#9c7a00",
            width=max(1, int(2 * zoom_level)),
        )
        self.fold_line = self.canvas.create_line(
            left + w - fold, top,
            left + w - fold, top + fold,
            left + w, top + fold,
            fill="#9c7a00",
            width=max(1, int(1 * zoom_level)),
        )
        self.text_item = self.canvas.create_text(
            left + (w / 2),
            top + (h / 2),
            text=self.text,
            font=font,
            width=max(70, int(text_width)),
            justify="center",
            fill="#5c4500",
        )
        for item in [self.box, self.fold_line, self.text_item]:
            self.canvas.tag_raise(item)

    def update_position(self):
        self.create_visual()

    def delete(self):
        for item_name in ("box", "fold_line", "text_item"):
            item = getattr(self, item_name, None)
            if item:
                self.canvas.delete(item)
                setattr(self, item_name, None)

class StateNode:
    """Represents a state in a state diagram"""
    def __init__(self, canvas, x, y, name="State", tool=None, state_kind="normal"):
        self.canvas = canvas
        self.tool = tool
        self.x = x
        self.y = y
        self.name = name
        self.state_kind = state_kind
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

        if self.state_kind in {"start", "end"}:
            radius = max(10, int(12 * zoom_level))
            outer_radius = radius + max(4, int(5 * zoom_level))
            center_x = self.x + outer_radius
            center_y = self.y + outer_radius
            self.width = (outer_radius * 2) / zoom_level
            self.height = (outer_radius * 2) / zoom_level
            if self.state_kind == "end":
                self.box = self.canvas.create_oval(
                    center_x - outer_radius, center_y - outer_radius,
                    center_x + outer_radius, center_y + outer_radius,
                    fill="white", outline="black", width=max(1, int(2 * zoom_level))
                )
                self.text_item = self.canvas.create_oval(
                    center_x - radius, center_y - radius,
                    center_x + radius, center_y + radius,
                    fill="black", outline="black", width=max(1, int(1 * zoom_level))
                )
            else:
                self.box = self.canvas.create_oval(
                    center_x - radius, center_y - radius,
                    center_x + radius, center_y + radius,
                    fill="black", outline="black", width=max(1, int(1 * zoom_level))
                )
                self.text_item = None
            for item in [self.box] + ([self.text_item] if self.text_item else []):
                self.canvas.tag_bind(item, "<Button-1>", self.on_press)
                self.canvas.tag_bind(item, "<B1-Motion>", self.on_drag)
                self.canvas.tag_bind(item, "<ButtonRelease-1>", self.on_release)
            return
        
        font_size = max(8, int(10 * zoom_level))
        text_width, text_height = measure_wrapped_text(
            self.canvas,
            self.name,
            ("Arial", font_size, "bold"),
            self.width * zoom_level * 0.78,
            minimum_width=max(70, int(76 * zoom_level)),
            max_width=max(180, int(220 * zoom_level)),
        )
        w = max(self.width * zoom_level, text_width + max(24, int(28 * zoom_level)))
        h = max(self.height * zoom_level, text_height + max(18, int(22 * zoom_level)))
        self.width = max(90, w / zoom_level)
        self.height = max(50, h / zoom_level)

        # Draw rounded rectangle for state
        self.box = create_rounded_rectangle(
            self.canvas,
            self.x, self.y, self.x + w, self.y + h,
            radius=max(12, int(16 * zoom_level)),
            fill="lightgreen", outline="black", width=max(1, int(2 * zoom_level))
        )
        
        self.text_item = self.canvas.create_text(
            self.x + w/2, self.y + h/2,
            text=self.name,
            font=("Arial", font_size, "bold"),
            width=max(50, int(text_width)),
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
        if self.state_kind in {"start", "end"}:
            return "break"
        new_name = simpledialog.askstring("Edit State", "Enter state name:", initialvalue=self.name)
        if new_name:
            self.name = new_name
            self.create_visual()
            if self.tool:
                self.tool.update_relationships()
                self.tool.update_scroll_region()
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
        if self.text_item:
            self.canvas.delete(self.text_item)

class EREntity:
    """Represents an entity in an ER diagram"""
    def __init__(self, canvas, x, y, name="Entity", tool=None):
        self.canvas = canvas
        self.tool = tool
        self.x = x
        self.y = y
        self.name = name
        self.entity_id = name.replace(" ", "_").upper()
        self.entity_alias = None
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
        
        font_size = max(8, int(10 * zoom_level))
        text_width, text_height = measure_wrapped_text(
            self.canvas,
            self.name,
            ("Arial", font_size, "bold"),
            self.width * zoom_level * 0.78,
            minimum_width=max(70, int(76 * zoom_level)),
            max_width=max(200, int(240 * zoom_level)),
        )
        w = max(self.width * zoom_level, text_width + max(26, int(30 * zoom_level)))
        h = max(self.height * zoom_level, text_height + max(24, int(28 * zoom_level)))
        self.width = max(100, w / zoom_level)
        self.height = max(60, h / zoom_level)

        # Draw entity box
        self.box = self.canvas.create_rectangle(
            self.x, self.y, self.x + w, self.y + h,
            fill="lightyellow", outline="black", width=max(1, int(2 * zoom_level))
        )
        
        self.text_item = self.canvas.create_text(
            self.x + w/2, self.y + h/2,
            text=self.name,
            font=("Arial", font_size, "bold"),
            width=max(50, int(text_width)),
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
            self.create_visual()
            if self.tool:
                self.tool.update_relationships()
                self.tool.update_scroll_region()
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

    def get_label_side(self):
        from_id = getattr(self.from_node, "node_id", "")
        to_id = getattr(self.to_node, "node_id", "")
        return 1 if from_id <= to_id else -1

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
            label_side = self.get_label_side()
            mid_x, mid_y = get_perpendicular_label_position(
                from_point, to_point, int(12 * zoom_level), side=label_side
            )
            self.label_text = self.canvas.create_text(
                mid_x, mid_y, text=self.label,
                font=("Arial", max(8, int(9 * zoom_level))), fill="#0c2461"
            )
            position_connection_label(
                self.canvas,
                self.label_text,
                from_point,
                to_point,
                [
                    self.canvas.bbox(self.from_node.shape_item),
                    self.canvas.bbox(self.to_node.shape_item),
                ],
                preferred_side=label_side,
                base_offset=int(12 * zoom_level),
                padding=2,
                line_item=self.line,
            )
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
        self.arrow_symbol = None
        self.directives_before = []
        self.selected = False
        self.visual_items = []
        self.line = None
        self.label_text = None
        self.create_visual()

    def get_y(self):
        zoom_level = self.tool.zoom_level if self.tool and hasattr(self.tool, 'zoom_level') else 1.0
        top = max(self.from_actor.y + self.from_actor.height * zoom_level, self.to_actor.y + self.to_actor.height * zoom_level)
        return top + ((self.index + 1) * 50 * zoom_level)

    def get_effective_symbol(self):
        if self.arrow_symbol:
            return self.arrow_symbol
        arrow_map = {
            "sync": "->>",
            "async": "-->",
            "return": "-->>",
            "note": "--",
        }
        return arrow_map.get(self.msg_type, "->>")

    def get_arrow_style(self):
        symbol = self.get_effective_symbol()
        central_start = symbol.startswith("()")
        central_end = symbol.endswith("()")
        core_symbol = symbol
        if central_start:
            core_symbol = core_symbol[2:]
        if central_end:
            core_symbol = core_symbol[:-2]

        marker_map = {
            "->>": (None, "filled"),
            "-->>": (None, "filled"),
            "<<->>": ("filled", "filled"),
            "<<-->>": ("filled", "filled"),
            "->": (None, None),
            "-->": (None, None),
            "-)": (None, "open"),
            "--)": (None, "open"),
            "-x": (None, "cross"),
            "--x": (None, "cross"),
            "-|\\": (None, "half-top-filled"),
            "--|\\": (None, "half-top-filled"),
            "-|/": (None, "half-bottom-filled"),
            "--|/": (None, "half-bottom-filled"),
            "-\\\\": (None, "half-top-stick"),
            "--\\\\": (None, "half-top-stick"),
            "-//": (None, "half-bottom-stick"),
            "--//": (None, "half-bottom-stick"),
            "/|-": ("half-top-filled", None),
            "/|--": ("half-top-filled", None),
            "\\|-": ("half-bottom-filled", None),
            "\\|--": ("half-bottom-filled", None),
            "//-": ("half-top-stick", None),
            "//--": ("half-top-stick", None),
            "\\\\-": ("half-bottom-stick", None),
            "\\\\--": ("half-bottom-stick", None),
        }
        start_marker, end_marker = marker_map.get(core_symbol, (None, None))
        return {
            "symbol": symbol,
            "core_symbol": core_symbol,
            "central_start": central_start,
            "central_end": central_end,
            "dotted": "--" in core_symbol,
            "start_marker": start_marker,
            "end_marker": end_marker,
        }

    def register_item(self, item):
        self.visual_items.append(item)
        return item

    def bind_item(self, item):
        self.canvas.tag_bind(item, "<Button-1>", self.on_click)
        self.canvas.tag_bind(item, "<Double-Button-1>", self.on_double_click)

    def lower_item(self, item):
        self.canvas.tag_lower(item)
        if self.tool and self.canvas.find_withtag("grid"):
            self.canvas.tag_raise(item, "grid")

    def get_marker_extent(self, marker_kind, zoom_level):
        if marker_kind == "filled":
            return max(10, int(10 * zoom_level))
        if marker_kind in {"open", "cross"}:
            return max(9, int(9 * zoom_level))
        return max(8, int(8 * zoom_level))

    def draw_central_circle(self, center_x, y, radius, color, width):
        return self.register_item(
            self.canvas.create_oval(
                center_x - radius,
                y - radius,
                center_x + radius,
                y + radius,
                outline=color,
                width=width,
            )
        )

    def draw_marker(self, marker_kind, tip_x, y, tip_direction, color, width, zoom_level):
        size = self.get_marker_extent(marker_kind, zoom_level)
        half = max(4, int(4 * zoom_level))

        if marker_kind == "filled":
            points = [
                tip_x,
                y,
                tip_x - (tip_direction * size),
                y - half,
                tip_x - (tip_direction * size),
                y + half,
            ]
            return [self.register_item(self.canvas.create_polygon(points, fill=color, outline=color, width=1))]

        if marker_kind == "open":
            return [
                self.register_item(
                    self.canvas.create_line(
                        tip_x - (tip_direction * size),
                        y - half,
                        tip_x,
                        y,
                        fill=color,
                        width=width,
                    )
                ),
                self.register_item(
                    self.canvas.create_line(
                        tip_x - (tip_direction * size),
                        y + half,
                        tip_x,
                        y,
                        fill=color,
                        width=width,
                    )
                ),
            ]

        if marker_kind == "cross":
            center_x = tip_x - (tip_direction * max(4, int(4 * zoom_level)))
            return [
                self.register_item(
                    self.canvas.create_line(
                        center_x - max(3, int(3 * zoom_level)),
                        y - half,
                        center_x + max(3, int(3 * zoom_level)),
                        y + half,
                        fill=color,
                        width=width,
                    )
                ),
                self.register_item(
                    self.canvas.create_line(
                        center_x - max(3, int(3 * zoom_level)),
                        y + half,
                        center_x + max(3, int(3 * zoom_level)),
                        y - half,
                        fill=color,
                        width=width,
                    )
                ),
            ]

        if marker_kind == "half-top-filled":
            points = [
                tip_x,
                y,
                tip_x - (tip_direction * size),
                y,
                tip_x - (tip_direction * size),
                y - half,
            ]
            return [self.register_item(self.canvas.create_polygon(points, fill=color, outline=color, width=1))]

        if marker_kind == "half-bottom-filled":
            points = [
                tip_x,
                y,
                tip_x - (tip_direction * size),
                y,
                tip_x - (tip_direction * size),
                y + half,
            ]
            return [self.register_item(self.canvas.create_polygon(points, fill=color, outline=color, width=1))]

        if marker_kind == "half-top-stick":
            return [
                self.register_item(
                    self.canvas.create_line(
                        tip_x - (tip_direction * size),
                        y - half,
                        tip_x,
                        y,
                        fill=color,
                        width=width,
                    )
                )
            ]

        if marker_kind == "half-bottom-stick":
            return [
                self.register_item(
                    self.canvas.create_line(
                        tip_x - (tip_direction * size),
                        y + half,
                        tip_x,
                        y,
                        fill=color,
                        width=width,
                    )
                )
            ]

        return []

    def create_visual(self):
        zoom_level = self.tool.zoom_level if self.tool and hasattr(self.tool, 'zoom_level') else 1.0
        from_x = self.from_actor.get_center()[0]
        to_x = self.to_actor.get_center()[0]
        y = self.get_y()
        color = "red" if self.selected else "#2d3436"
        width = max(1, int((3 if self.selected else 2) * zoom_level))
        self.delete()
        label_from_point = (from_x, y)
        label_to_point = (to_x, y)
        label_side = -1

        if self.msg_type == "note":
            self.line = self.register_item(
                self.canvas.create_line(from_x, y, to_x, y, fill=color, width=width, dash=(2, 4))
            )
            self.lower_item(self.line)
            self.bind_item(self.line)
        elif from_x == to_x:
            loop_width = max(40, int(50 * zoom_level))
            loop_drop = max(18, int(22 * zoom_level))
            style = self.get_arrow_style()
            dash = (6, 4) if style["dotted"] else None
            points = [
                from_x,
                y,
                from_x + loop_width,
                y,
                from_x + loop_width,
                y + loop_drop,
                from_x,
                y + loop_drop,
            ]
            self.line = self.register_item(
                self.canvas.create_line(*points, fill=color, width=width, dash=dash, smooth=False)
            )
            label_from_point = (from_x, y)
            label_to_point = (from_x + loop_width, y)
            self.lower_item(self.line)
            self.bind_item(self.line)
            for item in self.draw_marker(
                style["end_marker"] or "filled",
                from_x,
                y + loop_drop,
                -1,
                color,
                width,
                zoom_level,
            ):
                self.lower_item(item)
                self.bind_item(item)
        else:
            style = self.get_arrow_style()
            dash = (6, 4) if style["dotted"] else None
            direction = 1 if to_x >= from_x else -1
            circle_radius = max(4, int(5 * zoom_level))

            source_anchor = from_x + (direction * (circle_radius + 2) if style["central_start"] else 0)
            target_anchor = to_x - (direction * (circle_radius + 2) if style["central_end"] else 0)
            start_extent = self.get_marker_extent(style["start_marker"], zoom_level) if style["start_marker"] else 0
            end_extent = self.get_marker_extent(style["end_marker"], zoom_level) if style["end_marker"] else 0

            line_start_x = source_anchor + (direction * start_extent)
            line_end_x = target_anchor - (direction * end_extent)
            if direction > 0 and line_start_x > line_end_x:
                line_start_x = source_anchor
                line_end_x = target_anchor
            if direction < 0 and line_start_x < line_end_x:
                line_start_x = source_anchor
                line_end_x = target_anchor

            self.line = self.register_item(
                self.canvas.create_line(line_start_x, y, line_end_x, y, fill=color, width=width, dash=dash)
            )
            label_from_point = (line_start_x, y)
            label_to_point = (line_end_x, y)
            self.lower_item(self.line)
            self.bind_item(self.line)

            if style["central_start"]:
                circle = self.draw_central_circle(from_x, y, circle_radius, color, width)
                self.lower_item(circle)
                self.bind_item(circle)
            if style["central_end"]:
                circle = self.draw_central_circle(to_x, y, circle_radius, color, width)
                self.lower_item(circle)
                self.bind_item(circle)

            if style["start_marker"]:
                for item in self.draw_marker(
                    style["start_marker"],
                    source_anchor,
                    y,
                    -direction,
                    color,
                    width,
                    zoom_level,
                ):
                    self.lower_item(item)
                    self.bind_item(item)
            if style["end_marker"]:
                for item in self.draw_marker(
                    style["end_marker"],
                    target_anchor,
                    y,
                    direction,
                    color,
                    width,
                    zoom_level,
                ):
                    self.lower_item(item)
                    self.bind_item(item)

        label_fill = "#6c5ce7" if self.msg_type != "note" else "#b9770e"
        self.label_text = self.register_item(
            self.canvas.create_text(
                (label_from_point[0] + label_to_point[0]) / 2,
                y - (12 * zoom_level),
                text=self.label,
                font=("Arial", max(8, int(9 * zoom_level))),
                fill=label_fill,
            )
        )
        actor_obstacles = []
        for actor in self.tool.sequence_actors if self.tool else [self.from_actor, self.to_actor]:
            for item_name in ("box", "text_item"):
                obstacle_item = getattr(actor, item_name, None)
                if obstacle_item:
                    actor_obstacles.append(self.canvas.bbox(obstacle_item))
        position_connection_label(
            self.canvas,
            self.label_text,
            label_from_point,
            label_to_point,
            actor_obstacles,
            preferred_side=label_side,
            base_offset=int(12 * zoom_level),
            padding=2,
            line_item=self.line,
            exclude_items=self.visual_items,
        )
        self.bind_item(self.label_text)

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
        for item in self.visual_items:
            self.canvas.delete(item)
        self.visual_items = []
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
            position_connection_label(
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
                line_item=self.line,
            )
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
        self.raw_relation = None
        self.from_cardinality = None
        self.to_cardinality = None
        self.identifying = True
        self.selected = False
        self.line = None
        self.label_text = None
        self.from_card_text = None
        self.to_card_text = None
        self.create_visual()

    def cardinalities(self):
        if self.from_cardinality and self.to_cardinality:
            return self.from_cardinality, self.to_cardinality
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
        dash = None if self.identifying else (6, 4)

        self.line = self.canvas.create_line(
            from_point[0], from_point[1], to_point[0], to_point[1],
            fill=color, width=width, dash=dash
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
            position_connection_label(
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
                line_item=self.line,
            )
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
    def __init__(self, startup_file=None):
        self.root = tk.Tk()
        self.root.title("Mermaid Diagram Tool")
        self.root.geometry("1440x900")
        self.root.minsize(1280, 780)
        self.startup_file = self.resolve_startup_file(startup_file)
        
        self.diagram_type = "classDiagram"  # or "flowchart", "sequenceDiagram", "stateDiagram", "erDiagram"
        self.classes = []
        self.flowchart_nodes = []  # For flowchart mode
        self.flowchart_connections = []
        self.flowchart_direction = "TD"
        self.flowchart_preserved_lines = []
        self.sequence_actors = []  # For sequence diagram
        self.sequence_messages = []  # For sequence diagram
        self.sequence_notes = []
        self.sequence_directives = []
        self.sequence_export_rows = []
        self.state_nodes = []  # For state diagram
        self.state_transitions = []  # For state diagram
        self.state_preserved_lines = []
        self.er_entities = []  # For ER diagram
        self.er_relationships = []  # For ER diagram
        self.er_direction = None
        self.er_preserved_lines = []
        self.relationships = []
        self.class_preserved_lines = []
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
        self.canvas_svg_exports = {}
        self.palette_panel_visible = True
        self.preview_panel_visible = True
        self.top_controls_visible = True
        
        # Track changes and current file
        self.has_unsaved_changes = False
        self.current_file = None
        self.runtime_base_dir = get_runtime_base_dir()
        self.config_file = os.path.join(self.runtime_base_dir, "mermaid_tool_config.txt")
        self.debug_logging = False
        
        self.create_widgets()
        self.update_diagram_type_ui()
        
        # Set up window close handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Open an explicit startup file first, otherwise restore the last file.
        if not self.load_startup_diagram():
            self.load_last_diagram()

    def resolve_startup_file(self, startup_file):
        if not startup_file:
            return None
        return os.path.abspath(os.path.expanduser(startup_file))

    def load_startup_diagram(self):
        if not self.startup_file:
            return False
        return self.load_diagram_from_file(
            self.startup_file,
            prompt_for_unsaved=False,
            show_errors=True,
        )
        
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
        file_menu.add_separator()
        file_menu.add_command(label="Export PNG", command=self.export_png)
        file_menu.add_command(label="Export SVG", command=self.export_svg)

        layout_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Layout", menu=layout_menu)
        layout_menu.add_command(label="Auto Layout", command=self.apply_auto_layout)
        layout_menu.add_separator()
        layout_menu.add_command(label="Toggle Top Bar", command=self.toggle_top_controls)
        layout_menu.add_command(label="Toggle Tools Panel", command=self.toggle_palette_panel)
        layout_menu.add_command(label="Toggle Code Panel", command=self.toggle_preview_panel)
        layout_menu.add_command(label="Canvas Focus Mode", command=self.toggle_canvas_focus_mode)
        
        app_shell = tk.Frame(self.root, bg="#f3f6fb")
        app_shell.pack(fill=tk.BOTH, expand=True, padx=14, pady=14)

        header = tk.Frame(app_shell, bg="#f3f6fb")
        header.pack(fill=tk.X, pady=(0, 12))
        self.header = header

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
        self.toolbar_groups = []
        self._toolbar_layout_scheduled = False
        self.toolbar.bind("<Configure>", self.on_toolbar_configure)

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

        self.add_button = tk.Button(mode_tools, text="Add Class", command=self.add_primary_element, width=11)
        self.add_button.pack(side=tk.LEFT, padx=3, pady=2)
        self.delete_button = tk.Button(mode_tools, text="Delete", command=self.delete_selected, width=10)
        self.delete_button.pack(side=tk.LEFT, padx=3, pady=2)
        self.layout_button = tk.Button(mode_tools, text="Layout", command=self.apply_auto_layout, width=9)
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

        view_zoom_row = tk.Frame(zoom_tools, bg="#f7f9fc")
        view_zoom_row.pack(anchor=tk.W)
        tk.Label(
            view_zoom_row,
            text="Zoom",
            bg="#f7f9fc",
            fg="#243447",
            font=("Segoe UI", 9, "bold"),
        ).pack(side=tk.LEFT, padx=(0, 6), pady=2)
        self.zoom_out_button = tk.Button(view_zoom_row, text="-", command=self.zoom_out, width=3)
        self.zoom_out_button.pack(side=tk.LEFT, padx=2, pady=2)
        self.zoom_label = tk.Label(
            view_zoom_row,
            text="100%",
            bg="#f7f9fc",
            width=4,
            fg="#243447",
            font=("Segoe UI Semibold", 9),
        )
        self.zoom_label.pack(side=tk.LEFT, padx=2, pady=2)
        self.zoom_in_button = tk.Button(view_zoom_row, text="+", command=self.zoom_in, width=3)
        self.zoom_in_button.pack(side=tk.LEFT, padx=2, pady=2)
        self.zoom_reset_button = tk.Button(view_zoom_row, text="1:1", command=self.zoom_reset, width=4)
        self.zoom_reset_button.pack(side=tk.LEFT, padx=(2, 8), pady=2)

        self.show_grid = tk.BooleanVar(value=False)
        self.grid_check = tk.Checkbutton(
            view_zoom_row,
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
        self.summary_card = summary_card
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
        self.palette_shell = palette_shell
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
        self.center_column = center_column

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
        self.preview_panel = preview_panel

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
        self.render_code_button = tk.Button(action_row, text="Render Code", command=self.render_code_preview, width=11)
        self.render_code_button.pack(side=tk.LEFT, padx=(0, 6))
        self.copy_code_button = tk.Button(action_row, text="Copy Code", command=self.copy_mermaid_code, width=11)
        self.copy_code_button.pack(side=tk.LEFT, padx=(0, 6))
        self.refresh_code_button = tk.Button(action_row, text="Sync", command=lambda: self.refresh_code_preview(force=True), width=9)
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
        self.code_preview.bind("<<Modified>>", self.on_code_preview_modified)
        code_scroll.config(command=self.code_preview.yview)
        code_x_scroll.config(command=self.code_preview.xview)
        self.code_preview_dirty = False
        self._updating_code_preview = False

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
            "Class sample": os.path.join("samples", "sample_class_diagram.md"),
            "Flowchart sample": os.path.join("samples", "sample_flowchart.md"),
            "Sequence sample": os.path.join("samples", "sample_sequence_diagram.md"),
            "State sample": os.path.join("samples", "sample_state_diagram.md"),
            "ER sample": os.path.join("samples", "sample_er_diagram.md"),
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
        self.update_panel_toggle_buttons()
        self.schedule_toolbar_layout()
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
        self.toolbar_groups.append(frame)
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

    def on_toolbar_configure(self, event=None):
        self.schedule_toolbar_layout()

    def schedule_toolbar_layout(self):
        if self._toolbar_layout_scheduled or not hasattr(self, "toolbar"):
            return
        self._toolbar_layout_scheduled = True
        self.root.after_idle(self.update_toolbar_layout)

    def update_toolbar_layout(self):
        self._toolbar_layout_scheduled = False
        if not getattr(self, "top_controls_visible", True):
            return
        if not hasattr(self, "toolbar_groups"):
            return

        self.toolbar.update_idletasks()
        available_width = max(320, self.toolbar.winfo_width() - 24)
        for column in range(len(self.toolbar_groups) + 1):
            self.toolbar.grid_columnconfigure(column, weight=0)
        row = 0
        col = 0
        used_width = 0
        for group in self.toolbar_groups:
            group.update_idletasks()
            group_width = group.winfo_reqwidth()
            if col > 0 and used_width + group_width > available_width:
                row += 1
                col = 0
                used_width = 0
            group.grid(row=row, column=col, padx=(0, 10), pady=(0, 10 if row == 0 else 0), sticky="nw")
            used_width += group_width + 10
            col += 1

        for extra_row in range(row + 1, 6):
            self.toolbar.grid_rowconfigure(extra_row, weight=0)
        for grid_row in range(row + 1):
            self.toolbar.grid_rowconfigure(grid_row, weight=0)
        self.toolbar.grid_columnconfigure(max(col - 1, 0), weight=1)
    
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
            (self.add_button, "primary"),
            (self.delete_button, "warning"),
            (self.layout_button, "accent"),
            (self.rel_button, "neutral"),
            (self.zoom_out_button, "subtle"),
            (self.zoom_in_button, "subtle"),
            (self.zoom_reset_button, "subtle"),
            (self.render_code_button, "primary"),
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

    def set_code_preview_text(self, preview_text, mark_clean=True):
        self._updating_code_preview = True
        self.code_preview.edit_modified(False)
        self.code_preview.delete("1.0", tk.END)
        self.code_preview.insert("1.0", preview_text)
        self.code_preview.edit_modified(False)
        self._updating_code_preview = False
        self.code_preview_dirty = not mark_clean

    def on_code_preview_modified(self, event=None):
        if self._updating_code_preview:
            self.code_preview.edit_modified(False)
            return
        self.code_preview_dirty = True
        self.code_preview.edit_modified(False)
        if hasattr(self, "code_meta_label"):
            current_text = self.code_preview.get("1.0", tk.END).rstrip("\n")
            line_count = len(current_text.splitlines()) if current_text else 0
            self.code_meta_label.config(
                text=f"{self.get_diagram_display_name()} · {line_count} line{'s' if line_count != 1 else ''} · edited"
            )

    def refresh_code_preview(self, force=False):
        if not hasattr(self, "code_preview"):
            return
        if self.code_preview_dirty and not force:
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

        self.set_code_preview_text(preview_text, mark_clean=True)

    def update_panel_toggle_buttons(self):
        if hasattr(self, "toggle_tools_button"):
            self.toggle_tools_button.config(
                text="Hide Tools" if self.palette_panel_visible else "Show Tools",
                width=11,
            )
        if hasattr(self, "toggle_code_button"):
            self.toggle_code_button.config(
                text="Hide Code" if self.preview_panel_visible else "Show Code",
                width=11,
            )
        if hasattr(self, "focus_canvas_button"):
            is_focused = not self.palette_panel_visible and not self.preview_panel_visible
            self.focus_canvas_button.config(
                text="Restore Panels" if is_focused else "Canvas Focus",
                width=12,
            )

    def toggle_top_controls(self):
        self.top_controls_visible = not self.top_controls_visible
        if self.top_controls_visible:
            self.toolbar.pack(fill=tk.X, pady=(0, 12), after=self.header)
            self.summary_card.pack(fill=tk.X, pady=(0, 12), after=self.toolbar)
            self.schedule_toolbar_layout()
        else:
            self.toolbar.pack_forget()
            self.summary_card.pack_forget()
        self.update_panel_toggle_buttons()

    def toggle_palette_panel(self):
        self.palette_panel_visible = not self.palette_panel_visible
        if self.palette_panel_visible:
            self.palette_shell.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12), before=self.center_column)
        else:
            self.palette_shell.pack_forget()
        self.update_panel_toggle_buttons()

    def toggle_preview_panel(self):
        self.preview_panel_visible = not self.preview_panel_visible
        if self.preview_panel_visible:
            self.preview_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(12, 0))
        else:
            self.preview_panel.pack_forget()
        self.update_panel_toggle_buttons()

    def toggle_canvas_focus_mode(self):
        should_focus = self.palette_panel_visible or self.preview_panel_visible
        self.palette_panel_visible = not should_focus
        self.preview_panel_visible = not should_focus

        if self.palette_panel_visible:
            self.palette_shell.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12), before=self.center_column)
        else:
            self.palette_shell.pack_forget()

        if self.preview_panel_visible:
            self.preview_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(12, 0))
        else:
            self.preview_panel.pack_forget()

        self.update_panel_toggle_buttons()

    def copy_mermaid_code(self):
        mermaid_code = self.code_preview.get("1.0", tk.END).rstrip("\n")
        if not mermaid_code:
            try:
                mermaid_code = self.generate_mermaid()
            except Exception as exc:
                messagebox.showerror("Copy Mermaid Code", f"Could not generate Mermaid code: {exc}")
                return

        self.root.clipboard_clear()
        self.root.clipboard_append(mermaid_code)
        self.update_status("Copied Mermaid code to clipboard")

    def render_code_preview(self):
        code_text = self.code_preview.get("1.0", tk.END).strip()
        if not code_text:
            messagebox.showinfo("Render Mermaid", "Enter Mermaid code in the editor first.")
            return

        if self.has_unsaved_changes:
            response = messagebox.askyesnocancel(
                "Unsaved Diagram Changes",
                "Rendering code will replace the current visual diagram. Save your current changes first?"
            )
            if response is None:
                return
            if response:
                self.save_mermaid()
                if self.has_unsaved_changes:
                    return

        try:
            self.set_zoom_level(1.0)
            self.parse_mermaid(code_text, apply_auto_layout=True)
            self.current_file = None
            self.mark_as_changed()
            self.code_preview_dirty = False
            self.refresh_code_preview(force=True)
            self.update_status("Rendered Mermaid code from editor")
        except Exception as exc:
            messagebox.showerror("Render Mermaid", f"Could not render Mermaid code:\n{exc}")

    def load_sample_diagram(self, sample_file):
        sample_path = os.path.join(self.runtime_base_dir, sample_file)
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
                create_rounded_rectangle(
                    icon_canvas,
                    18, 10, 98, 34,
                    radius=10,
                    fill=color,
                    outline="black",
                    width=2,
                )
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
        self.select_new_item(node, f"Added {shape_type} node")

        self.update_scroll_region()
        self.ensure_grid_behind()
        self.mark_as_changed()

    def add_sequence_actor(self):
        """Add a sequence diagram actor"""
        if self.diagram_type != "sequenceDiagram":
            self.update_status("Actors can only be added in sequence diagrams")
            return

        x = 100 + len(self.sequence_actors) * 150
        y = 50
        actor = SequenceActor(self.canvas, x, y, f"Actor{len(self.sequence_actors) + 1}", self)
        self.sequence_actors.append(actor)
        self.select_new_item(actor, "Added actor")
        self.update_scroll_region()
        self.mark_as_changed()

    def add_state_node(self):
        """Add a state diagram node"""
        if self.diagram_type != "stateDiagram":
            self.update_status("States can only be added in state diagrams")
            return

        x = 150 + (len(self.state_nodes) % 3) * 200
        y = 150 + (len(self.state_nodes) // 3) * 120
        state = StateNode(self.canvas, x, y, f"State{len(self.state_nodes) + 1}", self)
        self.state_nodes.append(state)
        self.select_new_item(state, "Added state")
        self.update_scroll_region()
        self.mark_as_changed()

    def add_er_entity(self):
        """Add an ER diagram entity"""
        if self.diagram_type != "erDiagram":
            self.update_status("Entities can only be added in ER diagrams")
            return

        x = 150 + (len(self.er_entities) % 3) * 200
        y = 150 + (len(self.er_entities) // 3) * 150
        entity = EREntity(self.canvas, x, y, f"Entity{len(self.er_entities) + 1}", self)
        self.er_entities.append(entity)
        self.select_new_item(entity, "Added entity")
        self.update_scroll_region()
        self.mark_as_changed()
        
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
        selection_description = self.get_selected_visual_description()
        if selection_description:
            return f"Selected: {selection_description}. Double-click to edit. Delete removes the current selection."
        return f"Right-click empty space to add a {self.get_primary_element_name()}. Drag to reposition. Delete removes the current selection."

    def refresh_ui_feedback(self):
        selection_description = self.get_selected_visual_description()
        if hasattr(self, 'summary_label'):
            summary_text = (
                f"{self.get_diagram_display_name()}  |  "
                f"{len(self.get_active_node_collection())} {self.get_primary_element_plural()}  |  "
                f"{len(self.get_active_connection_collection())} {self.get_short_connector_name()}  |  "
                f"Zoom {int(self.zoom_level * 100)}%"
            )
            if selection_description:
                summary_text += f"  |  Selected {selection_description}"
            self.summary_label.config(
                text=summary_text
            )
        if hasattr(self, 'mode_hint_label'):
            self.mode_hint_label.config(text=self.get_mode_hint_text())
        if hasattr(self, 'info_banner'):
            shortcut_hint = "Esc cancels connector mode" if self.relationship_mode else "Right-click empty space to add an element quickly"
            self.info_banner.config(
                text=f"{self.current_status_message}   |   {shortcut_hint}",
                bg="#eef7ef" if self.relationship_mode else "#eef5ff",
                fg="#244b34" if self.relationship_mode else "#1e3a5f",
            )
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

    def get_selected_visual_description(self):
        if self.selected_class:
            return f"class {self.selected_class.name}"
        if self.selected_node:
            return f"node {self.selected_node.node_id}"
        if self.selected_item:
            if hasattr(self.selected_item, "name"):
                return f"{self.get_primary_element_name()} {self.selected_item.name}"
            if hasattr(self.selected_item, "node_id"):
                return f"{self.get_primary_element_name()} {self.selected_item.node_id}"
        for connection in self.get_all_connections():
            if getattr(connection, "selected", False):
                if hasattr(connection, "rel_type"):
                    return f"{connection.rel_type} {self.get_connector_name()}"
                if hasattr(connection, "conn_type"):
                    return f"{connection.conn_type} {self.get_connector_name()}"
                if hasattr(connection, "msg_type"):
                    return f"{connection.msg_type} {self.get_connector_name()}"
                return self.get_connector_name()
        return None

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

    def select_new_item(self, item, status_message=None):
        self.deselect_all_visuals()
        if hasattr(item, "select"):
            item.select()
        if isinstance(item, ClassBox):
            self.selected_class = item
        elif isinstance(item, FlowchartNode):
            self.selected_node = item
        else:
            self.selected_item = item
        self.canvas.focus_set()
        if status_message:
            self.update_status(status_message)
        else:
            self.refresh_ui_feedback()

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

    def is_canvas_position_empty(self, canvas_x, canvas_y):
        return self.find_active_node_at(canvas_x, canvas_y) is None

    def begin_canvas_pan(self, event):
        self.is_panning = True
        self.pan_start_x = event.x
        self.pan_start_y = event.y
        self.canvas.config(cursor="fleur")
        self.deselect_all_visuals()
        self.update_status("Pan mode - drag to move diagram")

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
        for note in self.sequence_notes:
            note.update_position()
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
        self.select_new_item(class_box, f"Added class {class_box.name}")

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
        self.select_new_item(node, f"Added node {node.node_id}")

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
            self.layout_button.config(state=tk.NORMAL)
        elif self.diagram_type == "sequenceDiagram":
            self.add_button.config(text="Add Actor")
            self.create_sequence_palette()
            rel_values = ["sync", "async", "return"]
            rel_label = "Message:"
            self.layout_button.config(state=tk.NORMAL)
        elif self.diagram_type == "stateDiagram":
            self.add_button.config(text="Add State")
            self.create_state_palette()
            rel_values = ["transition"]
            rel_label = "State:"
            self.layout_button.config(state=tk.NORMAL)
        elif self.diagram_type == "erDiagram":
            self.add_button.config(text="Add Entity")
            self.create_er_palette()
            rel_values = ["one-to-one", "one-to-many", "many-to-many"]
            rel_label = "ER:"
            self.layout_button.config(state=tk.NORMAL)
        else:
            self.add_button.config(text="Add Class")
            self.create_uml_palette()
            rel_values = ["association", "inheritance", "composition", "aggregation", "dependency", "realization"]
            rel_label = "Class:"
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
                self.select_new_item(clicked_class, f"Selected class: {clicked_class.name}")

            elif clicked_relationship:
                # Clicked on a relationship - select it
                self.is_panning = False
                self.deselect_all_visuals()
                clicked_relationship.select()
                self.update_status(f"Selected {clicked_relationship.rel_type} relationship - click a relationship type in the palette to change it")

            else:
                if self.is_canvas_position_empty(canvas_x, canvas_y):
                    self.begin_canvas_pan(event)
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
        
        self.canvas.config(cursor="hand2" if not self.is_canvas_position_empty(canvas_x, canvas_y) else "")
    
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
        self.select_new_item(class_box, f"Added class {class_box.name}")

        self.update_scroll_region()
        self.ensure_grid_behind()
        self.mark_as_changed()

    def add_primary_element_at_position(self, x, y):
        if self.diagram_type == "flowchart":
            node = FlowchartNode(self.canvas, x, y, f"node{len(self.flowchart_nodes) + 1}", f"Node {len(self.flowchart_nodes) + 1}", "rectangle", self)
            self.flowchart_nodes.append(node)
            self.select_new_item(node, f"Added node {node.node_id}")
        elif self.diagram_type == "sequenceDiagram":
            actor = SequenceActor(self.canvas, x, y, f"Actor{len(self.sequence_actors) + 1}", self)
            self.sequence_actors.append(actor)
            self.select_new_item(actor, "Added actor")
        elif self.diagram_type == "stateDiagram":
            state = StateNode(self.canvas, x, y, f"State{len(self.state_nodes) + 1}", self)
            self.state_nodes.append(state)
            self.select_new_item(state, "Added state")
        elif self.diagram_type == "erDiagram":
            entity = EREntity(self.canvas, x, y, f"Entity{len(self.er_entities) + 1}", self)
            self.er_entities.append(entity)
            self.select_new_item(entity, "Added entity")
        else:
            self.add_class_at_position(x, y)
            return

        self.update_scroll_region()
        self.ensure_grid_behind()
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
            self.update_status("Deleted selection")
            
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
        bbox = self.get_content_bbox()

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
            scroll_region = (0, 0, 2000, 2000)

        self.canvas.configure(scrollregion=scroll_region)

        if hasattr(self, 'show_grid') and self.show_grid.get():
            if self.should_redraw_grid(scroll_region):
                self.draw_grid()
                self._last_grid_scroll_region = scroll_region
            self.canvas.after_idle(self.ensure_grid_behind)

    def get_content_bbox(self):
        """Return the bbox of all non-grid canvas items."""
        items = self.canvas.find_all()
        non_grid_items = [item for item in items if "grid" not in self.canvas.gettags(item)]
        if not non_grid_items:
            return None

        boxes = [self.canvas.bbox(item) for item in non_grid_items]
        boxes = [box for box in boxes if box]
        if not boxes:
            return None

        x1 = min(box[0] for box in boxes)
        y1 = min(box[1] for box in boxes)
        x2 = max(box[2] for box in boxes)
        y2 = max(box[3] for box in boxes)
        return (x1, y1, x2, y2)

    def should_redraw_grid(self, scroll_region, tolerance=120):
        """Redraw the grid only when the scrollable area changes meaningfully."""
        previous_region = getattr(self, "_last_grid_scroll_region", None)
        if previous_region is None:
            return True

        return any(
            abs(current - previous) > tolerance
            for current, previous in zip(scroll_region, previous_region)
        )
    
    def toggle_grid(self):
        """Toggle grid visibility"""
        if self.show_grid.get():
            self.draw_grid()
            scroll_region = self.canvas.cget("scrollregion").split()
            if len(scroll_region) == 4:
                self._last_grid_scroll_region = tuple(map(float, scroll_region))
            self.canvas.after_idle(self.ensure_grid_behind)
        else:
            self.hide_grid()
            if hasattr(self, '_last_grid_scroll_region'):
                delattr(self, '_last_grid_scroll_region')
    
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
        if hasattr(self, '_last_grid_scroll_region'):
            delattr(self, '_last_grid_scroll_region')
    
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

    def get_export_base_name(self):
        if self.current_file:
            return os.path.splitext(os.path.basename(self.current_file))[0]
        return f"{self.diagram_type or 'diagram'}_export"

    def get_export_bounds(self, padding=24):
        bbox = self.get_content_bbox()
        if not bbox:
            return None
        x1, y1, x2, y2 = bbox
        return (
            int(math.floor(x1 - padding)),
            int(math.floor(y1 - padding)),
            int(math.ceil(x2 + padding)),
            int(math.ceil(y2 + padding)),
        )

    def get_export_items(self):
        return [item for item in self.canvas.find_all() if "grid" not in self.canvas.gettags(item)]

    def export_png(self):
        self.export_diagram("png")

    def export_svg(self):
        self.export_diagram("svg")

    def export_diagram(self, export_format):
        if export_format not in {"png", "svg"}:
            messagebox.showerror("Export Error", f"Unsupported export format: {export_format}")
            return

        export_bounds = self.get_export_bounds()
        if not export_bounds:
            messagebox.showinfo("Export", "There is nothing on the canvas to export yet.")
            return

        default_name = f"{self.get_export_base_name()}.{export_format}"
        filename = filedialog.asksaveasfilename(
            defaultextension=f".{export_format}",
            initialfile=default_name,
            filetypes=[(f"{export_format.upper()} files", f"*.{export_format}"), ("All files", "*.*")],
        )
        if not filename:
            return

        try:
            self.canvas.update_idletasks()
            if export_format == "svg":
                self.save_canvas_as_svg(filename, export_bounds)
            else:
                self.save_canvas_as_png(filename, export_bounds)
            self.update_status(f"Exported {os.path.basename(filename)}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export diagram: {str(e)}")

    def parse_dash_pattern(self, dash_value):
        text = (dash_value or "").strip()
        if not text or text in {"{}", "none"}:
            return None
        values = [int(float(part)) for part in re.findall(r"-?\d+(?:\.\d+)?", text)]
        return values or None

    def parse_canvas_font(self, font_value):
        try:
            actual = tkfont.Font(font=font_value).actual()
            return {
                "family": actual.get("family", "Arial"),
                "size": abs(int(actual.get("size", 10))),
                "weight": actual.get("weight", "normal"),
                "slant": actual.get("slant", "roman"),
            }
        except Exception:
            parts = str(font_value).split()
            family = parts[0] if parts else "Arial"
            size = 10
            for part in parts[1:]:
                if str(part).lstrip("-").isdigit():
                    size = abs(int(part))
                    break
            return {"family": family, "size": size, "weight": "normal", "slant": "roman"}

    def get_export_font(self, font_value):
        if ImageFont is None:
            return None
        font_info = self.parse_canvas_font(font_value)
        size = max(8, int(font_info["size"]))
        candidates = []
        family = font_info["family"].lower().replace(" ", "")
        if "consolas" in family:
            candidates.extend(["consola.ttf", "cour.ttf"])
        elif "segoeui" in family:
            candidates.extend(["segoeui.ttf", "arial.ttf"])
        else:
            candidates.extend(["arial.ttf", "segoeui.ttf", "DejaVuSans.ttf"])
        for candidate in candidates:
            try:
                return ImageFont.truetype(candidate, size)
            except OSError:
                continue
        return ImageFont.load_default()

    def get_pil_color(self, value, default=None):
        text = (value or "").strip()
        if not text:
            return default
        if ImageColor is None:
            return default or text
        try:
            return ImageColor.getrgb(text)
        except ValueError:
            return default

    def svg_escape(self, value):
        return html.escape("" if value is None else str(value), quote=True)

    def svg_dash_attr(self, item):
        dash = self.parse_dash_pattern(self.canvas.itemcget(item, "dash"))
        if not dash:
            return ""
        return f' stroke-dasharray="{" ".join(str(part) for part in dash)}"'

    def svg_arrow_marker_attrs(self, item):
        arrow = self.canvas.itemcget(item, "arrow")
        if arrow == tk.FIRST:
            return ' marker-start="url(#arrowhead)"'
        if arrow == tk.LAST:
            return ' marker-end="url(#arrowhead)"'
        if arrow == tk.BOTH:
            return ' marker-start="url(#arrowhead)" marker-end="url(#arrowhead)"'
        return ""

    def canvas_arc_path(self, coords, start_degrees, extent_degrees, style):
        x1, y1, x2, y2 = coords
        rx = abs(x2 - x1) / 2
        ry = abs(y2 - y1) / 2
        if rx == 0 or ry == 0:
            return ""
        cx = min(x1, x2) + rx
        cy = min(y1, y2) + ry

        start_rad = math.radians(start_degrees)
        end_rad = math.radians(start_degrees + extent_degrees)

        start_x = cx + (rx * math.cos(start_rad))
        start_y = cy - (ry * math.sin(start_rad))
        end_x = cx + (rx * math.cos(end_rad))
        end_y = cy - (ry * math.sin(end_rad))
        large_arc = 1 if abs(extent_degrees) > 180 else 0
        sweep = 0 if extent_degrees >= 0 else 1

        path = f"M {start_x:.2f} {start_y:.2f} A {rx:.2f} {ry:.2f} 0 {large_arc} {sweep} {end_x:.2f} {end_y:.2f}"
        if style == tk.CHORD:
            path += " Z"
        elif style == tk.PIESLICE:
            path = f"M {cx:.2f} {cy:.2f} L {start_x:.2f} {start_y:.2f} " + path[1:] + " Z"
        return path

    def get_svg_export_markup_for_item(self, item, offset_x, offset_y):
        export_info = self.canvas_svg_exports.get(item)
        if not export_info:
            return ""
        svg_markup = export_info["svg_markup"]
        x = export_info["x"] + offset_x
        y = export_info["y"] + offset_y
        return re.sub(r"<svg\b", f'<svg x="{x:.2f}" y="{y:.2f}"', svg_markup, count=1)

    def build_svg_document(self, export_bounds):
        x1, y1, x2, y2 = export_bounds
        width = max(1, x2 - x1)
        height = max(1, y2 - y1)
        offset_x = -x1
        offset_y = -y1
        elements = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            "  <defs>",
            '    <marker id="arrowhead" markerWidth="10" markerHeight="8" refX="8" refY="4" orient="auto-start-reverse">',
            '      <path d="M 0 0 L 8 4 L 0 8 z" fill="context-stroke" />',
            "    </marker>",
            "  </defs>",
            f'  <rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff" />',
        ]

        for item in self.get_export_items():
            item_type = self.canvas.type(item)
            coords = self.canvas.coords(item)

            if item_type == "line":
                shifted = [coords[i] + (offset_x if i % 2 == 0 else offset_y) for i in range(len(coords))]
                stroke = self.canvas.itemcget(item, "fill") or "#000000"
                stroke_width = float(self.canvas.itemcget(item, "width") or 1)
                dash_attr = self.svg_dash_attr(item)
                marker_attr = self.svg_arrow_marker_attrs(item)
                if len(shifted) == 4:
                    elements.append(
                        f'  <line x1="{shifted[0]:.2f}" y1="{shifted[1]:.2f}" x2="{shifted[2]:.2f}" y2="{shifted[3]:.2f}"'
                        f' stroke="{self.svg_escape(stroke)}" stroke-width="{stroke_width:.2f}" fill="none"{dash_attr}{marker_attr} />'
                    )
                else:
                    points = " ".join(f"{shifted[i]:.2f},{shifted[i+1]:.2f}" for i in range(0, len(shifted), 2))
                    elements.append(
                        f'  <polyline points="{points}" stroke="{self.svg_escape(stroke)}" stroke-width="{stroke_width:.2f}" fill="none"{dash_attr}{marker_attr} />'
                    )
            elif item_type == "rectangle":
                x_a, y_a, x_b, y_b = coords
                fill = self.canvas.itemcget(item, "fill") or "none"
                stroke = self.canvas.itemcget(item, "outline") or "none"
                stroke_width = float(self.canvas.itemcget(item, "width") or 1)
                elements.append(
                    f'  <rect x="{x_a + offset_x:.2f}" y="{y_a + offset_y:.2f}" width="{abs(x_b - x_a):.2f}" height="{abs(y_b - y_a):.2f}"'
                    f' fill="{self.svg_escape(fill)}" stroke="{self.svg_escape(stroke)}" stroke-width="{stroke_width:.2f}" />'
                )
            elif item_type == "oval":
                x_a, y_a, x_b, y_b = coords
                fill = self.canvas.itemcget(item, "fill") or "none"
                stroke = self.canvas.itemcget(item, "outline") or "none"
                stroke_width = float(self.canvas.itemcget(item, "width") or 1)
                cx = (x_a + x_b) / 2 + offset_x
                cy = (y_a + y_b) / 2 + offset_y
                rx = abs(x_b - x_a) / 2
                ry = abs(y_b - y_a) / 2
                elements.append(
                    f'  <ellipse cx="{cx:.2f}" cy="{cy:.2f}" rx="{rx:.2f}" ry="{ry:.2f}"'
                    f' fill="{self.svg_escape(fill)}" stroke="{self.svg_escape(stroke)}" stroke-width="{stroke_width:.2f}" />'
                )
            elif item_type == "polygon":
                fill = self.canvas.itemcget(item, "fill") or "none"
                stroke = self.canvas.itemcget(item, "outline") or "none"
                stroke_width = float(self.canvas.itemcget(item, "width") or 1)
                points = " ".join(
                    f"{coords[i] + offset_x:.2f},{coords[i+1] + offset_y:.2f}" for i in range(0, len(coords), 2)
                )
                elements.append(
                    f'  <polygon points="{points}" fill="{self.svg_escape(fill)}" stroke="{self.svg_escape(stroke)}" stroke-width="{stroke_width:.2f}" />'
                )
            elif item_type == "arc":
                stroke = self.canvas.itemcget(item, "outline") or "#000000"
                fill = self.canvas.itemcget(item, "fill") or "none"
                stroke_width = float(self.canvas.itemcget(item, "width") or 1)
                start = float(self.canvas.itemcget(item, "start") or 0)
                extent = float(self.canvas.itemcget(item, "extent") or 0)
                style = self.canvas.itemcget(item, "style") or tk.PIESLICE
                shifted = [coords[0] + offset_x, coords[1] + offset_y, coords[2] + offset_x, coords[3] + offset_y]
                path = self.canvas_arc_path(shifted, start, extent, style)
                if path:
                    elements.append(
                        f'  <path d="{path}" fill="{self.svg_escape(fill)}" stroke="{self.svg_escape(stroke)}" stroke-width="{stroke_width:.2f}" />'
                    )
            elif item_type == "text":
                x, y = coords[0] + offset_x, coords[1] + offset_y
                text = self.canvas.itemcget(item, "text")
                fill = self.canvas.itemcget(item, "fill") or "#000000"
                font_info = self.parse_canvas_font(self.canvas.itemcget(item, "font"))
                anchor = self.canvas.itemcget(item, "anchor") or "center"
                anchor_map = {
                    "w": "start",
                    "sw": "start",
                    "nw": "start",
                    "e": "end",
                    "se": "end",
                    "ne": "end",
                }
                text_anchor = anchor_map.get(anchor, "middle")
                font_style = ' font-style="italic"' if font_info["slant"] == "italic" else ""
                font_weight = ' font-weight="bold"' if font_info["weight"] == "bold" else ""
                lines = text.splitlines() or [""]
                line_height = max(12, int(font_info["size"] * 1.25))
                base_y = y - ((len(lines) - 1) * line_height / 2)
                elements.append(
                    f'  <text x="{x:.2f}" y="{base_y:.2f}" fill="{self.svg_escape(fill)}" text-anchor="{text_anchor}"'
                    f' font-family="{self.svg_escape(font_info["family"])}" font-size="{font_info["size"]}"{font_weight}{font_style}>'
                )
                for index, line in enumerate(lines):
                    dy = 0 if index == 0 else line_height
                    elements.append(f'    <tspan x="{x:.2f}" dy="{dy}">{self.svg_escape(line)}</tspan>')
                elements.append("  </text>")
            elif item_type == "image":
                markup = self.get_svg_export_markup_for_item(item, offset_x, offset_y)
                if markup:
                    elements.append(f"  {markup}")

        elements.append("</svg>")
        return "\n".join(elements)

    def save_canvas_as_svg(self, filename, export_bounds):
        svg_document = self.build_svg_document(export_bounds)
        with open(filename, "w", encoding="utf-8") as handle:
            handle.write(svg_document)

    def draw_dashed_line_on_image(self, draw, start, end, dash_pattern, fill, width):
        if not dash_pattern:
            draw.line([start, end], fill=fill, width=width)
            return
        x1, y1 = start
        x2, y2 = end
        length = math.hypot(x2 - x1, y2 - y1)
        if length == 0:
            return
        dx = (x2 - x1) / length
        dy = (y2 - y1) / length
        pattern = dash_pattern if len(dash_pattern) > 1 else [dash_pattern[0], dash_pattern[0]]
        distance = 0.0
        draw_segment = True
        pattern_index = 0
        while distance < length:
            seg_length = pattern[pattern_index % len(pattern)]
            next_distance = min(length, distance + seg_length)
            if draw_segment:
                draw.line(
                    [
                        (x1 + dx * distance, y1 + dy * distance),
                        (x1 + dx * next_distance, y1 + dy * next_distance),
                    ],
                    fill=fill,
                    width=width,
                )
            draw_segment = not draw_segment
            pattern_index += 1
            distance = next_distance

    def draw_arrowhead_on_image(self, draw, tip, tail, fill, width):
        dx = tip[0] - tail[0]
        dy = tip[1] - tail[1]
        length = math.hypot(dx, dy)
        if length == 0:
            return
        ux = dx / length
        uy = dy / length
        size = max(8, int(width * 3))
        px = -uy
        py = ux
        base_x = tip[0] - ux * size
        base_y = tip[1] - uy * size
        points = [
            tip,
            (base_x + px * (size * 0.45), base_y + py * (size * 0.45)),
            (base_x - px * (size * 0.45), base_y - py * (size * 0.45)),
        ]
        draw.polygon(points, fill=fill)

    def render_canvas_to_png_image(self, export_bounds):
        if Image is None or ImageDraw is None:
            raise RuntimeError("Pillow is required for PNG export.")

        x1, y1, x2, y2 = export_bounds
        width = max(1, x2 - x1)
        height = max(1, y2 - y1)
        offset_x = -x1
        offset_y = -y1

        image = Image.new("RGBA", (width, height), (255, 255, 255, 255))
        draw = ImageDraw.Draw(image)

        for item in self.get_export_items():
            item_type = self.canvas.type(item)
            coords = self.canvas.coords(item)

            if item_type == "line":
                shifted = [(coords[i] + offset_x, coords[i + 1] + offset_y) for i in range(0, len(coords), 2)]
                fill = self.get_pil_color(self.canvas.itemcget(item, "fill"), (0, 0, 0))
                width_value = max(1, int(float(self.canvas.itemcget(item, "width") or 1)))
                dash = self.parse_dash_pattern(self.canvas.itemcget(item, "dash"))
                for start, end in zip(shifted, shifted[1:]):
                    self.draw_dashed_line_on_image(draw, start, end, dash, fill, width_value)
                arrow = self.canvas.itemcget(item, "arrow")
                if arrow in {tk.FIRST, tk.BOTH} and len(shifted) >= 2:
                    self.draw_arrowhead_on_image(draw, shifted[0], shifted[1], fill, width_value)
                if arrow in {tk.LAST, tk.BOTH} and len(shifted) >= 2:
                    self.draw_arrowhead_on_image(draw, shifted[-1], shifted[-2], fill, width_value)
            elif item_type == "rectangle":
                x_a, y_a, x_b, y_b = coords
                fill = self.get_pil_color(self.canvas.itemcget(item, "fill"))
                outline = self.get_pil_color(self.canvas.itemcget(item, "outline"), (0, 0, 0))
                width_value = max(1, int(float(self.canvas.itemcget(item, "width") or 1)))
                draw.rectangle(
                    [x_a + offset_x, y_a + offset_y, x_b + offset_x, y_b + offset_y],
                    fill=fill,
                    outline=outline,
                    width=width_value,
                )
            elif item_type == "oval":
                x_a, y_a, x_b, y_b = coords
                fill = self.get_pil_color(self.canvas.itemcget(item, "fill"))
                outline = self.get_pil_color(self.canvas.itemcget(item, "outline"), (0, 0, 0))
                width_value = max(1, int(float(self.canvas.itemcget(item, "width") or 1)))
                draw.ellipse(
                    [x_a + offset_x, y_a + offset_y, x_b + offset_x, y_b + offset_y],
                    fill=fill,
                    outline=outline,
                    width=width_value,
                )
            elif item_type == "polygon":
                points = [(coords[i] + offset_x, coords[i + 1] + offset_y) for i in range(0, len(coords), 2)]
                fill = self.get_pil_color(self.canvas.itemcget(item, "fill"))
                outline = self.get_pil_color(self.canvas.itemcget(item, "outline"), (0, 0, 0))
                draw.polygon(points, fill=fill, outline=outline)
            elif item_type == "arc":
                x_a, y_a, x_b, y_b = coords
                fill = self.get_pil_color(self.canvas.itemcget(item, "fill"))
                outline = self.get_pil_color(self.canvas.itemcget(item, "outline"), (0, 0, 0))
                width_value = max(1, int(float(self.canvas.itemcget(item, "width") or 1)))
                start = float(self.canvas.itemcget(item, "start") or 0)
                end = start + float(self.canvas.itemcget(item, "extent") or 0)
                style = self.canvas.itemcget(item, "style") or tk.PIESLICE
                box = [x_a + offset_x, y_a + offset_y, x_b + offset_x, y_b + offset_y]
                if style == tk.ARC:
                    draw.arc(box, start=start, end=end, fill=outline, width=width_value)
                elif style == tk.CHORD:
                    draw.chord(box, start=start, end=end, fill=fill, outline=outline, width=width_value)
                else:
                    draw.pieslice(box, start=start, end=end, fill=fill, outline=outline, width=width_value)
            elif item_type == "text":
                x, y = coords[0] + offset_x, coords[1] + offset_y
                text = self.canvas.itemcget(item, "text")
                fill = self.get_pil_color(self.canvas.itemcget(item, "fill"), (0, 0, 0))
                font = self.get_export_font(self.canvas.itemcget(item, "font"))
                anchor = self.canvas.itemcget(item, "anchor") or "center"
                anchor_map = {
                    "center": "mm",
                    "n": "ma",
                    "s": "md",
                    "e": "rm",
                    "w": "lm",
                    "ne": "ra",
                    "nw": "la",
                    "se": "rd",
                    "sw": "ld",
                }
                try:
                    draw.multiline_text((x, y), text, fill=fill, font=font, align="center", anchor=anchor_map.get(anchor, "mm"))
                except TypeError:
                    draw.multiline_text((x, y), text, fill=fill, font=font, align="center")
            elif item_type == "image":
                export_info = self.canvas_svg_exports.get(item)
                if not export_info:
                    continue
                temp_path = None
                try:
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as handle:
                        temp_path = handle.name
                    export_info["photo"].write(temp_path, format="png")
                    image_overlay = Image.open(temp_path).convert("RGBA")
                    x = int(round(export_info["x"] + offset_x))
                    y = int(round(export_info["y"] + offset_y))
                    image.alpha_composite(image_overlay, (x, y))
                finally:
                    if temp_path and os.path.exists(temp_path):
                        os.remove(temp_path)

        return image.convert("RGB")

    def save_canvas_as_png(self, filename, export_bounds):
        image = self.render_canvas_to_png_image(export_bounds)
        image.save(filename, format="PNG")
            
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
        self.flowchart_direction = "TD"
        self.flowchart_preserved_lines.clear()
        self.sequence_actors.clear()
        self.sequence_messages.clear()
        self.sequence_notes.clear()
        self.sequence_directives.clear()
        self.sequence_export_rows.clear()
        self.state_nodes.clear()
        self.state_transitions.clear()
        self.state_preserved_lines.clear()
        self.er_entities.clear()
        self.er_relationships.clear()
        self.er_direction = None
        self.er_preserved_lines.clear()
        self.class_preserved_lines.clear()
        self.canvas_svg_exports.clear()
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
            return self.parse_flowchart(mermaid_code, apply_auto_layout)
        if diagram_type == "sequenceDiagram":
            return self.parse_sequence_diagram(mermaid_code, apply_auto_layout)
        if diagram_type == "stateDiagram":
            return self.parse_state_diagram(mermaid_code, apply_auto_layout)
        if diagram_type == "erDiagram":
            return self.parse_er_diagram(mermaid_code, apply_auto_layout)
        return self.parse_class_diagram(mermaid_code, apply_auto_layout)

    def parse_flowchart_node_reference(self, reference, nodes_data):
        match = FLOWCHART_NODE_REFERENCE_RE.match(reference or "")
        if not match:
            return None
        node_id, circle_text, rounded_text, rect_text, diamond_text = match.groups()
        if circle_text is not None:
            nodes_data[node_id] = {'text': circle_text, 'shape': 'circle'}
        elif rounded_text is not None:
            nodes_data[node_id] = {'text': rounded_text, 'shape': 'rounded'}
        elif rect_text is not None:
            nodes_data[node_id] = {'text': rect_text, 'shape': 'rectangle'}
        elif diamond_text is not None:
            nodes_data[node_id] = {'text': diamond_text, 'shape': 'diamond'}
        elif node_id not in nodes_data:
            nodes_data[node_id] = {'text': node_id, 'shape': 'rectangle'}
        return node_id

    def parse_flowchart(self, mermaid_code, apply_auto_layout=True):
        """Parse flowchart code."""
        lines = [line.strip() for line in mermaid_code.split('\n') if line.strip()]
        
        nodes_data = {}
        connections = []
        self.flowchart_direction = "TD"
        self.flowchart_preserved_lines = []
        in_subgraph = False
        
        for line in lines:
            if line.startswith('flowchart') or line.startswith('graph'):
                parts = line.split()
                if len(parts) >= 2:
                    self.flowchart_direction = parts[1].upper()
                continue
            if line.startswith("%%"):
                self.flowchart_preserved_lines.append(line)
                continue
            if line.startswith("subgraph"):
                in_subgraph = True
                self.flowchart_preserved_lines.append(line)
                continue
            if in_subgraph:
                self.flowchart_preserved_lines.append(line)
                if line.lower() == "end":
                    in_subgraph = False
                continue
            
            # Parse connections: A --> B or A -->|label| B, including inline node refs
            conn_match = re.match(r'(.+?)\s*(-->|---|-\.->|==>)\s*(?:\|([^|]+)\|\s*)?(.+)', line)
            if conn_match:
                from_ref, conn_type, label, to_ref = conn_match.groups()
                from_node = self.parse_flowchart_node_reference(from_ref.strip(), nodes_data)
                to_node = self.parse_flowchart_node_reference(to_ref.strip(), nodes_data)
                if from_node and to_node:
                    flow_type_map = {
                        "-->": "arrow",
                        "---": "line",
                        "-.->": "dotted",
                        "==>": "thick"
                    }
                    connections.append((from_node, to_node, flow_type_map.get(conn_type, "arrow"), (label or "").strip()))
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
            self.flowchart_preserved_lines.append(line)

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

        if apply_auto_layout:
            self.apply_auto_layout()
        else:
            self.update_scroll_region()
        self.update_status(f"Loaded flowchart with {len(self.flowchart_nodes)} nodes")

    def parse_sequence_diagram(self, mermaid_code, apply_auto_layout=True):
        lines = [line.strip() for line in mermaid_code.split('\n') if line.strip()]
        actor_lookup = {}
        message_rows = []
        note_rows = []
        pending_directives = []
        self.sequence_export_rows = []
        preserved_block = []
        block_depth = 0
        block_keywords = ("alt ", "opt ", "loop ", "par ", "critical ", "break ", "rect ")

        def flush_preserved_block():
            nonlocal preserved_block
            if preserved_block:
                self.sequence_export_rows.append({"type": "raw", "lines": preserved_block[:]})
                preserved_block = []

        for line in lines:
            if line.startswith("sequenceDiagram"):
                continue
            if line.startswith("%%"):
                self.sequence_export_rows.append({"type": "raw", "lines": [line]})
                continue
            if block_depth > 0:
                preserved_block.append(line)
                if line.startswith(block_keywords):
                    block_depth += 1
                elif line == "end":
                    block_depth -= 1
                    if block_depth <= 0:
                        flush_preserved_block()
                continue
            if line.startswith(block_keywords):
                preserved_block = [line]
                block_depth = 1
                continue
            note_match = re.match(r'Note\s+(right of|left of|over)\s+(.+?)\s*:\s*(.+)', line)
            if note_match:
                placement, actor_text, note_text = note_match.groups()
                actor_ids = [part.strip() for part in actor_text.split(",") if part.strip()]
                note_rows.append({
                    "placement": placement,
                    "actor_ids": actor_ids,
                    "text": note_text.strip(),
                    "row_index": len(message_rows) + len(note_rows),
                })
                self.sequence_export_rows.append({"type": "note", "placement": placement, "actor_ids": actor_ids, "text": note_text.strip()})
                for actor_id in actor_ids:
                    actor_lookup.setdefault(actor_id, {"name": actor_id, "kind": "participant", "participant_type": None})
                continue
            participant_match = re.match(r'(participant|actor)\s+([A-Za-z0-9_]+)(@\{.*?\})?(?:\s+as\s+(.+))?$', line)
            if participant_match:
                actor_kind, actor_id, config_text, display_name = participant_match.groups()
                config = parse_sequence_participant_config(config_text)
                actor_lookup[actor_id] = {
                    "name": (display_name or config.get("alias") or actor_id).strip(),
                    "kind": actor_kind,
                    "participant_type": config.get("type"),
                }
                continue

            directive_match = re.match(r'(create\s+(?:participant|actor)\s+[A-Za-z0-9_]+(?:\s+as\s+.+)?|destroy\s+[A-Za-z0-9_]+)$', line)
            if directive_match:
                directive_text = directive_match.group(1)
                pending_directives.append(directive_text)
                create_match = re.match(r'create\s+(participant|actor)\s+([A-Za-z0-9_]+)(?:\s+as\s+(.+))?$', directive_text)
                if create_match:
                    actor_kind, actor_id, display_name = create_match.groups()
                    actor_lookup.setdefault(
                        actor_id,
                        {
                            "name": (display_name or actor_id).strip(),
                            "kind": actor_kind,
                            "participant_type": None,
                        },
                    )
                continue

            msg_match = SEQUENCE_MESSAGE_RE.match(line)
            if msg_match:
                source, source_central, base_arrow, target_central, target, label = msg_match.groups()
                arrow = f'{source_central or ""}{base_arrow}{target_central or ""}'
                msg_type = "sync"
                if base_arrow in {"-->>", "<<-->>"}:
                    msg_type = "return"
                elif "--" in base_arrow:
                    msg_type = "async"
                elif base_arrow in {"-)", "-x"}:
                    msg_type = "async"
                elif base_arrow in {"->>", "->", "<<->>", "-|\\", "-|/", "/|-", "\\\\-", "-\\\\", "-//", "//-"}:
                    msg_type = "sync"
                message_rows.append({
                    "source": source,
                    "target": target,
                    "msg_type": msg_type,
                    "label": label.strip(),
                    "arrow": arrow,
                    "directives_before": pending_directives[:],
                })
                self.sequence_export_rows.append({"type": "message"})
                pending_directives.clear()
                actor_lookup.setdefault(source, {"name": source, "kind": "participant", "participant_type": None})
                actor_lookup.setdefault(target, {"name": target, "kind": "participant", "participant_type": None})
                continue
            self.sequence_export_rows.append({"type": "raw", "lines": [line]})

        x = 100
        for actor_id, data in actor_lookup.items():
            actor = SequenceActor(self.canvas, x, 60, data["name"], self)
            actor.actor_id = actor_id
            actor.actor_kind = data.get("kind", "participant")
            actor.participant_type = data.get("participant_type")
            actor.create_visual()
            self.sequence_actors.append(actor)
            x += 180

        actor_objects = {getattr(actor, "actor_id", actor.name): actor for actor in self.sequence_actors}
        self.sequence_notes = []
        for note_row in note_rows:
            actors = [actor_objects.get(actor_id) for actor_id in note_row["actor_ids"] if actor_id in actor_objects]
            if actors:
                self.sequence_notes.append(
                    SequenceNote(
                        self.canvas,
                        note_row["placement"],
                        actors,
                        note_row["text"],
                        row_index=note_row["row_index"],
                        tool=self,
                    )
                )
        for index, row in enumerate(message_rows):
            source = row["source"]
            target = row["target"]
            if source in actor_objects and target in actor_objects:
                message = SequenceMessage(
                    self.canvas,
                    actor_objects[source],
                    actor_objects[target],
                    row["msg_type"],
                    row["label"],
                    index,
                    self,
                )
                message.arrow_symbol = row["arrow"]
                message.directives_before = row["directives_before"]
                message.update_position()
                self.sequence_messages.append(message)

        self.sequence_directives = pending_directives[:]
        flush_preserved_block()

        if apply_auto_layout:
            self.apply_auto_layout()
        else:
            self.update_scroll_region()
        self.update_status(f"Loaded sequence diagram with {len(self.sequence_actors)} participants")

    def parse_state_diagram(self, mermaid_code, apply_auto_layout=True):
        lines = [line.strip() for line in mermaid_code.split('\n') if line.strip()]
        state_names = []
        transitions = []
        self.state_preserved_lines = []
        start_state_id = "__start__"
        end_state_id = "__end__"

        for line in lines:
            if line.startswith("stateDiagram"):
                continue
            if line.startswith("%%") or line.startswith("direction ") or "{" in line or "}" in line:
                self.state_preserved_lines.append(line)
                continue
            state_match = re.match(r'state\s+([A-Za-z0-9_]+)', line)
            if state_match:
                state_names.append(state_match.group(1))
                continue
            trans_match = re.match(r'(\[\*\]|[A-Za-z0-9_]+)\s*-->\s*(\[\*\]|[A-Za-z0-9_]+)(?:\s*:\s*(.+))?', line)
            if trans_match:
                source, target, label = trans_match.groups()
                source = start_state_id if source == "[*]" else source
                target = end_state_id if target == "[*]" else target
                transitions.append((source, target, (label or "").strip()))
                if source not in state_names:
                    state_names.append(source)
                if target not in state_names:
                    state_names.append(target)
                continue
            self.state_preserved_lines.append(line)

        x, y = 150, 150
        state_lookup = {}
        for index, state_name in enumerate(state_names):
            state_kind = "normal"
            display_name = state_name
            if state_name == start_state_id:
                state_kind = "start"
                display_name = "[*]"
            elif state_name == end_state_id:
                state_kind = "end"
                display_name = "[*]"
            state = StateNode(self.canvas, x, y, display_name, self, state_kind=state_kind)
            state.state_id = state_name
            self.state_nodes.append(state)
            state_lookup[state_name] = state
            x += 220
            if (index + 1) % 3 == 0:
                x = 150
                y += 140

        for source, target, label in transitions:
            if source in state_lookup and target in state_lookup:
                self.state_transitions.append(StateTransition(self.canvas, state_lookup[source], state_lookup[target], label, self))

        if apply_auto_layout:
            self.apply_auto_layout()
        else:
            self.update_scroll_region()
        self.update_status(f"Loaded state diagram with {len(self.state_nodes)} states")

    def parse_er_diagram(self, mermaid_code, apply_auto_layout=True):
        lines = [line.rstrip() for line in mermaid_code.split('\n') if line.strip()]
        entity_blocks = {}
        relationships = []
        current_entity = None
        self.er_direction = None
        self.er_preserved_lines = []

        def ensure_entity(reference):
            entity_id, entity_alias = split_er_entity_reference(reference)
            if entity_id not in entity_blocks:
                entity_blocks[entity_id] = {"attrs": [], "alias": entity_alias}
            elif entity_alias and not entity_blocks[entity_id].get("alias"):
                entity_blocks[entity_id]["alias"] = entity_alias
            return entity_id

        for raw_line in lines:
            line = raw_line.strip()
            if line.startswith("erDiagram"):
                continue
            if line.startswith("%%"):
                self.er_preserved_lines.append(line)
                continue
            if line.startswith("direction "):
                self.er_direction = line.split(" ", 1)[1].strip()
                continue

            entity_start = re.match(r'((?:"[^"]+"|[A-Za-z0-9_-]+)(?:\[(?:"[^"]+"|[^\]]+)\])?)\s*\{', line)
            if entity_start:
                current_entity = ensure_entity(entity_start.group(1))
                continue

            if line == "}":
                current_entity = None
                continue

            if current_entity:
                entity_blocks[current_entity]["attrs"].append(line)
                continue

            rel_match = re.match(r'((?:"[^"]+"|[A-Za-z0-9_-]+))\s+(.+?)\s+((?:"[^"]+"|[A-Za-z0-9_-]+))(?:\s*:\s*(.+))?$', line)
            if rel_match:
                left_ref, relation_text, right_ref, label = rel_match.groups()
                left = ensure_entity(left_ref)
                right = ensure_entity(right_ref)
                parsed_relation = parse_er_relationship_syntax(relation_text)
                if parsed_relation:
                    relationships.append(
                        (
                            left,
                            right,
                            parsed_relation["rel_type"],
                            (label or "").strip(),
                            relation_text.strip(),
                            parsed_relation["from_cardinality"],
                            parsed_relation["to_cardinality"],
                            parsed_relation["identifying"],
                        )
                    )
                    continue

            standalone_entity = re.match(r'((?:"[^"]+"|[A-Za-z0-9_-]+)(?:\[(?:"[^"]+"|[^\]]+)\])?)$', line)
            if standalone_entity:
                ensure_entity(standalone_entity.group(1))
                continue
            self.er_preserved_lines.append(line)

        x, y = 150, 150
        entity_lookup = {}
        for index, (entity_id, entity_data) in enumerate(entity_blocks.items()):
            display_name = entity_data.get("alias") or entity_id
            entity = EREntity(self.canvas, x, y, display_name, self)
            entity.entity_id = entity_id
            entity.entity_alias = entity_data.get("alias")
            entity.attributes = entity_data.get("attrs", [])
            self.er_entities.append(entity)
            entity_lookup[entity_id] = entity
            x += 240
            if (index + 1) % 3 == 0:
                x = 150
                y += 170

        for left, right, rel_type, label, raw_relation, from_cardinality, to_cardinality, identifying in relationships:
            if left in entity_lookup and right in entity_lookup:
                relationship = ERRelationship(self.canvas, entity_lookup[left], entity_lookup[right], rel_type, label, self)
                relationship.raw_relation = raw_relation
                relationship.from_cardinality = from_cardinality
                relationship.to_cardinality = to_cardinality
                relationship.identifying = identifying
                self.er_relationships.append(relationship)

        if apply_auto_layout:
            self.apply_auto_layout()
        else:
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
        self.class_preserved_lines = []
        namespace_depth = 0
        
        for line in lines:
            if 'classDiagram' in line:
                continue
            if line.startswith("%%"):
                self.class_preserved_lines.append(line)
                continue
            if namespace_depth > 0:
                self.class_preserved_lines.append(line)
                if "{" in line:
                    namespace_depth += line.count("{")
                if "}" in line:
                    namespace_depth -= line.count("}")
                continue
            if line.startswith("namespace "):
                namespace_depth = max(1, line.count("{"))
                self.class_preserved_lines.append(line)
                continue
            if line.startswith("direction ") or line.startswith("classDef ") or line.startswith("cssClass ") or line.startswith("style ") or line.startswith("click ") or line.startswith("link ") or line.startswith("callback "):
                self.class_preserved_lines.append(line)
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
                    classes_data[class_name] = {'attributes': [], 'methods': [], 'annotations': [], 'stereotype': '', 'display_label': class_name}
                classes_data[class_name]['annotations'].append(annotation)
                continue
            
            stereotype_match = re.match(r'\s*(\w+)\s*:\s*<<([^>]+)>>', line)
            if stereotype_match:
                class_name, stereotype = stereotype_match.groups()
                if class_name not in classes_data:
                    classes_data[class_name] = {'attributes': [], 'methods': [], 'annotations': [], 'stereotype': '', 'display_label': class_name}
                classes_data[class_name]['stereotype'] = stereotype
                continue

            class_alias_match = re.match(r'\s*class\s+(\w+)\s*\[\s*"([^"]+)"\s*\]\s*$', line)
            if class_alias_match:
                class_name, display_label = class_alias_match.groups()
                if class_name not in classes_data:
                    classes_data[class_name] = {'attributes': [], 'methods': [], 'annotations': [], 'stereotype': '', 'display_label': display_label}
                else:
                    classes_data[class_name]['display_label'] = display_label
                continue
                
            # Parse class definition start
            class_match = re.match(r'\s*class\s+(\w+)\s*\{', line)
            if class_match:
                current_class = class_match.group(1)
                if current_class not in classes_data:
                    classes_data[current_class] = {'attributes': [], 'methods': [], 'annotations': [], 'stereotype': '', 'display_label': current_class}
                continue

            standalone_class_match = re.match(r'\s*class\s+(\w+)\s*$', line)
            if standalone_class_match:
                class_name = standalone_class_match.group(1)
                if class_name not in classes_data:
                    classes_data[class_name] = {'attributes': [], 'methods': [], 'annotations': [], 'stereotype': '', 'display_label': class_name}
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

                    for class_name in (from_class, to_class):
                        if class_name not in classes_data:
                            classes_data[class_name] = {
                                'attributes': [],
                                'methods': [],
                                'annotations': [],
                                'stereotype': '',
                                'display_label': class_name,
                            }
                    
                    relationships.append({
                        'from': from_class,
                        'to': to_class,
                        'type': rel_type,
                        'label': label or "",
                        'from_multiplicity': from_mult,
                        'to_multiplicity': to_mult
                    })
                    break
            else:
                self.class_preserved_lines.append(line)
        
        # Create visual classes
        class_positions = self.calculate_class_positions(len(classes_data))
        class_objects = {}
        
        for i, (class_name, class_data) in enumerate(classes_data.items()):
            x, y = class_positions[i]
            class_box = ClassBox(self.canvas, x, y, class_data.get('display_label', class_name), self)
            class_box.class_id = class_name
            class_box.display_label = class_data.get('display_label', class_name)
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

    def build_class_layout_graphs(self):
        """Build directed hierarchy and undirected connectivity maps for class layout."""
        hierarchy_children = {cls: [] for cls in self.classes}
        hierarchy_parents = {cls: [] for cls in self.classes}
        all_connections = {cls: set() for cls in self.classes}

        for rel in self.relationships:
            if rel.rel_type in ["inheritance", "composition", "realization"]:
                hierarchy_children[rel.to_class].append(rel.from_class)
                hierarchy_parents[rel.from_class].append(rel.to_class)

            all_connections[rel.from_class].add(rel.to_class)
            all_connections[rel.to_class].add(rel.from_class)

        return hierarchy_children, hierarchy_parents, all_connections

    def get_class_connected_components(self, connections):
        """Return connected components for the undirected class graph."""
        remaining = set(self.classes)
        components = []

        while remaining:
            start = remaining.pop()
            queue = [start]
            component = []
            seen = {start}

            while queue:
                current = queue.pop(0)
                component.append(current)
                for neighbor in connections[current]:
                    if neighbor not in seen:
                        seen.add(neighbor)
                        if neighbor in remaining:
                            remaining.remove(neighbor)
                        queue.append(neighbor)

            components.append(component)

        components.sort(key=lambda comp: (-len(comp), sorted(cls.name for cls in comp)))
        return components

    def compute_class_layout_levels(self, hierarchy_children, hierarchy_parents, all_connections):
        """Assign classes to levels using hierarchy edges first, then graph proximity."""
        component_map = {}
        level_map = {}
        components = self.get_class_connected_components(all_connections)

        for component_index, component in enumerate(components):
            component_set = set(component)
            for cls in component:
                component_map[cls] = component_index

            local_children = {
                cls: [child for child in hierarchy_children[cls] if child in component_set]
                for cls in component
            }
            local_parents = {
                cls: [parent for parent in hierarchy_parents[cls] if parent in component_set]
                for cls in component
            }

            has_hierarchy = any(local_children[cls] or local_parents[cls] for cls in component)

            if has_hierarchy:
                local_in_degree = {cls: len(local_parents[cls]) for cls in component}
                roots = [cls for cls in component if local_in_degree[cls] == 0]
                if not roots:
                    roots = [max(component, key=lambda cls: len(all_connections[cls]))]

                queue = roots[:]
                for root in roots:
                    level_map[root] = 0

                while queue:
                    current = queue.pop(0)
                    current_level = level_map[current]
                    for child in local_children[current]:
                        next_level = current_level + 1
                        if next_level > level_map.get(child, -1):
                            level_map[child] = next_level
                        if child in local_in_degree:
                            local_in_degree[child] = max(0, local_in_degree[child] - 1)
                        if child not in queue and local_in_degree.get(child, 0) == 0:
                            queue.append(child)

                unresolved = [cls for cls in component if cls not in level_map]
                while unresolved:
                    progressed = False
                    for cls in unresolved[:]:
                        neighbor_levels = [
                            level_map[parent] + 1
                            for parent in local_parents[cls]
                            if parent in level_map
                        ]
                        neighbor_levels.extend(
                            level_map[neighbor]
                            for neighbor in all_connections[cls]
                            if neighbor in level_map
                        )
                        if neighbor_levels:
                            level_map[cls] = max(0, round(sum(neighbor_levels) / len(neighbor_levels)))
                            unresolved.remove(cls)
                            progressed = True
                    if not progressed:
                        fallback = max(unresolved, key=lambda cls: len(all_connections[cls]))
                        level_map[fallback] = 0
                        unresolved.remove(fallback)
            else:
                root = max(component, key=lambda cls: (len(all_connections[cls]), cls.name))
                queue = [root]
                level_map[root] = 0
                seen = {root}
                while queue:
                    current = queue.pop(0)
                    for neighbor in all_connections[current]:
                        if neighbor in component_set and neighbor not in seen:
                            seen.add(neighbor)
                            level_map[neighbor] = level_map[current] + 1
                            queue.append(neighbor)

            min_level = min(level_map[cls] for cls in component)
            for cls in component:
                level_map[cls] -= min_level

        max_level = max(level_map.values(), default=0)
        levels = [[] for _ in range(max_level + 1)]
        for cls in self.classes:
            levels[level_map.get(cls, 0)].append(cls)

        levels = [level for level in levels if level]
        return levels, level_map, component_map

    def sort_class_layout_levels(self, levels, hierarchy_children, hierarchy_parents, all_connections, component_map, sweeps=4):
        """Reduce crossings by reordering each level using barycenter passes."""
        for level in levels:
            level.sort(key=lambda cls: (component_map.get(cls, 0), -len(all_connections[cls]), cls.name.lower()))

        for _ in range(sweeps):
            for level_idx in range(1, len(levels)):
                previous_positions = {cls: idx for idx, cls in enumerate(levels[level_idx - 1])}

                def top_down_key(cls):
                    weights = []
                    for parent in hierarchy_parents[cls]:
                        if parent in previous_positions:
                            weights.extend([previous_positions[parent]] * 4)
                    for neighbor in all_connections[cls]:
                        if neighbor in previous_positions:
                            weights.append(previous_positions[neighbor])
                    if weights:
                        return (sum(weights) / len(weights), component_map.get(cls, 0), cls.name.lower())
                    return (float("inf"), component_map.get(cls, 0), cls.name.lower())

                levels[level_idx].sort(key=top_down_key)

            for level_idx in range(len(levels) - 2, -1, -1):
                next_positions = {cls: idx for idx, cls in enumerate(levels[level_idx + 1])}

                def bottom_up_key(cls):
                    weights = []
                    for child in hierarchy_children[cls]:
                        if child in next_positions:
                            weights.extend([next_positions[child]] * 4)
                    for neighbor in all_connections[cls]:
                        if neighbor in next_positions:
                            weights.append(next_positions[neighbor])
                    if weights:
                        return (sum(weights) / len(weights), component_map.get(cls, 0), cls.name.lower())
                    return (float("inf"), component_map.get(cls, 0), cls.name.lower())

                levels[level_idx].sort(key=bottom_up_key)

    def distribute_class_level(self, level, desired_centers, anchor_x=200, gap=60):
        """Place classes left-to-right near desired centers while preserving order and spacing."""
        centers = {}
        current_left = anchor_x

        desired_average = 0.0
        desired_count = 0
        for cls in level:
            desired = desired_centers.get(cls)
            if desired is not None:
                desired_average += desired
                desired_count += 1

        for cls in level:
            half_width = cls.width / 2
            desired = desired_centers.get(cls, current_left + half_width)
            left = max(current_left, desired - half_width)
            centers[cls] = left + half_width
            current_left = left + cls.width + gap

        if desired_count:
            actual_average = sum(centers[cls] for cls in level) / len(level)
            target_average = desired_average / desired_count
            shift = target_average - actual_average
            left_boundary = min(centers[cls] - cls.width / 2 for cls in level)
            if left_boundary + shift < anchor_x:
                shift += anchor_x - (left_boundary + shift)
            if abs(shift) > 1:
                for cls in level:
                    centers[cls] += shift

        return centers

    def place_class_layout_levels(self, levels, hierarchy_children, hierarchy_parents, all_connections):
        """Place each level, then relax horizontally to align related classes."""
        start_x, start_y = 180, 140
        horizontal_gap = 70
        vertical_gap = 110
        level_max_heights = [max((cls.height for cls in level), default=120) for level in levels]
        y_positions = []
        running_y = start_y
        for level_height in level_max_heights:
            y_positions.append(running_y)
            running_y += level_height + vertical_gap

        centers_by_class = {}
        canvas_width = self.canvas.winfo_width() if self.canvas.winfo_width() > 1 else 1280

        for level_idx, level in enumerate(levels):
            if level_idx == 0:
                level_width = sum(cls.width for cls in level) + max(0, len(level) - 1) * horizontal_gap
                current_left = max(start_x, (canvas_width - level_width) / 2)
                for cls in level:
                    centers_by_class[cls] = current_left + (cls.width / 2)
                    current_left += cls.width + horizontal_gap
            else:
                desired_centers = {}
                for cls in level:
                    anchors = []
                    for parent in hierarchy_parents[cls]:
                        if parent in centers_by_class:
                            anchors.extend([centers_by_class[parent]] * 4)
                    for neighbor in all_connections[cls]:
                        if neighbor in centers_by_class:
                            anchors.append(centers_by_class[neighbor])
                    if anchors:
                        desired_centers[cls] = sum(anchors) / len(anchors)
                centers_by_class.update(
                    self.distribute_class_level(level, desired_centers, anchor_x=start_x, gap=horizontal_gap)
                )

        for _ in range(6):
            for level in levels:
                desired_centers = {}
                for cls in level:
                    anchors = []
                    for parent in hierarchy_parents[cls]:
                        if parent in centers_by_class:
                            anchors.extend([centers_by_class[parent]] * 4)
                    for child in hierarchy_children[cls]:
                        if child in centers_by_class:
                            anchors.extend([centers_by_class[child]] * 3)
                    for neighbor in all_connections[cls]:
                        if neighbor in centers_by_class:
                            anchors.append(centers_by_class[neighbor])
                    anchors.append(centers_by_class.get(cls, cls.get_center()[0]))
                    desired_centers[cls] = sum(anchors) / len(anchors)

                centers_by_class.update(
                    self.distribute_class_level(level, desired_centers, anchor_x=start_x, gap=horizontal_gap)
                )

        for level_idx, level in enumerate(levels):
            target_y = y_positions[level_idx]
            for cls in level:
                target_x = centers_by_class[cls] - (cls.width / 2)
                dx = target_x - cls.x
                dy = target_y - cls.y
                cls.move(dx, dy)

    def resolve_class_level_overlaps(self, levels, min_gap=36):
        """Resolve residual horizontal overlaps while preserving level structure."""
        for level in levels:
            if len(level) < 2:
                continue
            level.sort(key=lambda cls: cls.x)
            current_right = None
            for cls in level:
                if current_right is None:
                    current_right = cls.x + cls.width
                    continue
                minimum_left = current_right + min_gap
                if cls.x < minimum_left:
                    cls.move(minimum_left - cls.x, 0)
                current_right = cls.x + cls.width

            left_edge = min(cls.x for cls in level)
            if left_edge < 180:
                shift = 180 - left_edge
                for cls in level:
                    cls.move(shift, 0)

    def apply_hierarchical_layout(self):
        """Apply a layered class layout with barycentric ordering and alignment passes."""
        if not self.classes:
            self.update_status("No classes to layout")
            return
        
        self.update_status("Applying hierarchical layout...")

        hierarchy_children, hierarchy_parents, all_connections = self.build_class_layout_graphs()
        levels, _, component_map = self.compute_class_layout_levels(
            hierarchy_children,
            hierarchy_parents,
            all_connections,
        )
        self.sort_class_layout_levels(
            levels,
            hierarchy_children,
            hierarchy_parents,
            all_connections,
            component_map,
        )
        self.place_class_layout_levels(
            levels,
            hierarchy_children,
            hierarchy_parents,
            all_connections,
        )
        self.resolve_class_level_overlaps(levels)

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

    def apply_auto_layout(self):
        """Apply the most appropriate automatic layout for the active diagram type."""
        if self.diagram_type == "flowchart":
            self.apply_flowchart_layout()
        elif self.diagram_type == "sequenceDiagram":
            self.apply_sequence_layout()
        elif self.diagram_type == "stateDiagram":
            self.apply_state_layout()
        elif self.diagram_type == "erDiagram":
            self.apply_er_layout()
        else:
            self.apply_hierarchical_layout()

    def move_diagram_item_to(self, item, target_x, target_y):
        dx = target_x - item.x
        dy = target_y - item.y
        if abs(dx) < 0.01 and abs(dy) < 0.01:
            return

        if isinstance(item, ClassBox):
            item.move(dx, dy)
            return

        item.x += dx
        item.y += dy

        if isinstance(item, SequenceActor):
            for visual_item in item.visual_items:
                self.canvas.move(visual_item, dx, dy)
            if item.primary_bbox:
                item.primary_bbox = (
                    item.primary_bbox[0] + dx,
                    item.primary_bbox[1] + dy,
                    item.primary_bbox[2] + dx,
                    item.primary_bbox[3] + dy,
                )
            return

        if isinstance(item, FlowchartNode):
            self.canvas.move(item.shape_item, dx, dy)
            self.canvas.move(item.text_item, dx, dy)
            return

        self.canvas.move(item.box, dx, dy)
        if getattr(item, "text_item", None):
            self.canvas.move(item.text_item, dx, dy)

    def get_layout_item_size(self, item):
        zoom_level = self.zoom_level if hasattr(self, "zoom_level") else 1.0
        return (
            max(60, getattr(item, "width", 120) * zoom_level),
            max(40, getattr(item, "height", 80) * zoom_level),
        )

    def build_directed_layout_levels(self, items, edge_pairs):
        outgoing = {item: [] for item in items}
        incoming = {item: [] for item in items}
        neighbors = {item: set() for item in items}

        for source, target in edge_pairs:
            if source not in outgoing or target not in outgoing:
                continue
            outgoing[source].append(target)
            incoming[target].append(source)
            neighbors[source].add(target)
            neighbors[target].add(source)

        in_degree = {item: len(incoming[item]) for item in items}
        roots = [item for item in items if in_degree[item] == 0]
        if not roots and items:
            roots = [max(items, key=lambda item: len(outgoing[item]) + len(neighbors[item]))]

        level_map = {root: 0 for root in roots}
        queue = roots[:]
        pending = in_degree.copy()

        while queue:
            current = queue.pop(0)
            current_level = level_map[current]
            for child in outgoing[current]:
                next_level = current_level + 1
                if next_level > level_map.get(child, -1):
                    level_map[child] = next_level
                pending[child] = max(0, pending[child] - 1)
                if pending[child] == 0 and child not in queue:
                    queue.append(child)

        unresolved = [item for item in items if item not in level_map]
        while unresolved:
            progressed = False
            for item in unresolved[:]:
                anchor_levels = [level_map[parent] + 1 for parent in incoming[item] if parent in level_map]
                if anchor_levels:
                    level_map[item] = max(anchor_levels)
                    unresolved.remove(item)
                    progressed = True
            if not progressed:
                fallback = max(unresolved, key=lambda item: len(neighbors[item]))
                level_map[fallback] = 0
                unresolved.remove(fallback)

        levels = []
        for item in items:
            level = level_map.get(item, 0)
            while len(levels) <= level:
                levels.append([])
            levels[level].append(item)

        return levels, outgoing, incoming, neighbors

    def sort_layout_levels(self, levels, incoming, outgoing, neighbors, sweeps=3):
        for level in levels:
            level.sort(key=lambda item: getattr(item, "x", 0))

        for _ in range(sweeps):
            for index in range(1, len(levels)):
                previous_positions = {item: pos for pos, item in enumerate(levels[index - 1])}

                def top_key(item):
                    weights = []
                    for parent in incoming[item]:
                        if parent in previous_positions:
                            weights.extend([previous_positions[parent]] * 4)
                    for neighbor in neighbors[item]:
                        if neighbor in previous_positions:
                            weights.append(previous_positions[neighbor])
                    return sum(weights) / len(weights) if weights else getattr(item, "x", 0)

                levels[index].sort(key=top_key)

            for index in range(len(levels) - 2, -1, -1):
                next_positions = {item: pos for pos, item in enumerate(levels[index + 1])}

                def bottom_key(item):
                    weights = []
                    for child in outgoing[item]:
                        if child in next_positions:
                            weights.extend([next_positions[child]] * 4)
                    for neighbor in neighbors[item]:
                        if neighbor in next_positions:
                            weights.append(next_positions[neighbor])
                    return sum(weights) / len(weights) if weights else getattr(item, "x", 0)

                levels[index].sort(key=bottom_key)

    def place_layout_levels(self, levels, orientation="TB", start_x=140, start_y=120, primary_gap=110, secondary_gap=80):
        reverse_primary = orientation in {"BT", "RL"}
        horizontal = orientation in {"LR", "RL"}
        ordered_levels = list(reversed(levels)) if reverse_primary else levels
        canvas_width = self.canvas.winfo_width() if self.canvas.winfo_width() > 1 else 1200
        canvas_height = self.canvas.winfo_height() if self.canvas.winfo_height() > 1 else 900

        if horizontal:
            primary_cursor = start_x
            for level in ordered_levels:
                level_sizes = [self.get_layout_item_size(item) for item in level]
                level_primary_size = max((size[0] for size in level_sizes), default=120)
                total_secondary = sum(size[1] for size in level_sizes) + max(0, len(level) - 1) * secondary_gap
                secondary_cursor = max(start_y, start_y + (canvas_height - total_secondary) / 2)
                for item, (width, height) in zip(level, level_sizes):
                    self.move_diagram_item_to(item, primary_cursor, secondary_cursor)
                    secondary_cursor += height + secondary_gap
                primary_cursor += level_primary_size + primary_gap
            return

        primary_cursor = start_y
        for level in ordered_levels:
            level_sizes = [self.get_layout_item_size(item) for item in level]
            level_primary_size = max((size[1] for size in level_sizes), default=80)
            total_secondary = sum(size[0] for size in level_sizes) + max(0, len(level) - 1) * secondary_gap
            secondary_cursor = max(start_x, start_x + (canvas_width - total_secondary) / 2)
            for item, (width, height) in zip(level, level_sizes):
                self.move_diagram_item_to(item, secondary_cursor, primary_cursor)
                secondary_cursor += width + secondary_gap
            primary_cursor += level_primary_size + primary_gap

    def apply_flowchart_layout(self):
        if not self.flowchart_nodes:
            self.update_status("No nodes to layout")
            return

        self.update_status("Applying flowchart layout...")
        edges = [(connection.from_node, connection.to_node) for connection in self.flowchart_connections]
        levels, outgoing, incoming, neighbors = self.build_directed_layout_levels(self.flowchart_nodes, edges)
        self.sort_layout_levels(levels, incoming, outgoing, neighbors)
        self.place_layout_levels(
            levels,
            orientation=getattr(self, "flowchart_direction", "TD") or "TD",
            start_x=140,
            start_y=120,
            primary_gap=120,
            secondary_gap=90,
        )
        self.update_relationships()
        self.update_scroll_region()
        self.ensure_grid_behind()
        self.mark_as_changed()
        self.update_status(f"Flowchart layout applied to {len(self.flowchart_nodes)} nodes")

    def apply_sequence_layout(self):
        if not self.sequence_actors:
            self.update_status("No participants to layout")
            return

        self.update_status("Applying sequence layout...")
        ordered_actors = sorted(self.sequence_actors, key=lambda actor: actor.x)
        canvas_width = self.canvas.winfo_width() if self.canvas.winfo_width() > 1 else 1200
        sizes = [self.get_layout_item_size(actor) for actor in ordered_actors]
        gap = 100
        total_width = sum(width for width, _ in sizes) + max(0, len(ordered_actors) - 1) * gap
        cursor_x = max(120, (canvas_width - total_width) / 2)
        top_y = 70

        for actor, (width, _) in zip(ordered_actors, sizes):
            self.move_diagram_item_to(actor, cursor_x, top_y)
            cursor_x += width + gap

        self.sequence_actors[:] = ordered_actors
        self.reindex_sequence_messages()
        self.update_relationships()
        self.update_scroll_region()
        self.ensure_grid_behind()
        self.mark_as_changed()
        self.update_status(f"Sequence layout applied to {len(self.sequence_actors)} participants")

    def apply_state_layout(self):
        if not self.state_nodes:
            self.update_status("No states to layout")
            return

        self.update_status("Applying state layout...")
        edges = [(transition.from_state, transition.to_state) for transition in self.state_transitions]
        levels, outgoing, incoming, neighbors = self.build_directed_layout_levels(self.state_nodes, edges)
        self.sort_layout_levels(levels, incoming, outgoing, neighbors)
        self.place_layout_levels(levels, orientation="TD", start_x=140, start_y=130, primary_gap=120, secondary_gap=100)
        self.update_relationships()
        self.update_scroll_region()
        self.ensure_grid_behind()
        self.mark_as_changed()
        self.update_status(f"State layout applied to {len(self.state_nodes)} states")

    def apply_er_layout(self):
        if not self.er_entities:
            self.update_status("No entities to layout")
            return

        self.update_status("Applying ER layout...")
        edges = [(relationship.from_entity, relationship.to_entity) for relationship in self.er_relationships]
        levels, outgoing, incoming, neighbors = self.build_directed_layout_levels(self.er_entities, edges)
        self.sort_layout_levels(levels, incoming, outgoing, neighbors)
        self.place_layout_levels(
            levels,
            orientation=(self.er_direction or "LR").upper(),
            start_x=150,
            start_y=140,
            primary_gap=140,
            secondary_gap=110,
        )
        self.update_relationships()
        self.update_scroll_region()
        self.ensure_grid_behind()
        self.mark_as_changed()
        self.update_status(f"ER layout applied to {len(self.er_entities)} entities")
    
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
        lines = [f"flowchart {getattr(self, 'flowchart_direction', 'TD') or 'TD'}"]
        lines.extend(f"    {line}" if not line.startswith("    ") else line for line in getattr(self, "flowchart_preserved_lines", []))
        
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
            actor_kind = getattr(actor, "actor_kind", "participant")
            participant_type = getattr(actor, "participant_type", None)
            declaration = f"    {actor_kind} {actor_id}"
            if participant_type:
                declaration += f'@{{ "type": "{participant_type}" }}'
            if actor_name != actor_id:
                declaration += f" as {actor_name}"
            lines.append(declaration)
        message_iter = iter(self.sequence_messages)
        arrow_map = {
            "sync": "->>",
            "async": "-->",
            "return": "-->>",
            "note": "--"
        }
        export_rows = self.sequence_export_rows or [{"type": "message"} for _ in self.sequence_messages]
        for row in export_rows:
            if row.get("type") == "raw":
                for raw_line in row.get("lines", []):
                    lines.append(f"    {raw_line}" if raw_line and not raw_line.startswith("    ") else raw_line)
                continue
            if row.get("type") == "note":
                actor_ids = row.get("actor_ids", [])
                actor_text = ",".join(actor_ids)
                lines.append(f"    Note {row.get('placement', 'over')} {actor_text}: {row.get('text', '')}")
                continue
            message = next(message_iter, None)
            if not message:
                continue
            for directive in getattr(message, "directives_before", []):
                lines.append(f"    {directive}")
            source = getattr(message.from_actor, "actor_id", message.from_actor.name.replace(" ", "_"))
            target = getattr(message.to_actor, "actor_id", message.to_actor.name.replace(" ", "_"))
            symbol = getattr(message, "arrow_symbol", arrow_map.get(message.msg_type, "->>"))
            left_sep = "" if symbol.startswith("()") else " "
            right_sep = "" if symbol.endswith("()") else " "
            lines.append(f"    {source}{left_sep}{symbol}{right_sep}{target} : {message.label}")
        for message in message_iter:
            for directive in getattr(message, "directives_before", []):
                lines.append(f"    {directive}")
            source = getattr(message.from_actor, "actor_id", message.from_actor.name.replace(" ", "_"))
            target = getattr(message.to_actor, "actor_id", message.to_actor.name.replace(" ", "_"))
            symbol = getattr(message, "arrow_symbol", arrow_map.get(message.msg_type, "->>"))
            left_sep = "" if symbol.startswith("()") else " "
            right_sep = "" if symbol.endswith("()") else " "
            lines.append(f"    {source}{left_sep}{symbol}{right_sep}{target} : {message.label}")
        for directive in self.sequence_directives:
            lines.append(f"    {directive}")
        return '\n'.join(lines)

    def generate_state_diagram(self):
        lines = ["stateDiagram-v2"]
        lines.extend(f"    {line}" if not line.startswith("    ") else line for line in getattr(self, "state_preserved_lines", []))
        for state in self.state_nodes:
            if getattr(state, "state_kind", "normal") != "normal":
                continue
            state_name = state.name.replace("\n", " ").strip() or "State"
            lines.append(f"    state {state_name}")
        for transition in self.state_transitions:
            from_name = "[*]" if getattr(transition.from_state, "state_kind", "normal") == "start" else transition.from_state.name
            to_name = "[*]" if getattr(transition.to_state, "state_kind", "normal") == "end" else transition.to_state.name
            line = f"    {from_name} --> {to_name}"
            if transition.label:
                line += f" : {transition.label}"
            lines.append(line)
        return '\n'.join(lines)

    def generate_er_diagram(self):
        lines = ["erDiagram"]
        if self.er_direction:
            lines.append(f"    direction {self.er_direction}")
        lines.extend(f"    {line}" if not line.startswith("    ") else line for line in getattr(self, "er_preserved_lines", []))
        for entity in self.er_entities:
            entity_id = getattr(entity, "entity_id", entity.name.replace(" ", "_").upper()) or "ENTITY"
            entity_alias = getattr(entity, "entity_alias", None)
            entity_header = entity_id
            if entity_alias and entity_alias != entity_id:
                escaped_alias = entity_alias.replace('"', '\\"')
                entity_header = f'{entity_id}["{escaped_alias}"]'
            lines.append(f"    {entity_header} {{")
            for attr in entity.attributes:
                lines.append(f"        {attr}")
            lines.append("    }")
        symbol_map = {
            "one-to-one": "||--||",
            "one-to-many": "||--o{",
            "many-to-many": "}o--o{"
        }
        for relation in self.er_relationships:
            left = getattr(relation.from_entity, "entity_id", relation.from_entity.name.replace(" ", "_").upper())
            right = getattr(relation.to_entity, "entity_id", relation.to_entity.name.replace(" ", "_").upper())
            relation_symbol = getattr(relation, "raw_relation", None) or symbol_map.get(relation.rel_type, '||--o{')
            line = f"    {left} {relation_symbol} {right}"
            if relation.label:
                line += f" : {relation.label}"
            lines.append(line)
        return '\n'.join(lines)
    
    def generate_class_diagram(self):
        lines = ["classDiagram"]
        lines.extend(f"    {line}" if not line.startswith("    ") else line for line in getattr(self, "class_preserved_lines", []))
        
        # Add classes with enhanced features
        for class_box in self.classes:
            class_name = getattr(class_box, "class_id", class_box.name.replace(" ", "_"))
            display_label = getattr(class_box, "display_label", class_box.name)
            has_details = bool(class_box.attributes or class_box.methods or class_box.annotations or class_box.stereotype or class_box.notes)
            if display_label != class_name:
                escaped_label = display_label.replace('"', '\\"')
                lines.append(f'    class {class_name}["{escaped_label}"]')
            elif not has_details:
                lines.append(f"    class {class_name}")
                continue
            
            # Add annotations
            for annotation in class_box.annotations:
                lines.append(f"    {class_name} : @{annotation}")
            
            # Add stereotype
            if class_box.stereotype:
                lines.append(f"    {class_name} : <<{class_box.stereotype}>>")
            
            if not has_details:
                continue

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
            from_name = getattr(rel.from_class, "class_id", rel.from_class.name.replace(" ", "_"))
            to_name = getattr(rel.to_class, "class_id", rel.to_class.name.replace(" ", "_"))
            
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
                class_name = getattr(class_box, "class_id", class_box.name.replace(" ", "_"))
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
            entity_key = getattr(entity, "entity_id", entity.name.replace(" ", "_").upper())
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
                class_name = getattr(class_box, "class_id", class_box.name.replace(" ", "_"))
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
                entity_key = getattr(entity, "entity_id", entity.name.replace(" ", "_").upper())
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
    startup_file = sys.argv[1] if len(sys.argv) > 1 else None
    app = MermaidDiagramTool(startup_file=startup_file)
    app.run()
