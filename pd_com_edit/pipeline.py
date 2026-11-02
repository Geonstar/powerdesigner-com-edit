#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Declarative High-Level Diagram Pipeline (pd_com_edit.pipeline)
Provides one-call declarative generation for:
- Sequence Diagrams (with activation bars, alt frames, auto-crop, independent file saving, and workspace registration)
- Use Case Diagrams (with 3-column layout, verified association links, and collision avoidance)
- Physical Data Models (with PK/FK reference joins and relational schemas)
"""

import os
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Any, Union

from .client import PowerDesignerClient
from .config import get_config
from .sequence import SequenceDiagramBuilder
from .usecase import UseCaseDiagramBuilder
from .pdm import PdmBuilder
from .export import ImageExporter


def build_sequence_diagram(
    name: str,
    lifelines: List[Union[str, Dict[str, Any]]],
    messages: List[Dict[str, Any]],
    fragments: Optional[List[Dict[str, Any]]] = None,
    client: Optional[PowerDesignerClient] = None,
    folder: Optional[str] = None,
    output_dir: Optional[str] = None,
    export_image: bool = True,
    auto_crop: bool = True,
    close_after_build: bool = True,
) -> Dict[str, Any]:
    """
    Declarative one-step builder for Sequence Diagrams.
    Handles:
    - Model creation with default diagram cleanup
    - Lifeline and message timeline layout with jitter and activation stacks
    - Independent file saving and PowerDesigner workspace registration
    - High-resolution image export with whitespace auto-crop
    """
    cfg = get_config()
    own_client = False
    if client is None:
        client = PowerDesignerClient(visible=cfg.com.visible)
        own_client = True

    try:
        model, diagram = client.create_dedicated_diagram(name, diagram_type="sequence")
        builder = SequenceDiagramBuilder(diagram)

        # 1. Lifelines
        for item in lifelines:
            if isinstance(item, str):
                builder.add_lifeline(item)
            elif isinstance(item, dict):
                l_name = item.get("name", "Object")
                is_actor = item.get("is_actor", False)
                builder.add_lifeline(l_name, is_actor=is_actor)

        # 2. Messages
        for msg in messages:
            s_name = msg.get("sender")
            r_name = msg.get("receiver")
            label = msg.get("label", "")
            is_ret = msg.get("is_return", False)
            m_type = msg.get("type", "sync")
            builder.add_message(s_name, r_name, label=label, is_return=is_ret, message_type=m_type)

        # 3. Combined Fragments
        if fragments:
            for frag in fragments:
                builder.add_combined_fragment(
                    operator=frag.get("operator", "alt"),
                    participants=frag.get("participants", []),
                    start_msg_idx=frag.get("start_msg_idx", 0),
                    end_msg_idx=frag.get("end_msg_idx", len(messages) - 1),
                    guard=frag.get("guard", ""),
                )

        # 4. Render messages & activation bars
        builder.build_messages()

        # 5. Save independent model file & register workspace
        model_path = client.save_diagram_as_file(
            model, name, output_dir=output_dir, register_workspace=True, folder=folder
        )

        # 6. Export Image
        image_path = None
        if export_image:
            img_dir = Path(cfg.export.output_dir).resolve()
            img_dir.mkdir(parents=True, exist_ok=True)
            image_path = str(img_dir / f"{name}.png")
            ImageExporter.export(diagram, image_path, auto_crop=auto_crop, margin=cfg.export.margin)

        return {
            "diagram_name": name,
            "model_path": model_path,
            "image_path": image_path,
            "workspace_path": client.workspace_mgr.workspace_path,
        }

    finally:
        if close_after_build:
            client.close_model(model, save_changes=False)
        if own_client:
            client.close_all_safely(save_changes=False)


def build_usecase_diagram(
    name: str,
    actors: List[Union[str, Dict[str, Any]]],
    usecases: List[Union[str, Dict[str, Any]]],
    links: Optional[List[Tuple[str, str]]] = None,
    client: Optional[PowerDesignerClient] = None,
    folder: Optional[str] = None,
    output_dir: Optional[str] = None,
    export_image: bool = True,
    auto_crop: bool = True,
    close_after_build: bool = True,
) -> Dict[str, Any]:
    """
    Declarative one-step builder for Use Case Diagrams with canonical 3-column layout.
    """
    cfg = get_config()
    own_client = False
    if client is None:
        client = PowerDesignerClient(visible=cfg.com.visible)
        own_client = True

    try:
        model, diagram = client.create_dedicated_diagram(name, diagram_type="usecase")
        builder = UseCaseDiagramBuilder(diagram)

        # 1. Actors
        for act in actors:
            if isinstance(act, str):
                builder.add_actor(act)
            elif isinstance(act, dict):
                a_name = act.get("name", "Actor")
                code = act.get("code", "")
                is_sec = act.get("is_secondary", False)
                builder.add_actor(a_name, code=code, is_secondary=is_sec)

        # 2. Use Cases
        for uc in usecases:
            if isinstance(uc, str):
                builder.add_use_case(uc)
            elif isinstance(uc, dict):
                u_name = uc.get("name", "UseCase")
                code = uc.get("code", "")
                col = uc.get("column", 2)
                builder.add_use_case(u_name, code=code, column=col)

        # 3. Links
        if links:
            for src, tgt in links:
                builder.connect(src, tgt)

        # 4. Layout
        builder.layout_three_column()

        # 5. Save & Register Workspace
        model_path = client.save_diagram_as_file(
            model, name, output_dir=output_dir, register_workspace=True, folder=folder
        )

        # 6. Export Image
        image_path = None
        if export_image:
            img_dir = Path(cfg.export.output_dir).resolve()
            img_dir.mkdir(parents=True, exist_ok=True)
            image_path = str(img_dir / f"{name}.png")
            ImageExporter.export(diagram, image_path, auto_crop=auto_crop, margin=cfg.export.margin)

        return {
            "diagram_name": name,
            "model_path": model_path,
            "image_path": image_path,
            "workspace_path": client.workspace_mgr.workspace_path,
        }

    finally:
        if close_after_build:
            client.close_model(model, save_changes=False)
        if own_client:
            client.close_all_safely(save_changes=False)


def build_pdm_diagram(
    name: str,
    tables: List[Dict[str, Any]],
    references: Optional[List[Dict[str, Any]]] = None,
    dbms: str = "PostgreSQL 15",
    client: Optional[PowerDesignerClient] = None,
    folder: Optional[str] = None,
    output_dir: Optional[str] = None,
    export_image: bool = True,
    auto_crop: bool = True,
    close_after_build: bool = True,
) -> Dict[str, Any]:
    """
    Declarative one-step builder for Physical Data Models (PDM).
    """
    cfg = get_config()
    own_client = False
    if client is None:
        client = PowerDesignerClient(visible=cfg.com.visible)
        own_client = True

    try:
        model, diagram = client.create_dedicated_diagram(name, diagram_type="pdm", language_or_dbms=dbms)
        builder = PdmBuilder(model, diagram=diagram)

        # 1. Tables
        for tbl in tables:
            builder.add_table(
                code=tbl.get("code", ""),
                name=tbl.get("name", ""),
                columns=tbl.get("columns", []),
            )

        # 2. References (Foreign Keys)
        if references:
            for ref in references:
                builder.add_reference(
                    parent_table=ref.get("parent_table", ""),
                    child_table=ref.get("child_table", ""),
                    parent_col=ref.get("parent_col", ""),
                    child_col=ref.get("child_col", ""),
                    name=ref.get("name", ""),
                    cardinality=ref.get("cardinality", "1..*"),
                )

        # 3. Save & Register Workspace
        model_path = client.save_diagram_as_file(
            model, name, output_dir=output_dir, register_workspace=True, folder=folder
        )

        # 4. Export Image
        image_path = None
        if export_image:
            img_dir = Path(cfg.export.output_dir).resolve()
            img_dir.mkdir(parents=True, exist_ok=True)
            image_path = str(img_dir / f"{name}.png")
            ImageExporter.export(diagram, image_path, auto_crop=auto_crop, margin=cfg.export.margin)

        return {
            "diagram_name": name,
            "model_path": model_path,
            "image_path": image_path,
            "workspace_path": client.workspace_mgr.workspace_path,
        }

    finally:
        if close_after_build:
            client.close_model(model, save_changes=False)
        if own_client:
            client.close_all_safely(save_changes=False)
