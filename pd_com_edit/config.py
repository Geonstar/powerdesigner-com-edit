#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Centralized Configuration Manager for PowerDesigner COM Edit
Provides configurable settings for:
- Random layout jitter / coordinate perturbation
- File naming & independent model saving
- PowerDesigner Workspace (.sws / .pbw) auto-detection & registration
- Diagram layout dimensions & spacings
- Image export options
"""

import os
import json
import random
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

try:
    import yaml
except ImportError:
    yaml = None


@dataclass
class JitterConfig:
    """Random offset / coordinate perturbation settings."""
    enabled: bool = False
    range_x: Tuple[int, int] = (-400, 400)   # PowerDesigner coordinate logical units (~100 = 1mm)
    range_y: Tuple[int, int] = (-300, 300)
    seed: Optional[int] = None              # Set integer for deterministic reproducible jitter

    def get_offset(self) -> Tuple[int, int]:
        """Compute a randomized (dx, dy) within the configured ranges."""
        if not self.enabled:
            return 0, 0
        if self.seed is not None:
            # Deterministic based on state or seed
            pass
        dx = random.randint(self.range_x[0], self.range_x[1])
        dy = random.randint(self.range_y[0], self.range_y[1])
        return dx, dy


@dataclass
class WorkspaceConfig:
    """Settings for PowerDesigner Workspace (.sws / .pbw) management."""
    auto_detect: bool = True               # Check COM ActiveWorkspace and local .sws files
    auto_register: bool = True            # Automatically register saved models into workspace
    auto_create: bool = True              # Create a new .sws if no workspace is found
    workspace_name: str = "ProjectWorkspace"
    workspace_path: Optional[str] = None   # Explicit path to .sws/.pbw file, or auto-discovered
    save_on_model_add: bool = True        # Commit workspace updates immediately to disk


@dataclass
class FileNamingConfig:
    """Settings for saving each diagram into independent, clearly named model files."""
    separate_files: bool = True           # Enforce 1 diagram = 1 dedicated model file
    output_dir: str = "./output_models"    # Default directory for generated model files
    oom_extension: str = ".oom"
    pdm_extension: str = ".pdm"
    prefix: str = ""                      # e.g., "图_" or "Arch_"
    suffix: str = ""                      # e.g., "_工程"


@dataclass
class LayoutConfig:
    """Default layout spacing, columns, and step sizes."""
    # Sequence diagram
    seq_start_x: int = 1500
    seq_spacing_x: int = 2500
    seq_start_y: int = -1500
    seq_step_y: int = -500
    seq_activation_tier_offset: int = 120

    # Use Case diagram 4-column canonical layout
    uc_col1_x: int = -38000
    uc_col2_x: int = -14000
    uc_col3_x: int = 14000
    uc_col4_x: int = 38000
    uc_start_y: int = 28000
    uc_step_y: int = -8000

    # Class diagram
    class_start_x: int = 2000
    class_spacing_x: int = 12000
    class_start_y: int = 16000
    class_spacing_y: int = -8000


@dataclass
class ExportConfig:
    """Image export settings."""
    format: str = "PNG"                   # PNG, JPEG, EMF, BMP
    crop_whitespace: bool = True
    margin: int = 25                      # Margin around cropped diagrams (pixels)
    output_dir: str = "./output_images"


@dataclass
class COMConfig:
    """PowerDesigner COM client connection settings."""
    visible: bool = False
    timeout_sec: int = 15
    preferred_prog_id: str = "PowerDesigner.Application.16.5"


@dataclass
class PDConfig:
    """Root configuration object for powerdesigner-com-edit."""
    jitter: JitterConfig = field(default_factory=JitterConfig)
    workspace: WorkspaceConfig = field(default_factory=WorkspaceConfig)
    file_naming: FileNamingConfig = field(default_factory=FileNamingConfig)
    layout: LayoutConfig = field(default_factory=LayoutConfig)
    export: ExportConfig = field(default_factory=ExportConfig)
    com: COMConfig = field(default_factory=COMConfig)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PDConfig":
        config = cls()
        if "jitter" in data and isinstance(data["jitter"], dict):
            j = data["jitter"]
            config.jitter = JitterConfig(
                enabled=j.get("enabled", False),
                range_x=tuple(j.get("range_x", (-400, 400))),
                range_y=tuple(j.get("range_y", (-300, 300))),
                seed=j.get("seed", None),
            )
            if config.jitter.seed is not None:
                random.seed(config.jitter.seed)

        if "workspace" in data and isinstance(data["workspace"], dict):
            w = data["workspace"]
            config.workspace = WorkspaceConfig(
                auto_detect=w.get("auto_detect", True),
                auto_register=w.get("auto_register", True),
                auto_create=w.get("auto_create", True),
                workspace_name=w.get("workspace_name", "ProjectWorkspace"),
                workspace_path=w.get("workspace_path", None),
                save_on_model_add=w.get("save_on_model_add", True),
            )

        if "file_naming" in data and isinstance(data["file_naming"], dict):
            f = data["file_naming"]
            config.file_naming = FileNamingConfig(
                separate_files=f.get("separate_files", True),
                output_dir=f.get("output_dir", "./output_models"),
                oom_extension=f.get("oom_extension", ".oom"),
                pdm_extension=f.get("pdm_extension", ".pdm"),
                prefix=f.get("prefix", ""),
                suffix=f.get("suffix", ""),
            )

        if "layout" in data and isinstance(data["layout"], dict):
            l = data["layout"]
            config.layout = LayoutConfig(**{k: v for k, v in l.items() if hasattr(config.layout, k)})

        if "export" in data and isinstance(data["export"], dict):
            e = data["export"]
            config.export = ExportConfig(**{k: v for k, v in e.items() if hasattr(config.export, k)})

        if "com" in data and isinstance(data["com"], dict):
            c = data["com"]
            config.com = COMConfig(**{k: v for k, v in c.items() if hasattr(config.com, k)})

        return config

    def save(self, filepath: str) -> None:
        """Save configuration to JSON or YAML file."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = self.to_dict()
        if path.suffix.lower() in (".yaml", ".yml") and yaml is not None:
            with open(path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
        else:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)


