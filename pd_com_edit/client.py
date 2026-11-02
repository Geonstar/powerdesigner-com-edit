#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PowerDesigner COM Application Client & Lifecycle Management
Supports:
- Auto-connection to PowerDesigner 16.5+ COM Dispatch
- Dedicated model generation per diagram (1 diagram = 1 distinct file)
- PowerDesigner Workspace (.sws / .pbw) auto-detection and registration
- Safe model/workspace closing and error recovery
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from typing import Optional, Any, Tuple

try:
    import win32com.client
    import pythoncom
except ImportError:
    win32com = None
    pythoncom = None

from .config import get_config, PDConfig
from .workspace import WorkspaceManager

# Model Type GUIDs & Integer Identifiers in PowerDesigner
CLS_OOM = "{4BA9FBC0-D824-11D1-A1DF-0020AF12A261}"  # Object-Oriented Model
CLS_PDM = "{CDE44E21-3017-11D2-8A2D-00609756FE6C}"  # Physical Data Model
CLS_CDM = "{9C84FDF4-9E0C-11D1-A1DE-0020AF12A261}"  # Conceptual Data Model
CLS_BPM = "{8F7D0DF1-7C65-11D3-B437-0060976527C0}"  # Business Process Model

# Native Model Kind Constants (for CreateModel integer call)
MODEL_OOM = 403775584
MODEL_CDM = 509178224
MODEL_PDM = -840675807

# Native Object Kind Constants in PowerDesigner OOM
KIND_CLASS = 403775587
KIND_INTERFACE = 403775588
KIND_ATTRIBUTE = 403775589
KIND_OPERATION = 403775590
KIND_GENERALIZATION = 403775592
KIND_DEPENDENCY = 403775593
KIND_CLASS_ASSOC = 403775594
KIND_ACTOR = 403775745
KIND_USECASE = 403775746
KIND_USECASE_ASSOC = 403775603
KIND_INTERACTION_FRAGMENT = -168517650


def rgb(r: int, g: int, b: int) -> int:
    """Convert RGB (0-255) to Windows COLORREF integer."""
    return int(r) + (int(g) << 8) + (int(b) << 16)


def ensure_dynamic(obj):
    """
    Ensure a COM object uses late-bound dynamic dispatch.
    This prevents early-binding BaseObject wrapper issues where derived properties
    (like Name, Position, Object1, etc.) are stripped by makepy/gencache.
    """
    if hasattr(obj, "_oleobj_") and win32com is not None:
        if type(obj).__name__ == "MagicMock" or type(getattr(obj, "_oleobj_", None)).__name__ == "MagicMock":
            return obj
        try:
            return win32com.client.dynamic.Dispatch(obj._oleobj_)
        except Exception:
            pass
    return obj


def attach_link_symbol(diagram, link_obj):
    """
    Safely attach a link/connector symbol (Association, Generalization, Dependency, Reference)
    to a PowerDesigner diagram.

    In PowerDesigner COM, 2D symbols use `AttachObject` while 1D line connectors MUST use
    `AttachLinkObject`. Under pywin32, calling AttachLinkObject directly on dynamic dispatch
    can encounter COM argument type coercion issues; invoking via IDispatch safely resolves this.
    """
    if hasattr(diagram, "_oleobj_") and pythoncom is not None:
        try:
            dispid = diagram._oleobj_.GetIDsOfNames("AttachLinkObject")
            ole_link = link_obj._oleobj_ if hasattr(link_obj, "_oleobj_") else link_obj
            res = diagram._oleobj_.Invoke(dispid, 0, pythoncom.DISPATCH_METHOD, True, ole_link)
            if win32com:
                return win32com.client.dynamic.Dispatch(res)
            return res
        except Exception:
            pass

    if hasattr(diagram, "AttachLinkObject"):
        try:
            return diagram.AttachLinkObject(link_obj)
        except Exception:
            pass

    if hasattr(diagram, "AttachObject"):
        try:
            return diagram.AttachObject(link_obj)
        except Exception:
            pass

    return None


