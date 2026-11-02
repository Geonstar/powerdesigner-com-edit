---
name: powerdesigner-com-edit
description: Automate SAP PowerDesigner modeling, diagram layout, collision/overlap checking, activation bar generation, workspace management, and batch export via Python COM. Use when creating/editing OOM, CDM, or PDM models, generating sequence diagrams with exact activation bars and alt frames, arranging use case diagrams, fixing overlapping text/lines/activation bars, configuring coordinate jitter, managing .sws workspaces, or exporting clean diagrams for reports.
---

# PowerDesigner COM Automation & Edit Skill (`powerdesigner-com-edit`)

Use this skill to automate, construct, audit, resolve visual overlaps, and batch-export SAP PowerDesigner 16.5+ models (OOM, CDM, PDM) using Python and `pywin32`.

## Core Capabilities

1. **Centralized Configuration (`pd_config.json`)**:
   - Zero hardcoding: Control coordinate offsets, file prefixes/suffixes, layout gaps, and export rules via JSON/YAML.
2. **Visual Jitter / Coordinate Perturbation (随机坐标微调)**:
   - Configurable slight random variations to element positions (`range_x`, `range_y`), eliminating rigid, copy-paste aesthetic slop.
3. **Independent Model File Generation (单图独立文件)**:
   - Each diagram is created and saved into its own dedicated file (e.g. `图1_用例图.oom`, `图2_顺序图.oom`, `图3_物理数据模型.pdm`), avoiding giant, unmaintainable single-file dumps.
4. **Workspace Auto-Detection & Management (`.sws` / `.pbw`)**:
   - Automatically discovers or creates a PowerDesigner Workspace file and registers newly generated model files into it, keeping the entire project organized in the PowerDesigner Object Browser tree.
5. **Headless & Interactive COM Control**:
   - Programmatically launch, connect, inspect, and modify PowerDesigner models without manual mouse clicks.
6. **Collision Detection & Overlap Auditing (重叠检查与自动规避)**:
   - **AABB Geometric Collision Check**: Audits all diagram symbols for bounding box and label intersections.
   - **Activation Bar Collision Check**: Verifies 0 same-depth intersecting activation intervals on all lifelines.
   - **Auto-Resolution Layout Shift**: Automatically adjusts vertical/horizontal coordinates to enforce minimum clearance.
   - **Draft Annotation Cleaner**: Automatically identifies and deletes lingering development notes.
7. **Sequence Diagram Automation**:
   - Timeline placement of lifelines and synchronous/asynchronous messages with nesting offsets (`X_offset = X_base + depth * 120`).
   - Combined fragment (`alt`, `opt`, `loop`) dynamic boundary calculation.
8. **Use Case & Class Diagram Layout**:
   - Canonical 4-column use case layout and vertical tree class hierarchy.
   - Guaranteed link attachments via `AttachLinkObject` (`attach_link_symbol`).
9. **Clean Production Export**:
   - High-res PNG/EMF diagram export with automated whitespace cropping.

---

## 1. Quick Start & Project-Wide Workflow

### Centralized Configuration File (`pd_config.json`)
You can place a `pd_config.json` in your workspace root to configure all options without modifying code:

```json
{
  "jitter": {
    "enabled": true,
    "range_x": [-300, 300],
    "range_y": [-200, 200],
    "seed": null
  },
  "workspace": {
    "auto_detect": true,
    "auto_register": true,
    "auto_create": true,
    "workspace_name": "ProjectWorkspace"
  },
  "file_naming": {
    "separate_files": true,
    "output_dir": "./output_models",
    "prefix": "图_",
    "suffix": "_工程"
  }
}
```

