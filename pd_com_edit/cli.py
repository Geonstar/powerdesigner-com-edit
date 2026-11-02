#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Command-Line Interface for pd_com_edit
"""

import sys
import argparse
from .client import PowerDesignerClient
from .collision import CollisionDetector, LayoutAuditor
from .export import ImageExporter

def main():
    parser = argparse.ArgumentParser(
        prog="pd-edit",
        description="PowerDesigner COM Automation, Collision Auditing & Export CLI"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: audit
    p_audit = subparsers.add_parser("audit", help="Audit model diagrams for overlaps and stray notes")
    p_audit.add_argument("model_path", help="Path to .oom, .pdm, or .cdm file")

    # Subcommand: clean-notes
    p_clean = subparsers.add_parser("clean-notes", help="Strip draft / unapproved annotations from model")
    p_clean.add_argument("model_path", help="Path to .oom, .pdm, or .cdm file")
    p_clean.add_argument("--save", action="store_true", help="Save model changes after cleaning")

    # Subcommand: export
    p_export = subparsers.add_parser("export", help="Batch export all diagrams in model to PNG with auto-crop")
    p_export.add_argument("model_path", help="Path to .oom, .pdm, or .cdm file")
    p_export.add_argument("--out-dir", "-o", default="./exports", help="Output directory for exported images")
    p_export.add_argument("--no-crop", action="store_true", help="Disable PIL white border auto-cropping")

    # Subcommand: init-config
    p_init = subparsers.add_parser("init-config", help="Initialize a default pd_config.json configuration file")
    p_init.add_argument("--path", default="pd_config.json", help="Path to write configuration file")

    # Subcommand: workspace
    p_ws = subparsers.add_parser("workspace", help="Inspect or synchronize PowerDesigner workspace (.sws)")
    p_ws.add_argument("--list", action="store_true", help="List all registered models in workspace")
    p_ws.add_argument("--sync", metavar="DIR", help="Scan directory and synchronize models into workspace")
    p_ws.add_argument("--ws-file", default=None, help="Explicit path to .sws workspace file")

    # Subcommand: kill-pd
    subparsers.add_parser("kill-pd", help="Force-kill any lingering pdshell16.exe processes")

    args = parser.parse_args()

    if args.command == "init-config":
        from .config import PDConfig
        cfg = PDConfig()
        cfg.save(args.path)
        print(f"Created default configuration file: {args.path}")
        return

    if args.command == "workspace":
        from .workspace import WorkspaceManager
        mgr = WorkspaceManager(workspace_path=args.ws_file)
        if args.sync:
            added = mgr.scan_and_sync(args.sync)
            print(f"Workspace ({mgr.workspace_path}): Synced {len(added)} model files from {args.sync}.")
            for a in added:
                print(f"  + {a}")
        if args.list or not args.sync:
            models = mgr.list_models()
            print(f"Workspace ({mgr.workspace_path}): {len(models)} models registered.")
            for idx, m in enumerate(models, 1):
                f_info = f" [Folder: {m['folder']}]" if m.get("folder") else ""
                print(f"  {idx}. {m['name']} ({m['type']}) -> {m['url']}{f_info}")
        return

    if args.command == "kill-pd":
        PowerDesignerClient.kill_lingering_processes()
        print("Killed lingering PowerDesigner processes.")
        return

    client = PowerDesignerClient(visible=False)
    try:
        model = client.open_model(args.model_path)
        print(f"Loaded model: {model.Name}")

        if args.command == "audit":
            diagram_types = ["SequenceDiagrams", "UseCaseDiagrams", "ClassDiagrams", "PhysicalDiagrams", "ConceptualDiagrams"]
            for dtype in diagram_types:
                if hasattr(model, dtype):
                    for diag in getattr(model, dtype):
                        report = LayoutAuditor.audit(diag)
                        print(f"[{report['status']}] {diag.Name}: {report['overlapping_pairs']} overlaps, {report['stray_draft_notes']} draft notes.")
                        for w in report["warnings"]:
                            print(f"  - {w}")

        elif args.command == "clean-notes":
            total_removed = 0
            diagram_types = ["SequenceDiagrams", "UseCaseDiagrams", "ClassDiagrams", "PhysicalDiagrams", "ConceptualDiagrams"]
            for dtype in diagram_types:
                if hasattr(model, dtype):
                    for diag in getattr(model, dtype):
                        total_removed += CollisionDetector.strip_draft_notes(diag)
            print(f"Removed {total_removed} stray draft notes.")
            if args.save:
                model.Save()
                print("Model saved successfully.")

        elif args.command == "export":
            auto_crop = not args.no_crop
            count = ImageExporter.export_all_diagrams(model, args.out_dir, auto_crop=auto_crop)
            print(f"Successfully exported {count} diagrams to {args.out_dir}")

    finally:
        client.close_all_safely(save_changes=False)

if __name__ == "__main__":
    main()
