from pathlib import Path

from mermaid_diagram_tool import MermaidDiagramTool


SAMPLES = [
    "samples/sample_flowchart.md",
    "samples/sample_sequence_diagram.md",
    "samples/sample_state_diagram.md",
    "samples/sample_er_diagram.md",
    "samples/sample_class_diagram.md",
]

def capture_canvas(tool, output_path):
    tool.canvas.update_idletasks()
    export_bounds = tool.get_export_bounds()
    if not export_bounds:
        raise RuntimeError("No canvas content available for export")
    image = tool.render_canvas_to_png_image(export_bounds)
    image.save(output_path, format="PNG")


def main():
    base_dir = Path(__file__).resolve().parent
    output_dir = base_dir / "docs" / "screenshots"
    output_dir.mkdir(parents=True, exist_ok=True)

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
