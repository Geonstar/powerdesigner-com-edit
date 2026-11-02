"""
PowerDesigner COM Edit (pd_com_edit)
A comprehensive automation and collision-free modeling framework for SAP PowerDesigner.
"""

__version__ = "1.1.0"
__author__ = "Ext Culith (NekoCCN)"

from .client import PowerDesignerClient, rgb, ensure_dynamic, attach_link_symbol
from .collision import CollisionDetector, LayoutAuditor, BoundingBox, CollisionRecord, AuditReport
from .config import (
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
)
from .workspace import WorkspaceManager
from .pipeline import build_sequence_diagram, build_usecase_diagram, build_pdm_diagram
from .sequence import SequenceDiagramBuilder
from .usecase import UseCaseDiagramBuilder
from .class_diagram import ClassDiagramBuilder
from .communication import CommunicationDiagramBuilder
from .activity import ActivityDiagramBuilder
from .statechart import StatechartDiagramBuilder
from .component import ComponentDiagramBuilder
from .deployment import DeploymentDiagramBuilder
from .pdm import PdmBuilder
from .export import ImageExporter

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