# Global configuration instance
_GLOBAL_CONFIG: Optional[PDConfig] = None


def get_config() -> PDConfig:
    """Get or auto-load current global configuration."""
    global _GLOBAL_CONFIG
    if _GLOBAL_CONFIG is None:
        _GLOBAL_CONFIG = load_config()
    return _GLOBAL_CONFIG


def set_config(config: PDConfig) -> None:
    """Explicitly set global configuration."""
    global _GLOBAL_CONFIG
    _GLOBAL_CONFIG = config
    if config.jitter.seed is not None:
        random.seed(config.jitter.seed)


def load_config(search_paths: Optional[list] = None) -> PDConfig:
    """
    Search for configuration file in current directory and parent directories.
    Supports pd_config.yaml, pd_config.yml, and pd_config.json.
    Falls back to default configuration if none found.
    """
    if search_paths is None:
        cwd = Path.cwd().resolve()
        search_paths = [
            cwd / "pd_config.yaml",
            cwd / "pd_config.yml",
            cwd / "pd_config.json",
            cwd.parent / "pd_config.yaml",
            cwd.parent / "pd_config.json",
            Path.home() / ".dsh" / "pd_config.yaml",
            Path.home() / ".dsh" / "pd_config.json",
        ]

    for p in search_paths:
        path = Path(p)
        if path.is_file():
            try:
                if path.suffix.lower() in (".yaml", ".yml") and yaml is not None:
                    with open(path, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                    if isinstance(data, dict):
                        return PDConfig.from_dict(data)
                elif path.suffix.lower() == ".json":
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, dict):
                        return PDConfig.from_dict(data)
            except Exception:
                pass

    return PDConfig()


def apply_jitter(x: int, y: int, jitter_cfg: Optional[JitterConfig] = None) -> Tuple[int, int]:
    """
    Apply random coordinate perturbation to (x, y) if jitter is enabled.
    Returns (x + dx, y + dy).
    """
    cfg = jitter_cfg or get_config().jitter
    if not cfg.enabled:
        return x, y
    dx, dy = cfg.get_offset()
    return x + dx, y + dy
