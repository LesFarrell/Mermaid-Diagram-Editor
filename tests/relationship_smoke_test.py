from mermaid_diagram_tool import (
    MermaidDiagramTool,
    ClassBox,
    Relationship,
    FlowchartNode,
    FlowchartConnection,
    SequenceActor,
    SequenceMessage,
    StateNode,
    StateTransition,
    EREntity,
    ERRelationship,
)


def assert_changed(before, after, label):
    if before == after:
        raise AssertionError(f"{label} did not change after redraw")


def bbox(canvas, item):
    return tuple(round(value, 2) for value in canvas.bbox(item))


def run():
    tool = MermaidDiagramTool()
    tool.root.geometry("1200x900+100+100")
    tool.root.update_idletasks()
    tool.root.update()

    try:
        # Class relationships
        tool.clear_diagram()
        tool.diagram_type = "classDiagram"
        a = ClassBox(tool.canvas, 120, 120, "Alpha", tool)
        b = ClassBox(tool.canvas, 460, 220, "Beta", tool)
        tool.classes.extend([a, b])
        rel = Relationship(tool.canvas, a, b, "association", tool)
        tool.relationships.append(rel)
        before = bbox(tool.canvas, rel.line)
        a.move(100, 40)
        tool.update_relationships()
        after = bbox(tool.canvas, rel.line)
        assert_changed(before, after, "Class relationship line")
        before_label = bbox(tool.canvas, rel.label_text) if hasattr(rel, "label_text") and rel.label_text else None
        rel.label = "uses"
        rel.update_position()
        if rel.label_text:
            after_label = bbox(tool.canvas, rel.label_text)
            if before_label is not None:
                assert_changed(before_label, after_label, "Class relationship label")

        # Flowchart relationships
        tool.clear_diagram()
        tool.diagram_type = "flowchart"
        n1 = FlowchartNode(tool.canvas, 100, 100, "A", "Start", "rectangle", tool)
        n2 = FlowchartNode(tool.canvas, 420, 160, "B", "Finish", "diamond", tool)
        tool.flowchart_nodes.extend([n1, n2])
        flow = FlowchartConnection(tool.canvas, n1, n2, "arrow", "next", tool)
        tool.flowchart_connections.append(flow)
        before = bbox(tool.canvas, flow.line)
        n2.x += 80
        n2.y += 50
        n2.create_visual()
        tool.update_relationships()
        after = bbox(tool.canvas, flow.line)
        assert_changed(before, after, "Flowchart connection line")

        # Sequence relationships
        tool.clear_diagram()
        tool.diagram_type = "sequenceDiagram"
        actor_a = SequenceActor(tool.canvas, 120, 80, "User", tool)
        actor_b = SequenceActor(tool.canvas, 420, 80, "Service", tool)
        tool.sequence_actors.extend([actor_a, actor_b])
        msg = SequenceMessage(tool.canvas, actor_a, actor_b, "sync", "request", 0, tool)
        tool.sequence_messages.append(msg)
        before = bbox(tool.canvas, msg.line)
        actor_b.x += 100
        actor_b.create_visual()
        tool.update_relationships()
        after = bbox(tool.canvas, msg.line)
        assert_changed(before, after, "Sequence message line")

        # State relationships
        tool.clear_diagram()
        tool.diagram_type = "stateDiagram"
        s1 = StateNode(tool.canvas, 150, 150, "Draft", tool)
        s2 = StateNode(tool.canvas, 480, 220, "Review", tool)
        tool.state_nodes.extend([s1, s2])
        st = StateTransition(tool.canvas, s1, s2, "submit", tool)
        tool.state_transitions.append(st)
        before = bbox(tool.canvas, st.line)
        s2.x += 60
        s2.y -= 40
        s2.create_visual()
        tool.update_relationships()
        after = bbox(tool.canvas, st.line)
        assert_changed(before, after, "State transition line")

        # ER relationships
        tool.clear_diagram()
        tool.diagram_type = "erDiagram"
        e1 = EREntity(tool.canvas, 150, 150, "CUSTOMER", tool)
        e2 = EREntity(tool.canvas, 500, 260, "ORDER", tool)
        tool.er_entities.extend([e1, e2])
        er = ERRelationship(tool.canvas, e1, e2, "one-to-many", "places", tool)
        tool.er_relationships.append(er)
        before = bbox(tool.canvas, er.line)
        e2.x += 70
        e2.create_visual()
        tool.update_relationships()
        after = bbox(tool.canvas, er.line)
        assert_changed(before, after, "ER relationship line")

        # Zoom redraw should also recreate all connections
        tool.apply_zoom(1.15, center_x=300, center_y=200)
        tool.root.update_idletasks()
        tool.root.update()

        print("relationship smoke test passed")
    finally:
        tool.root.destroy()


if __name__ == "__main__":
    run()
