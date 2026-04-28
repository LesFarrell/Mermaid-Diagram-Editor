from pathlib import Path
import time

from PIL import ImageGrab

from mermaid_diagram_tool import MermaidDiagramTool


VIEWS = [
    ("classDiagram", "sample_class_diagram.md", "ui_class.png"),
    ("flowchart", "sample_flowchart.md", "ui_flowchart.png"),
    ("sequenceDiagram", "sample_sequence_diagram.md", "ui_sequence.png"),
]


def capture_window(tool, output_path):
    tool.root.update_idletasks()
    tool.root.update()
    time.sleep(0.2)
    tool.root.update_idletasks()
    tool.root.update()
    x1 = tool.root.winfo_rootx()
    y1 = tool.root.winfo_rooty()
    x2 = x1 + tool.root.winfo_width()
    y2 = y1 + tool.root.winfo_height()
    ImageGrab.grab(bbox=(x1, y1, x2, y2)).save(output_path)


def main():
    base_dir = Path(__file__).resolve().parent
    output_dir = base_dir / "ui_checks"
    output_dir.mkdir(exist_ok=True)

    tool = MermaidDiagramTool()
    tool.root.geometry("1500x980+100+100")
    tool.root.lift()
    tool.root.attributes("-topmost", True)
    try:
        for diagram_type, sample_name, filename in VIEWS:
            tool.diagram_type = diagram_type
            tool.diagram_type_var.set(diagram_type)
            tool.update_diagram_type_ui()
            tool.load_diagram_from_file(str(base_dir / sample_name), prompt_for_unsaved=False, show_errors=False)
            capture_window(tool, output_dir / filename)
    finally:
        tool.root.attributes("-topmost", False)
        tool.root.destroy()


if __name__ == "__main__":
    main()
