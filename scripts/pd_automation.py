#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PowerDesigner COM Automation & Collision Resolution Engine (scripts/pd_automation.py)
Unified convenience entrypoint re-exporting the complete pd_com_edit engine:
- PowerDesigner COM Client & Process Safety
- Centralized Configuration (PDConfig, Jitter, Workspace, FileNaming)
- Workspace Management (.sws / .pbw auto-detection & registration)
- Independent Model File Generation (1 diagram = 1 dedicated file)
- UML Builders: Sequence, UseCase, Class, Communication, Activity, Statechart, Component, Deployment
- Relational Schema Builder: PdmBuilder
- Geometric Collision Detection & High-Res Cropping
"""

import sys
import os
from pathlib import Path

# Ensure package root is in path if script is executed or imported directly
_pkg_root = str(Path(__file__).resolve().parent.parent)
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

from pd_com_edit import (
    PowerDesignerClient,
    SequenceDiagramBuilder,
    UseCaseDiagramBuilder,
    ClassDiagramBuilder,
    CommunicationDiagramBuilder,
    ActivityDiagramBuilder,
    StatechartDiagramBuilder,
    ComponentDiagramBuilder,
    DeploymentDiagramBuilder,
    PdmBuilder,
    CollisionDetector,
    LayoutAuditor,
    BoundingBox,
    CollisionRecord,
    AuditReport,
    ImageExporter,
    rgb,
    ensure_dynamic,
    attach_link_symbol,
    PDConfig,
    JitterConfig,
    WorkspaceConfig,
    FileNamingConfig,
    LayoutConfig,
    ExportConfig,
    COMConfig,
    get_config,
    set_config,
    load_config,
    apply_jitter,
    WorkspaceManager,
    build_sequence_diagram,
    build_usecase_diagram,
    build_pdm_diagram,
)

__all__ = [
    "PowerDesignerClient",
    "SequenceDiagramBuilder",
    "UseCaseDiagramBuilder",
    "ClassDiagramBuilder",
    "CommunicationDiagramBuilder",
    "ActivityDiagramBuilder",
    "StatechartDiagramBuilder",
    "ComponentDiagramBuilder",
    "DeploymentDiagramBuilder",
    "PdmBuilder",
    "CollisionDetector",
    "LayoutAuditor",
    "BoundingBox",
    "CollisionRecord",
    "AuditReport",
    "ImageExporter",
    "rgb",
    "ensure_dynamic",
    "attach_link_symbol",
    "PDConfig",
    "JitterConfig",
    "WorkspaceConfig",
    "FileNamingConfig",
    "LayoutConfig",
    "ExportConfig",
    "COMConfig",
    "get_config",
    "set_config",
    "load_config",
    "apply_jitter",
    "WorkspaceManager",
    "build_sequence_diagram",
    "build_usecase_diagram",
    "build_pdm_diagram",
]
