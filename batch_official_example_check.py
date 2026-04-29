from __future__ import annotations

import json
import math
import re
import textwrap
import urllib.request
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from mermaid_diagram_tool import MermaidDiagramTool


DOC_SOURCES = {
    "flowchart": "https://raw.githubusercontent.com/mermaid-js/mermaid/develop/packages/mermaid/src/docs/syntax/flowchart.md",
    "sequence": "https://raw.githubusercontent.com/mermaid-js/mermaid/develop/packages/mermaid/src/docs/syntax/sequenceDiagram.md",
    "state": "https://raw.githubusercontent.com/mermaid-js/mermaid/develop/packages/mermaid/src/docs/syntax/stateDiagram.md",
    "er": "https://raw.githubusercontent.com/mermaid-js/mermaid/develop/packages/mermaid/src/docs/syntax/entityRelationshipDiagram.md",
    "class": "https://raw.githubusercontent.com/mermaid-js/mermaid/develop/packages/mermaid/src/docs/syntax/classDiagram.md",
    "examples": "https://raw.githubusercontent.com/mermaid-js/mermaid/develop/packages/mermaid/src/docs/syntax/examples.md",
    "readme": "https://raw.githubusercontent.com/mermaid-js/mermaid/develop/README.md",
}

SUPPORTED_PREFIXES = (
    "flowchart",
    "graph",
    "sequenceDiagram",
    "stateDiagram",
    "stateDiagram-v2",
    "erDiagram",
    "classDiagram",
)


def fetch_text(url: str) -> str:
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read().decode("utf-8")


def strip_front_matter(text: str) -> str:
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            return parts[2]
    return text


def normalize_example_text(raw: str) -> str:
    text = textwrap.dedent(raw).strip()
    text = re.sub(r"^---.*?---\s*", "", text, flags=re.DOTALL)
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def extract_examples(text: str, source_name: str) -> list[dict]:
    cleaned = strip_front_matter(text)
    examples = []

    fenced_pattern = re.compile(r"```mermaid-example\s*(.*?)```", re.DOTALL)
    for index, match in enumerate(fenced_pattern.finditer(cleaned), 1):
        block = normalize_example_text(match.group(1))
        if block.startswith(SUPPORTED_PREFIXES):
            examples.append({
                "source": source_name,
                "index": index,
                "diagram": block,
            })

    markdown_pattern = re.compile(r"```mermaid\s*(.*?)```", re.DOTALL)
    for index, match in enumerate(markdown_pattern.finditer(cleaned), 1):
        block = textwrap.dedent(match.group(1)).strip()
        if block.startswith(SUPPORTED_PREFIXES):
            examples.append({
                "source": f"{source_name}-mermaid",
                "index": index,
                "diagram": block,
            })

    return examples


def diagram_type(diagram: str) -> str:
    first_line = diagram.splitlines()[0].strip()
    if first_line.startswith(("flowchart", "graph")):
        return "flowchart"
    if first_line.startswith("sequenceDiagram"):
        return "sequence"
    if first_line.startswith("stateDiagram"):
        return "state"
    if first_line.startswith("erDiagram"):
        return "er"
    if first_line.startswith("classDiagram"):
        return "class"
    return "unknown"


def capture_canvas(tool: MermaidDiagramTool, output_path: Path) -> None:
    tool.root.update_idletasks()
    export_bounds = tool.get_export_bounds()
    if not export_bounds:
        raise RuntimeError("No canvas content available for export")
    image = tool.render_canvas_to_png_image(export_bounds)
    image.save(output_path, format="PNG")


def load_font(size: int):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def build_contact_sheet_page(image_paths: list[Path], labels: list[str], output_path: Path, title: str) -> None:
    if not image_paths:
        return

    thumb_w = 520
    thumb_h = 340
    margin = 20
    header_h = 60
    label_h = 44
    columns = 2
    rows = math.ceil(len(image_paths) / columns)
    sheet_w = (columns * thumb_w) + ((columns + 1) * margin)
    sheet_h = header_h + (rows * (thumb_h + label_h + margin)) + margin

    sheet = Image.new("RGB", (sheet_w, sheet_h), "white")
    draw = ImageDraw.Draw(sheet)
    title_font = load_font(28)
    label_font = load_font(16)
    draw.text((margin, 16), title, fill="black", font=title_font)

    for idx, image_path in enumerate(image_paths):
        image = Image.open(image_path).convert("RGB")
        image.thumbnail((thumb_w, thumb_h))
        col = idx % columns
        row = idx // columns
        x = margin + col * (thumb_w + margin)
        y = header_h + row * (thumb_h + label_h + margin)
        sheet.paste(image, (x, y))
        draw.rectangle((x, y, x + image.width, y + image.height), outline="#cccccc", width=1)
        label = labels[idx]
        draw.text((x, y + thumb_h + 8), label[:70], fill="black", font=label_font)

    sheet.save(output_path)


