from pathlib import Path
import time

from PIL import ImageGrab

from mermaid_diagram_tool import MermaidDiagramTool


SAMPLES = [
    "sample_flowchart.md",
    "sample_sequence_diagram.md",
    "sample_state_diagram.md",
    "sample_er_diagram.md",
    "sample_class_diagram.md",
]


def capture_canvas(tool, output_path):
    tool.root.update_idletasks()
    tool.root.update()
    time.sleep(0.3)
    tool.root.update_idletasks()
    tool.root.update()

    x1 = tool.canvas.winfo_rootx()
    y1 = tool.canvas.winfo_rooty()
    x2 = x1 + tool.canvas.winfo_width()
    y2 = y1 + tool.canvas.winfo_height()

    image = ImageGrab.grab(bbox=(x1, y1, x2, y2))
    image.save(output_path)


def main():
    base_dir = Path(__file__).resolve().parent
    output_dir = base_dir / "render_checks"
    output_dir.mkdir(exist_ok=True)

    tool = MermaidDiagramTool()
    tool.root.geometry("1400x950+100+100")
    tool.root.lift()
    tool.root.attributes("-topmost", True)
    tool.root.update_idletasks()
    tool.root.update()

    try:
        for sample_name in SAMPLES:
            sample_path = base_dir / sample_name
            ok = tool.load_diagram_from_file(str(sample_path), prompt_for_unsaved=False, show_errors=False)
            if not ok:
                print(f"FAILED {sample_name}")
                continue

            tool.root.title(f"Render Check - {sample_name}")
            tool.root.update_idletasks()
            tool.root.update()
            output_path = output_dir / f"{sample_path.stem}.png"
            capture_canvas(tool, output_path)
            print(f"SAVED {output_path}")
    finally:
        tool.root.attributes("-topmost", False)
        tool.root.destroy()


if __name__ == "__main__":
    main()
