from mermaid_diagram_tool import MermaidDiagramTool


def parse_scrollregion(canvas):
    return tuple(map(float, canvas.cget("scrollregion").split()))


def run():
    tool = MermaidDiagramTool()
    tool.root.geometry("1400x900+100+100")
    tool.root.update_idletasks()
    tool.root.update()

    try:
        tool.clear_diagram()
        tool.diagram_type = "classDiagram"
        tool.diagram_type_var.set("classDiagram")
        tool.update_diagram_type_ui()

        tool.add_class_at_position(150, 150)
        tool.show_grid.set(True)
        tool.toggle_grid()
        tool.root.update_idletasks()
        tool.root.update()

        initial_region = parse_scrollregion(tool.canvas)
        initial_grid_count = len(tool.canvas.find_withtag("grid"))
        if initial_grid_count == 0:
            raise AssertionError("Grid did not render when enabled")

        tool.add_class_at_position(3200, 2400)
        tool.root.update_idletasks()
        tool.root.update()

        expanded_region = parse_scrollregion(tool.canvas)
        expanded_grid_count = len(tool.canvas.find_withtag("grid"))

        if expanded_region[2] <= initial_region[2] or expanded_region[3] <= initial_region[3]:
            raise AssertionError(
                f"Scroll region did not expand: before={initial_region}, after={expanded_region}"
            )

        if expanded_grid_count <= initial_grid_count:
            raise AssertionError(
                f"Grid did not redraw for larger region: before={initial_grid_count}, after={expanded_grid_count}"
            )

        tool.on_h_scroll("moveto", "0.5")
        tool.on_v_scroll("moveto", "0.5")
        tool.root.update_idletasks()
        tool.root.update()

        xview = tool.canvas.xview()
        yview = tool.canvas.yview()
        if xview[0] <= 0 or yview[0] <= 0:
            raise AssertionError(f"Scroll handlers did not move viewport: xview={xview}, yview={yview}")

        tool.show_grid.set(False)
        tool.toggle_grid()
        tool.root.update_idletasks()
        tool.root.update()
        if tool.canvas.find_withtag("grid"):
            raise AssertionError("Grid items remained after disabling the grid")

        print("grid and scroll smoke test passed")
    finally:
        tool.root.destroy()


if __name__ == "__main__":
    run()