def build_contact_sheets(image_paths: list[Path], labels: list[str], output_path: Path, title: str, max_per_sheet: int = 12) -> None:
    if not image_paths:
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    chunks = [
        (image_paths[index:index + max_per_sheet], labels[index:index + max_per_sheet])
        for index in range(0, len(image_paths), max_per_sheet)
    ]

    if len(chunks) == 1:
        build_contact_sheet_page(chunks[0][0], chunks[0][1], output_path, title)
        return

    stem = output_path.stem
    suffix = output_path.suffix
    for page_index, (page_images, page_labels) in enumerate(chunks, 1):
        page_title = f"{title} (Page {page_index}/{len(chunks)})"
        page_name = output_path.with_name(f"{stem}_{page_index:02d}{suffix}")
        build_contact_sheet_page(page_images, page_labels, page_name, page_title)

    build_contact_sheet_page(chunks[0][0], chunks[0][1], output_path, f"{title} (Page 1/{len(chunks)})")


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    output_dir = base_dir / "official_example_checks"
    renders_dir = output_dir / "renders"
    output_dir.mkdir(exist_ok=True)
    renders_dir.mkdir(exist_ok=True)

    raw_examples = []
    for source_name, url in DOC_SOURCES.items():
        text = fetch_text(url)
        raw_examples.extend(extract_examples(text, source_name))

    unique = {}
    for example in raw_examples:
        key = example["diagram"]
        if key not in unique:
            unique[key] = example

    examples = list(unique.values())
    examples.sort(key=lambda item: (diagram_type(item["diagram"]), item["source"], item["index"]))

    tool = MermaidDiagramTool()
    tool.root.geometry("1500x980+80+80")
    tool.root.lift()
    tool.root.attributes("-topmost", True)
    tool.root.update_idletasks()
    tool.root.update()

    results = []
    grouped_images = defaultdict(list)
    grouped_labels = defaultdict(list)

    try:
        for idx, example in enumerate(examples, 1):
            dtype = diagram_type(example["diagram"])
            result = {
                "id": idx,
                "type": dtype,
                "source": example["source"],
                "source_index": example["index"],
                "status": "unknown",
                "image": None,
                "error": None,
            }
            try:
                tool.set_zoom_level(1.0)
                tool.parse_mermaid(example["diagram"], apply_auto_layout=True)
                tool.root.title(f"Official Example Check {idx}: {dtype}")
                image_name = f"{dtype}_{idx:03d}.png"
                image_path = renders_dir / image_name
                capture_canvas(tool, image_path)
                result["status"] = "rendered"
                result["image"] = str(image_path)
                grouped_images[dtype].append(image_path)
                grouped_labels[dtype].append(f"{idx}. {example['source']} #{example['index']}")
            except Exception as exc:
                result["status"] = "failed"
                result["error"] = str(exc)
            results.append(result)
    finally:
        tool.root.attributes("-topmost", False)
        tool.root.destroy()

    for dtype, image_paths in grouped_images.items():
        build_contact_sheets(
            image_paths,
            grouped_labels[dtype],
            output_dir / f"{dtype}_contact_sheet.png",
            f"Official Mermaid Examples: {dtype}",
        )

    with open(output_dir / "results.json", "w", encoding="utf-8") as handle:
        json.dump(
            {
                "sources": DOC_SOURCES,
                "total_examples": len(examples),
                "results": results,
            },
            handle,
            indent=2,
        )

    summary = defaultdict(lambda: {"rendered": 0, "failed": 0})
    for result in results:
        summary[result["type"]][result["status"]] += 1

    for dtype in sorted(summary):
        stats = summary[dtype]
        print(f"{dtype}: rendered={stats['rendered']} failed={stats['failed']}")
    print(f"total={len(results)}")


if __name__ == "__main__":
    main()
