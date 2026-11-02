"""
Unit tests for Declarative Diagram Pipeline (build_sequence_diagram, build_usecase_diagram, build_pdm_diagram).
"""

import unittest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from pd_com_edit.pipeline import (
    build_sequence_diagram,
    build_usecase_diagram,
    build_pdm_diagram,
)
from pd_com_edit.config import PDConfig, JitterConfig, set_config


class TestDeclarativePipeline(unittest.TestCase):
    def setUp(self):
        set_config(PDConfig(
            jitter=JitterConfig(enabled=False),
            file_naming={"output_dir": "./tmp_models", "prefix": "Test_"},
            workspace={"auto_create": True, "auto_register": False}
        ))

    @patch("pd_com_edit.pipeline.ImageExporter.export")
    def test_build_sequence_diagram(self, mock_export):
        mock_export.return_value = True

        # Create mock client & diagram
        mock_client = MagicMock()
        mock_model = MagicMock()
        mock_diagram = MagicMock()
        mock_diagram.Model = mock_model
        mock_client.create_dedicated_diagram.return_value = (mock_model, mock_diagram)
        mock_client.save_diagram_as_file.return_value = "tmp_models/Test_Seq.oom"
        mock_client.workspace_mgr.workspace_path = "tmp_models/ProjectWorkspace.sws"

        res = build_sequence_diagram(
            name="Seq",
            lifelines=[{"name": "Client", "is_actor": True}, "Server"],
            messages=[
                {"sender": "Client", "receiver": "Server", "label": "req()"},
                {"sender": "Server", "receiver": "Client", "label": "resp()", "is_return": True},
            ],
            client=mock_client,
            export_image=True,
            close_after_build=True,
        )

        self.assertEqual(res["diagram_name"], "Seq")
        self.assertEqual(res["model_path"], "tmp_models/Test_Seq.oom")
        mock_client.save_diagram_as_file.assert_called_once()
        mock_client.close_model.assert_called_once()
        mock_export.assert_called_once()

    @patch("pd_com_edit.pipeline.ImageExporter.export")
    def test_build_usecase_diagram(self, mock_export):
        mock_export.return_value = True

        mock_client = MagicMock()
        mock_model = MagicMock()
        mock_diagram = MagicMock()
        mock_diagram.Model = mock_model
        mock_client.create_dedicated_diagram.return_value = (mock_model, mock_diagram)
        mock_client.save_diagram_as_file.return_value = "tmp_models/Test_UC.oom"
        mock_client.workspace_mgr.workspace_path = "tmp_models/ProjectWorkspace.sws"

        res = build_usecase_diagram(
            name="UC",
            actors=["User", {"name": "Admin", "is_secondary": True}],
            usecases=["Login", "Manage"],
            links=[("User", "Login"), ("Admin", "Manage")],
            client=mock_client,
            export_image=True,
            close_after_build=True,
        )

        self.assertEqual(res["diagram_name"], "UC")
        self.assertEqual(res["model_path"], "tmp_models/Test_UC.oom")
        mock_client.save_diagram_as_file.assert_called_once()
        mock_client.close_model.assert_called_once()

    @patch("pd_com_edit.pipeline.ImageExporter.export")
    def test_build_pdm_diagram(self, mock_export):
        mock_export.return_value = True

        mock_client = MagicMock()
        mock_model = MagicMock()
        mock_diagram = MagicMock()
        mock_model.PhysicalDiagrams.Count = 1
        mock_model.PhysicalDiagrams.Item.return_value = mock_diagram
        mock_client.create_dedicated_diagram.return_value = (mock_model, mock_diagram)
        mock_client.save_diagram_as_file.return_value = "tmp_models/Test_PDM.pdm"
        mock_client.workspace_mgr.workspace_path = "tmp_models/ProjectWorkspace.sws"

        res = build_pdm_diagram(
            name="PDM",
            tables=[
                {
                    "code": "users",
                    "name": "Users",
                    "columns": [{"code": "id", "pk": True}],
                }
            ],
            client=mock_client,
            export_image=True,
            close_after_build=True,
        )

        self.assertEqual(res["diagram_name"], "PDM")
        self.assertEqual(res["model_path"], "tmp_models/Test_PDM.pdm")
        mock_client.save_diagram_as_file.assert_called_once()
        mock_client.close_model.assert_called_once()


if __name__ == "__main__":
    unittest.main()
