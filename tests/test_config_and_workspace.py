"""
Unit tests for PDConfig, Jitter, WorkspaceManager, and Independent File Naming.
"""

import os
import json
import tempfile
import unittest
from pathlib import Path

from pd_com_edit.config import (
    PDConfig,
    JitterConfig,
    WorkspaceConfig,
    FileNamingConfig,
    apply_jitter,
    load_config,
    set_config,
    get_config,
)
from pd_com_edit.workspace import WorkspaceManager


class TestConfigAndJitter(unittest.TestCase):
    def test_default_config(self):
        cfg = PDConfig()
        self.assertFalse(cfg.jitter.enabled)
        self.assertTrue(cfg.workspace.auto_detect)
        self.assertTrue(cfg.workspace.auto_register)
        self.assertTrue(cfg.file_naming.separate_files)

    def test_jitter_disabled(self):
        cfg = JitterConfig(enabled=False)
        x, y = apply_jitter(1000, 2000, cfg)
        self.assertEqual(x, 1000)
        self.assertEqual(y, 2000)

    def test_jitter_enabled_range(self):
        cfg = JitterConfig(enabled=True, range_x=(-200, 200), range_y=(-100, 100))
        for _ in range(20):
            x, y = apply_jitter(5000, 8000, cfg)
            self.assertTrue(4800 <= x <= 5200)
            self.assertTrue(7900 <= y <= 8100)

    def test_config_save_and_load_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_file = Path(tmpdir) / "pd_config.json"
            cfg = PDConfig(
                jitter=JitterConfig(enabled=True, range_x=(-150, 150)),
                file_naming=FileNamingConfig(prefix="图_", suffix="_测试"),
            )
            cfg.save(str(cfg_file))

            loaded = load_config(search_paths=[cfg_file])
            self.assertTrue(loaded.jitter.enabled)
            self.assertEqual(loaded.jitter.range_x, (-150, 150))
            self.assertEqual(loaded.file_naming.prefix, "图_")
            self.assertEqual(loaded.file_naming.suffix, "_测试")


class TestWorkspaceManager(unittest.TestCase):
    def test_create_and_register_workspace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ws_path = Path(tmpdir) / "TestProject.sws"
            mgr = WorkspaceManager(workspace_path=str(ws_path))

            # Create fresh workspace
            mgr.find_or_create_workspace(target_dir=tmpdir, name="TestProject")
            self.assertTrue(ws_path.exists())

            # Fake model files
            oom_file = Path(tmpdir) / "图1_用例图.oom"
            oom_file.write_text("dummy oom content", encoding="utf-8")

            pdm_file = Path(tmpdir) / "图2_数据库模型.pdm"
            pdm_file.write_text("dummy pdm content", encoding="utf-8")

            # Register OOM
            res1 = mgr.register_model(str(oom_file), model_name="图1_用例图", model_type="OOM")
            self.assertTrue(res1)

            # Register PDM
            res2 = mgr.register_model(str(pdm_file), model_name="图2_数据库模型", model_type="PDM")
            self.assertTrue(res2)

            # Check listed models
            models = mgr.list_models()
            self.assertEqual(len(models), 2)
            names = [m["name"] for m in models]
            self.assertIn("图1_用例图", names)
            self.assertIn("图2_数据库模型", names)

            # Verify idempotency (re-registering should not duplicate)
            res3 = mgr.register_model(str(oom_file), model_name="图1_用例图_更新", model_type="OOM")
            self.assertTrue(res3)
            models_after = mgr.list_models()
            self.assertEqual(len(models_after), 2)
            updated_names = [m["name"] for m in models_after]
            self.assertIn("图1_用例图_更新", updated_names)

    def test_workspace_folder_and_scan_sync(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ws_path = Path(tmpdir) / "TestGrouped.sws"
            mgr = WorkspaceManager(workspace_path=str(ws_path))
            mgr.create_workspace(str(ws_path), name="TestGrouped")

            # Create multiple models
            m1 = Path(tmpdir) / "U1_时序图.oom"
            m1.write_text("dummy", encoding="utf-8")
            m2 = Path(tmpdir) / "U2_时序图.oom"
            m2.write_text("dummy", encoding="utf-8")

            # Register with folder
            mgr.register_model(str(m1), model_name="U1_时序图", folder="用户模块")
            mgr.register_model(str(m2), model_name="U2_时序图", folder="订单模块")

            models = mgr.list_models()
            self.assertEqual(len(models), 2)
            folders = {m["name"]: m["folder"] for m in models}
            self.assertEqual(folders["U1_时序图"], "用户模块")
            self.assertEqual(folders["U2_时序图"], "订单模块")

            # Create another model file and test scan_and_sync
            m3 = Path(tmpdir) / "U3_数据库.pdm"
            m3.write_text("dummy", encoding="utf-8")

            synced = mgr.scan_and_sync(directory=tmpdir)
            self.assertIn(str(m3.resolve()), synced)

            all_models = mgr.list_models()
            self.assertEqual(len(all_models), 3)


if __name__ == "__main__":
    unittest.main()
