#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Example 08: Multi-Diagram Project Management with Workspace & Coordinate Jitter
Demonstrates:
1. Centralized configuration with custom jitter (randomized visual displacement)
2. Generating multiple independent diagram models (1 Diagram = 1 Independent File)
3. Auto-detecting and registering each model into a PowerDesigner Workspace (.sws)
4. High-resolution export with automatic whitespace trimming
"""

import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pd_com_edit import (
    PowerDesignerClient,
    UseCaseDiagramBuilder,
    SequenceDiagramBuilder,
    PdmBuilder,
    ImageExporter,
    PDConfig,
    JitterConfig,
    FileNamingConfig,
    WorkspaceConfig,
    set_config,
)


def main():
    print("=== PowerDesigner Multi-Diagram & Workspace Demo ===")

    # 1. Setup Configuration: enable slight random jitter and independent file naming
    custom_cfg = PDConfig(
        jitter=JitterConfig(
            enabled=True,
            range_x=(-300, 300),   # Slight random horizontal shift
            range_y=(-200, 200),   # Slight random vertical shift
            seed=42,               # Reproducible seed (or set None for pure random)
        ),
        file_naming=FileNamingConfig(
            separate_files=True,
            output_dir="./output_models",
            prefix="System_",
            suffix="_Model"
        ),
        workspace=WorkspaceConfig(
            auto_detect=True,
            auto_register=True,
            auto_create=True,
            workspace_name="OrderSystem_Workspace"
        )
    )
    set_config(custom_cfg)

    # 2. Connect to PowerDesigner
    print("[1/5] Connecting to PowerDesigner COM Client...")
    client = PowerDesignerClient(visible=False)

    try:
        # ---------------------------------------------------------
        # DIAGRAM 1: Use Case Diagram -> Saved as independent file
        # ---------------------------------------------------------
        print("[2/5] Creating Diagram 1: Use Case Diagram...")
        model_uc, diag_uc = client.create_dedicated_diagram("01_UseCase", diagram_type="usecase")
        # Attach Use Case Builder
        uc_builder = UseCaseDiagramBuilder(diag_uc)
        uc_builder.add_actor("Customer")
        uc_builder.add_actor("Administrator", is_secondary=True)
        uc_builder.add_use_case("UC1: Place Order", column=2)
        uc_builder.add_use_case("UC2: Query Inventory", column=2)
        uc_builder.add_use_case("UC3: Process Payment", column=3)
        uc_builder.link("Customer", "UC1: Place Order")
        uc_builder.link("Customer", "UC2: Query Inventory")
        uc_builder.link("Administrator", "UC3: Process Payment")

        # Save independently & register to workspace with folder grouping
        saved_uc_path = client.save_diagram_as_file(model_uc, "01_UseCase", folder="业务用例")
        print(f"      -> Saved Diagram 1 to: {saved_uc_path}")

        # ---------------------------------------------------------
        # DIAGRAM 2: Sequence Diagram -> Saved as independent file
        # ---------------------------------------------------------
        print("[3/5] Creating Diagram 2: Sequence Diagram...")
        model_seq, diag_seq = client.create_dedicated_diagram("02_OrderSequence", diagram_type="sequence")
        seq_builder = SequenceDiagramBuilder(diag_seq)
        seq_builder.add_lifeline("Customer", is_actor=True)
        seq_builder.add_lifeline("OrderService")
        seq_builder.add_lifeline("InventoryService")
        seq_builder.add_lifeline("PaymentGateway")

        seq_builder.add_message("Customer", "OrderService", "submitOrder(items)")
        seq_builder.add_message("OrderService", "InventoryService", "reserveStock(items)")
        seq_builder.add_message("InventoryService", "OrderService", "stockReserved()", is_return=True)
        seq_builder.add_message("OrderService", "PaymentGateway", "authorizePayment(amount)")
        seq_builder.add_message("PaymentGateway", "OrderService", "paymentApproved()", is_return=True)
        seq_builder.add_message("OrderService", "Customer", "orderConfirmation()", is_return=True)
        seq_builder.build_messages()

        # Save independently & register to workspace with folder grouping
        saved_seq_path = client.save_diagram_as_file(model_seq, "02_OrderSequence", folder="业务时序")
        print(f"      -> Saved Diagram 2 to: {saved_seq_path}")

        # ---------------------------------------------------------
        # DIAGRAM 3: Physical Database Model (PDM) -> Saved as file
        # ---------------------------------------------------------
        print("[4/5] Creating Diagram 3: Physical Database Model (PDM)...")
        model_pdm, diag_pdm = client.create_dedicated_diagram("03_DatabaseSchema", diagram_type="pdm", language_or_dbms="PostgreSQL 15")
        pdm_builder = PdmBuilder(model_pdm, diagram=diag_pdm)
        pdm_builder.add_table(
            code="t_orders",
            name="Orders",
            columns=[
                {"code": "order_id", "name": "Order ID", "type": "VARCHAR(36)", "pk": True},
                {"code": "customer_id", "name": "Customer ID", "type": "VARCHAR(36)", "mandatory": True},
                {"code": "total_amount", "name": "Total Amount", "type": "NUMERIC(12,2)"},
                {"code": "created_at", "name": "Created At", "type": "TIMESTAMP"},
            ]
        )
        pdm_builder.add_table(
            code="t_order_items",
            name="Order Items",
            columns=[
                {"code": "item_id", "name": "Item ID", "type": "VARCHAR(36)", "pk": True},
                {"code": "order_id", "name": "Order ID", "type": "VARCHAR(36)", "mandatory": True},
                {"code": "sku_code", "name": "SKU Code", "type": "VARCHAR(64)", "mandatory": True},
                {"code": "quantity", "name": "Quantity", "type": "INTEGER"},
            ]
        )
        pdm_builder.add_reference(
            parent_table="t_orders",
            child_table="t_order_items",
            parent_col="order_id",
            child_col="order_id",
            name="FK_Order_Items"
        )

        # Save independently & register to workspace with folder grouping
        saved_pdm_path = client.save_diagram_as_file(model_pdm, "03_DatabaseSchema", folder="数据库架构")
        print(f"      -> Saved Diagram 3 to: {saved_pdm_path}")

        # ---------------------------------------------------------
        # Inspect Workspace
        # ---------------------------------------------------------
        print("[5/5] Checking Workspace Status...")
        ws_path = client.workspace_mgr.workspace_path
        print(f"      Workspace Location: {ws_path}")
        models_in_ws = client.workspace_mgr.list_models()
        print(f"      Total Registered Models in Workspace: {len(models_in_ws)}")
        for idx, m in enumerate(models_in_ws, 1):
            folder_tag = f" [Folder: {m['folder']}]" if m.get("folder") else ""
            print(f"        {idx}. {m['name']} -> {m['url']}{folder_tag}")

        print("\nAll diagrams successfully generated, saved as distinct files, and registered in workspace!")

    finally:
        client.close_all_safely(save_changes=False)


if __name__ == "__main__":
    main()