### Complete Code Pattern: Independent Diagrams + Workspace Registration
```python
from pd_com_edit import (
    PowerDesignerClient,
    SequenceDiagramBuilder,
    UseCaseDiagramBuilder,
    PdmBuilder,
    ImageExporter,
    PDConfig,
    JitterConfig,
    set_config,
)

# 1. Initialize Client (reads pd_config.json automatically if present)
client = PowerDesignerClient(visible=False)

try:
    # 2. Diagram 1: Use Case Diagram -> Saved to independent file & registered in workspace
    model_uc = client.create_diagram_model("01_用例图", model_type="OOM")
    diag_uc = model_uc.UseCases.CreateNew()
    uc_builder = UseCaseDiagramBuilder(diag_uc)
    uc_builder.add_actor("用户")
    uc_builder.add_actor("后台管理系统", is_secondary=True)
    uc_builder.add_use_case("登录鉴权", column=2)
    uc_builder.add_use_case("创建订单", column=2)
    uc_builder.link("用户", "登录鉴权")
    uc_builder.link("用户", "创建订单")
    # Saves as ./output_models/图_01_用例图_工程.oom and registers to .sws
    client.save_diagram_as_file(model_uc, "01_用例图")

    # 3. Diagram 2: Sequence Diagram -> Saved to independent file & registered in workspace
    model_seq = client.create_diagram_model("02_系统时序图", model_type="OOM")
    diag_seq = model_seq.SequenceDiagrams.CreateNew()
    seq_builder = SequenceDiagramBuilder(diag_seq)
    seq_builder.add_lifeline("用户", is_actor=True)
    seq_builder.add_lifeline("网关服务")
    seq_builder.add_lifeline("订单中心")
    seq_builder.add_message("用户", "网关服务", "POST /orders")
    seq_builder.add_message("网关服务", "订单中心", "createOrder()")
    seq_builder.add_message("订单中心", "网关服务", "201 Created", is_return=True)
    seq_builder.add_message("网关服务", "用户", "200 OK", is_return=True)
    seq_builder.build_messages()
    client.save_diagram_as_file(model_seq, "02_系统时序图")

    # 4. Workspace Status
    print(f"Workspace path: {client.workspace_mgr.workspace_path}")
    for item in client.workspace_mgr.list_models():
        folder_tag = f" [{item['folder']}]" if item.get("folder") else ""
        print(f"Registered model: {item['name']} -> {item['url']}{folder_tag}")

finally:
    client.close_all_safely()
```

### Declarative Pipeline API (One-Shot Diagram Construction)
For rapid agentic construction without boilerplate model/diagram lifecycle management, use the top-level pipeline functions:

```python
from pd_com_edit import (
    build_sequence_diagram,
    build_usecase_diagram,
    build_pdm_diagram,
)

# 1. Sequence Diagram in one call:
res_seq = build_sequence_diagram(
    name="01_用户下单时序",
    lifelines=[
        {"name": "买家", "is_actor": True},
        "订单网关",
        "库存服务",
        "支付中心",
    ],
    messages=[
        {"sender": "买家", "receiver": "订单网关", "label": "submitOrder()"},
        {"sender": "订单网关", "receiver": "库存服务", "label": "checkAndDeduct()"},
        {"sender": "库存服务", "receiver": "订单网关", "label": "stockOk", "is_return": True},
        {"sender": "订单网关", "receiver": "支付中心", "label": "createPayment()"},
        {"sender": "支付中心", "receiver": "订单网关", "label": "payUrl", "is_return": True},
        {"sender": "订单网关", "receiver": "买家", "label": "orderCreated", "is_return": True},
    ],
    folder="交易模块",          # Groups model into <Folder Name="交易模块"> inside .sws
    export_image=True,         # Auto-exports cropped PNG
)
print(f"Model saved to: {res_seq['model_path']}")
print(f"Image exported to: {res_seq['image_path']}")

# 2. Use Case Diagram in one call:
res_uc = build_usecase_diagram(
    name="02_订单用例图",
    actors=["客户", {"name": "支付系统", "is_secondary": True}],
    usecases=["浏览商品", "下单支付", "申请退款"],
    links=[("客户", "浏览商品"), ("客户", "下单支付"), ("支付系统", "下单支付")],
    folder="订单模块",
)

# 3. Physical Data Model (PDM) in one call:
res_pdm = build_pdm_diagram(
    name="03_交易数据库模型",
    tables=[
        {
            "code": "orders",
            "name": "订单表",
            "columns": [
                {"code": "order_id", "pk": True, "type": "BIGINT"},
                {"code": "buyer_id", "type": "BIGINT", "mandatory": True},
                {"code": "amount", "type": "DECIMAL(12,2)"},
            ]
        },
        {
            "code": "order_items",
            "name": "订单明细表",
            "columns": [
                {"code": "item_id", "pk": True, "type": "BIGINT"},
                {"code": "order_id", "type": "BIGINT", "mandatory": True},
                {"code": "sku_code", "type": "VARCHAR(64)"},
            ]
        }
    ],
    references=[
        {
            "parent_table": "orders",
            "child_table": "order_items",
            "parent_col": "order_id",
            "child_col": "order_id",
            "name": "FK_ORDER_ITEMS",
        }
    ],
    folder="数据库模型",
)
```