def get_symbol_size(sym: Any) -> Tuple[int, int]:
    """Safely retrieves (width, height) of a PowerDesigner symbol."""
    try:
        sz = getattr(sym, "Size", None)
        if sz is not None:
            w = getattr(sz, "X", None)
            if w is None:
                w = getattr(sz, "Width", 0)
            h = getattr(sz, "Y", None)
            if h is None:
                h = getattr(sz, "Height", 0)
            return int(w), int(h)
    except Exception:
        pass
    return (0, 0)


def set_symbol_size(sym: Any, width: int, height: int):
    """Safely sets symbol dimensions (width, height) handling both .X/.Y and .Width/.Height."""
    try:
        sz = getattr(sym, "Size", None)
        if sz is not None:
            try:
                sz.X = width
                sz.Y = height
            except Exception:
                try:
                    sz.Width = width
                    sz.Height = height
                except Exception:
                    pass
    except Exception:
        pass


class PowerDesignerClient:
    """Manages connection, model lifecycle, workspace synchronization, and process safety for PowerDesigner."""

    def __init__(
        self,
        visible: Optional[bool] = None,
        timeout_sec: Optional[int] = None,
        workspace_path: Optional[str] = None
    ):
        if win32com is None:
            raise RuntimeError("pywin32 is required. Install via: pip install pywin32")
        cfg = get_config()
        self.visible = visible if visible is not None else cfg.com.visible
        self.timeout_sec = timeout_sec if timeout_sec is not None else cfg.com.timeout_sec
        self.app = None
        self._connect()
        self.workspace_mgr = WorkspaceManager(workspace_path=workspace_path, client=self)

    def _connect(self):
        start_time = time.time()
        last_error = None
        # Prioritize version-specific ProgIDs for Windows 10/11 compatibility
        prog_ids = [
            "PowerDesigner.Application.16.5",
            "PowerDesigner.Application",
            "PowerDesigner.Application.16"
        ]
        while time.time() - start_time < self.timeout_sec:
            for pid in prog_ids:
                try:
                    self.app = win32com.client.Dispatch(pid)
                    try:
                        self.app.Visible = self.visible
                    except Exception:
                        pass
                    return
                except Exception as e:
                    last_error = e
            time.sleep(1)
        raise RuntimeError(f"Failed to connect to PowerDesigner.Application: {last_error}")

    def start(self, visible: Optional[bool] = None):
        """Start or re-verify connection to PowerDesigner Application."""
        if visible is not None:
            self.visible = visible
        if self.app is None:
            self._connect()
        elif visible is not None:
            try:
                self.app.Visible = visible
            except Exception:
                pass

    def create_oom_model(self, name: str = "NewOOM", language: str = "Java"):
        """Create a new Object-Oriented Model (OOM)."""
        opts = f"|Language={language}|"
        try:
            model = self.app.CreateModel(MODEL_OOM, opts, 0)
        except Exception:
            model = self.app.CreateModel(CLS_OOM, opts)

        if hasattr(model, "_oleobj_") and win32com:
            try:
                model = win32com.client.dynamic.Dispatch(model._oleobj_)
            except Exception:
                pass

        if name:
            try:
                model.SetName(name)
            except Exception:
                try:
                    model.Name = name
                except Exception:
                    pass
        return model

    create_oom = create_oom_model

    def create_pdm_model(self, name: str = "NewPDM", dbms: str = "PostgreSQL 9.x"):
        """Create a new Physical Data Model (PDM) with DBMS fallback."""
        candidates = [dbms] if dbms else []
        dbms_lower = (dbms or "").lower()
        if "postgres" in dbms_lower and "9.x" not in dbms_lower:
            candidates.append("PostgreSQL 9.x")
        elif "mysql" in dbms_lower and "5.0" not in dbms_lower:
            candidates.append("MySQL 5.0")
        elif "oracle" in dbms_lower:
            candidates.append("Oracle 11g")
        candidates.append("")  # Fallback to PowerDesigner system default DBMS

        model = None
        last_err = None
        for cand in candidates:
            opts = f"|DBMS={cand}|" if cand else ""
            try:
                model = self.app.CreateModel(MODEL_PDM, opts, 0)
                break
            except Exception as e:
                last_err = e
                try:
                    model = self.app.CreateModel(MODEL_PDM, opts)
                    break
                except Exception as e2:
                    last_err = e2
                    continue

        if model is None:
            raise RuntimeError(f"Failed to create PDM with DBMS '{dbms}': {last_err}")
        if hasattr(model, "_oleobj_") and win32com:
            try:
                model = win32com.client.dynamic.Dispatch(model._oleobj_)
            except Exception:
                pass
        if name:
            try:
                model.SetName(name)
            except Exception:
                try:
                    model.Name = name
                except Exception:
                    pass
        return model

    create_pdm = create_pdm_model

    def create_cdm_model(self, name: str = "NewCDM"):
        """Create a new Conceptual Data Model (CDM)."""
        model = self.app.CreateModel(CLS_CDM, "")
        if name:
            model.SetName(name)
        return model

    create_cdm = create_cdm_model

    def create_diagram_model(
        self,
        diagram_name: str,
        model_type: str = "OOM",
        language_or_dbms: str = "Java"
    ) -> Any:
        """
        Create a dedicated, cleanly named Model for a single diagram.
        Enforces best practice: each diagram is saved as an independent model file.
        """
        cfg = get_config().file_naming
        formatted_name = f"{cfg.prefix}{diagram_name}{cfg.suffix}"

        if model_type.upper() == "PDM":
            return self.create_pdm_model(name=formatted_name, dbms=language_or_dbms)
        elif model_type.upper() == "CDM":
            return self.create_cdm_model(name=formatted_name)
        else:
            return self.create_oom_model(name=formatted_name, language=language_or_dbms)

    def open_model(self, path: str):
        """Open an existing .oom, .cdm, or .pdm file."""
        if not os.path.isabs(path):
            path = os.path.abspath(path)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Model file not found: {path}")
        m = self.app.OpenModel(path)
        if hasattr(m, "_oleobj_") and win32com:
            try:
                m = win32com.client.dynamic.Dispatch(m._oleobj_)
            except Exception:
                pass
        return m

    def save_model(
        self,
        model: Any,
        path: str,
        register_workspace: bool = True,
        folder: Optional[str] = None
    ):
        """
        Save a model to specified target file path.
        Automatically registers the model into the active or local PowerDesigner Workspace (.sws)
        if register_workspace is True and workspace.auto_register is enabled.
        """
        if not os.path.isabs(path):
            path = os.path.abspath(path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            model.SaveAs(path)
        except Exception:
            try:
                model.Save(path)
            except Exception:
                model.Save()

        # Workspace auto-registration
        if register_workspace and get_config().workspace.auto_register:
            try:
                m_type = "PDM" if path.lower().endswith(".pdm") else ("CDM" if path.lower().endswith(".cdm") else "OOM")
                m_name = getattr(model, "Name", Path(path).stem)
                self.workspace_mgr.register_model(path, model_name=m_name, model_type=m_type, folder=folder)
            except Exception:
                pass

    def save_diagram_as_file(
        self,
        model: Any,
        diagram_name: str,
        output_dir: Optional[str] = None,
        register_workspace: bool = True,
        folder: Optional[str] = None
    ) -> str:
        """
        Save a model containing a diagram to an independent, clearly named file.
        Uses configured output directory, prefix, and suffix.
        Returns the saved file path.
        """
        cfg = get_config().file_naming
        out_dir = Path(output_dir or cfg.output_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)

        ext = cfg.oom_extension
        if hasattr(model, "ClassName") and "Physical" in str(model.ClassName):
            ext = cfg.pdm_extension

        filename = f"{cfg.prefix}{diagram_name}{cfg.suffix}{ext}"
        target_path = str(out_dir / filename)

        self.save_model(model, target_path, register_workspace=register_workspace, folder=folder)
        return target_path

    def create_dedicated_diagram(
        self,
        diagram_name: str,
        diagram_type: str = "sequence",
        language_or_dbms: str = "Java"
    ) -> Tuple[Any, Any]:
        """
        Creates a dedicated model and diagram, purging any auto-generated empty template diagrams.
        Enforces 1 Diagram = 1 Clean Independent Model.
        Returns: (model, diagram)
        """
        dtype_lower = diagram_type.lower()
        is_pdm = "pdm" in dtype_lower or "physical" in dtype_lower
        model_type = "PDM" if is_pdm else "OOM"

        model = self.create_diagram_model(diagram_name, model_type=model_type, language_or_dbms=language_or_dbms)

        target_diagram = None
        type_to_coll = {
            "sequence": "SequenceDiagrams",
            "usecase": "UseCaseDiagrams",
            "class": "ClassDiagrams",
            "communication": "CommunicationDiagrams",
            "collaboration": "CollaborationDiagrams",
            "activity": "ActivityDiagrams",
            "statechart": "StatechartDiagrams",
            "state": "StatechartDiagrams",
            "component": "ComponentDiagrams",
            "deployment": "DeploymentDiagrams",
            "pdm": "PhysicalDiagrams",
            "physical": "PhysicalDiagrams",
        }
        coll_name = type_to_coll.get(dtype_lower, "SequenceDiagrams" if not is_pdm else "PhysicalDiagrams")
        coll = getattr(model, coll_name, None)

        if coll is not None:
            if coll.Count > 0 and getattr(coll.Item(0), "Symbols", None) is not None and coll.Item(0).Symbols.Count <= 1:
                target_diagram = ensure_dynamic(coll.Item(0))
                try:
                    target_diagram.SetName(diagram_name)
                except Exception:
                    try:
                        target_diagram.Name = diagram_name
                    except Exception:
                        pass
            else:
                target_diagram = ensure_dynamic(coll.CreateNew())
                try:
                    target_diagram.SetName(diagram_name)
                except Exception:
                    target_diagram.Name = diagram_name

        # Purge any lingering empty template diagrams in other diagram collections
        all_colls = [
            "ClassDiagrams", "SequenceDiagrams", "UseCaseDiagrams",
            "CommunicationDiagrams", "CollaborationDiagrams", "ActivityDiagrams",
            "StatechartDiagrams", "ComponentDiagrams", "DeploymentDiagrams",
            "PhysicalDiagrams"
        ]
        for c_name in all_colls:
            c = getattr(model, c_name, None)
            if c and c.Count > 0:
                for i in range(c.Count - 1, -1, -1):
                    try:
                        d = c.Item(i)
                        if d is not target_diagram:
                            name = getattr(d, "Name", "")
                            sym_count = getattr(d, "Symbols", None).Count if hasattr(d, "Symbols") else 0
                            if sym_count <= 1 and (name.endswith("_1") or name.startswith("Diagram_")):
                                d.Delete()
                    except Exception:
                        pass

        return model, target_diagram

    def close_model(self, model, save_changes: bool = False):
        """Close an individual model safely without prompting."""
        try:
            m = ensure_dynamic(model)
            if save_changes:
                m.Save()
            else:
                try:
                    m.Modified = False
                except Exception:
                    pass
            try:
                m.Close(False)
            except Exception:
                m.Close()
        except Exception:
            pass

    def open_workspace(self, path: str):
        """Target a PowerDesigner workspace (.sws / .pbw) file safely."""
        if not os.path.isabs(path):
            path = os.path.abspath(path)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Workspace file not found: {path}")
        self.workspace_mgr.workspace_path = path
        return self.workspace_mgr

    def close_all_safely(self, save_changes: bool = False):
        """Safely close open models and release the COM server handle."""
        try:
            if self.app:
                while self.app.Models.Count > 0:
                    m = ensure_dynamic(self.app.Models.Item(0))
                    if save_changes:
                        m.Save()
                    else:
                        try:
                            m.Modified = False
                        except Exception:
                            pass
                    try:
                        m.Close(False)
                    except Exception:
                        m.Close()
        except Exception:
            pass
        self.app = None

    @staticmethod
    def kill_lingering_processes():
        """Force-kill any hung or lingering pdshell16.exe processes."""
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/IM", "pdshell16.exe"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