### PowerDesigner CLI Utilities
The CLI supports workspace synchronization, config generation, note cleaning, and batch diagram export:

```bash
# Initialize external configuration file (pd_config.json)
pd-edit init-config

# List all registered models in the detected or specified workspace
pd-edit workspace --list

# Scan directory for all .oom / .pdm files and synchronize missing entries into workspace
pd-edit workspace --sync ./output_models

# Strip draft annotations from existing model
pd-edit clean-notes ./output_models/图_01_用例图_工程.oom --save

# Batch export all diagrams in a model to PNG with auto-crop
pd-edit export ./output_models/图_01_用例图_工程.oom --out-dir ./exports

# Force-terminate any frozen background PowerDesigner instances
pd-edit kill-pd
```

---

## 2. Collision Detection & Overlap Prevention (重叠排查与修复)

### 1. Activation Bar Overlaps
When multiple calls hit the same lifeline:
- **Root Cause**: Scripts rendering activation rectangles at identical X coordinates without tracking call depth.
- **Auto-Fix**: `SequenceDiagramBuilder` automatically computes call nesting depth. If `depth > 0`, horizontal position is shifted:
  `X_offset = X_base + depth * 120`
- **Verification**: `CollisionDetector.audit_activation_bar_overlaps(completed_bars)` ensures 0 intervals intersect on identical depths.

### 2. Symbol & Text Overlaps (AABB Collision)
```python
# Audit all symbols for overlapping bounding boxes
overlapping_pairs = CollisionDetector.audit_symbol_overlaps(diagram, clearance=150)
if overlapping_pairs:
    print(f"Found {len(overlapping_pairs)} colliding symbols! Auto-resolving...")
    CollisionDetector.auto_resolve_vertical_overlaps([p[1] for p in overlapping_pairs], min_spacing=300)
```

### 3. Cleaning Draft / Stray Annotations
Before submission or publication, strip development-phase text notes that cause label confusion:
```python
# Automatically removes text symbols matching draft patterns
removed = CollisionDetector.strip_draft_notes(diagram, keywords=[
    "实现中", "待整链验收", "兼有教学管理", "系统用例不能", "计划图等同"
])
print(f"Removed {removed} stray draft notes.")
```

---

## 3. Combined Fragments (`alt`, `opt`, `loop`)

To create clean branching blocks without manual coordinate guessing:

```python
# Bounding Box Math for alt / opt:
x_left = min(lifeline.x for lifeline in participants) - 400
x_right = max(lifeline.x for lifeline in participants) + 400
y_top = start_msg.y + 300
y_bottom = end_msg.y - 300

fragment = model.CombinedFragments.CreateNew()
fragment.SetName("alt")
frag_sym = diagram.AttachObject(fragment)
frag_sym.Position.X = (x_left + x_right) // 2
frag_sym.Position.Y = (y_top + y_bottom) // 2
frag_sym.Size.Width = x_right - x_left
frag_sym.Size.Height = y_top - y_bottom
```

---

## 4. Use Case Diagram Layout (防重叠三列布局)

To prevent line crossings and text collisions:
- **Column 1 (`X ≈ 1,500`)**: Primary Actors (e.g. Operator, Inspector, Dispatcher).
- **Column 2 (`X ≈ 5,500`)**: Use Cases inside System Boundary (`Width=3200, Height=1000, step_y=-1200`).
- **Column 3 (`X ≈ 9,500`)**: Secondary Actors / External Systems (e.g. Customer, Audit System).

Associations are drawn left-to-right into Column 2, ensuring clean horizontal connections with zero diagonal label collisions.

### Connector Attachment Rules (No Missing Lines)
- 2D symbols use `diagram.AttachObject(obj)`.
- 1D connectors (associations, dependencies, generalizations, references, instance links, flows, transitions) **must** use `diagram.AttachLinkObject(link)` via `attach_link_symbol()`.
- Set `link.Object1` and `link.Object2` before calling `AttachLinkObject`. Calling `AttachObject` on links silently fails to render line symbols.

---

## 5. Communication / Collaboration Diagram (协作图 / 通信图)

Communication diagrams represent object interaction focusing on structural relationships and message paths with explicit call sequence numbers (`1: submitOrder()`, `1.1: lockRoom()`, `2: processPayment()`):

```python
from pd_com_edit import PowerDesignerClient, CommunicationDiagramBuilder

client = PowerDesignerClient(visible=False)
model = client.create_oom(name="Booking_Collaboration")
diag = model.CommunicationDiagrams.CreateNew()

builder = CommunicationDiagramBuilder(diag, center_x=0, center_y=0, default_radius=18000)
builder.add_actor("Guest")
builder.add_object("OrderController")
builder.add_object("PaymentService")
builder.add_object("RoomInventoryService")

# Add numbered directional messages along structural instance links
builder.add_message("Guest", "OrderController", "submitBooking(info)", sequence_number="1:")
builder.add_message("OrderController", "RoomInventoryService", "lockRoom(roomId)", sequence_number="1.1:")
builder.add_message("OrderController", "PaymentService", "charge(amount)", sequence_number="2:")

# Radial star topology prevents crossing link lines
builder.layout_radial(center_name="OrderController", radius=18000)
builder.diagram.ExportImage("output/collaboration-flow.png")
```

---

## 6. Activity & State Machine Diagrams (活动图与状态机图)

### Activity Diagram (活动图)
```python
from pd_com_edit import ActivityDiagramBuilder

act_diag = model.ActivityDiagrams.CreateNew()
builder = ActivityDiagramBuilder(act_diag)
builder.add_activity("Fill Order Details")
builder.add_decision("Is Room Available?")
builder.add_activity("Process Payment")

builder.add_flow("Fill Order Details", "Is Room Available?")
builder.add_flow("Is Room Available?", "Process Payment", guard="Available")
builder.layout_vertical()
```

### State Machine / Statechart Diagram (状态机图)
```python
from pd_com_edit import StatechartDiagramBuilder

st_diag = model.StatechartDiagrams.CreateNew()
builder = StatechartDiagramBuilder(st_diag)
builder.add_state("PendingPayment")
builder.add_state("OrderConfirmed")
builder.add_state("Completed")

builder.add_transition("PendingPayment", "OrderConfirmed", event="paySuccess", guard="amount > 0", action="emitReceipt()")
builder.add_transition("OrderConfirmed", "Completed", event="checkOut")
builder.layout_pipeline()
```

---

## 7. Software Engineering Diagram Coverage Matrix

| Diagram Type | PlantUML Equivalent | PowerDesigner Metaclass | Skill Builder | SE Purpose |
|---|---|---|---|---|
| **Use Case Diagram** | `@startuml ... (UC)` | `UseCaseDiagram` | `UseCaseDiagramBuilder` | Requirements analysis: Actors and capabilities |
| **Sequence Diagram** | `@startuml ... ->` | `SequenceDiagram` | `SequenceDiagramBuilder` | Interaction: Chronological message timeline |
| **Communication / Collaboration** | `@startuml ...` (annotated) | `CommunicationDiagram` | `CommunicationDiagramBuilder` | Interaction: Object topology with sequence numbers |
| **Class Diagram** | `@startuml class ...` | `ClassDiagram` | `ClassDiagramBuilder` | Static architecture: OOP attributes, methods, inheritance |
| **Activity Diagram** | `@startuml :start; ...` | `ActivityDiagram` | `ActivityDiagramBuilder` | Workflow: Business processes, decisions, and joins |
| **State Machine Diagram** | `@startuml [*] --> ...` | `StatechartDiagram` | `StatechartDiagramBuilder` | Lifecycle: Entity states and event transitions |
| **Component Diagram** | `@startuml [Comp] ...` | `ComponentDiagram` | `ComponentDiagramBuilder` | High-level modular architecture and dependencies |
| **Deployment Diagram** | `@startuml node ...` | `DeploymentDiagram` | `DeploymentDiagramBuilder` | Physical infrastructure, nodes, and networking |
| **Physical Data Model (PDM)** | `@startuml entity/er` | `PhysicalDiagram` | `PdmBuilder` | Storage: Relational schema, tables, PK/FK joins |

---

## 8. Process Hygiene & Error Recovery

PowerDesigner's COM server (`pdshell16.exe`) can linger in memory if an exception occurs before `Quit()`, causing file-locking errors:

```powershell
# Kill lingering instances via PowerShell
Stop-Process -Name pdshell16 -Force -ErrorAction SilentlyContinue
```

In Python:
```python
from scripts.pd_automation import PowerDesignerClient
PowerDesignerClient.kill_lingering_processes()
```

---

## 9. References & Scripts

- [Overlap Detection Guide](references/overlap_detection_guide.md)
- [COM API Cheatsheet](references/com_api_cheatsheet.md)
- [Standalone Python Utility](scripts/pd_automation.py)
