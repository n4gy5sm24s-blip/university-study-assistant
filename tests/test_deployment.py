from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from app.database import database_path
from app.model_config import model_configuration_write_enabled


class RailwayDeploymentTests(unittest.TestCase):
    def test_database_uses_railway_volume(self) -> None:
        with patch.dict(
            os.environ,
            {"RAILWAY_VOLUME_MOUNT_PATH": "/app/data"},
            clear=True,
        ):
            self.assertEqual(database_path(), Path("/app/data/study_assistant.db"))

    def test_explicit_database_path_has_priority(self) -> None:
        with patch.dict(
            os.environ,
            {
                "STUDY_ASSISTANT_DB": "/custom/app.db",
                "RAILWAY_VOLUME_MOUNT_PATH": "/app/data",
            },
            clear=True,
        ):
            self.assertEqual(database_path(), Path("/custom/app.db"))

    def test_railway_disables_model_config_write_by_default(self) -> None:
        with patch.dict(os.environ, {"RAILWAY_ENVIRONMENT": "production"}, clear=True):
            self.assertFalse(model_configuration_write_enabled())

    def test_explicit_setting_controls_model_config_write(self) -> None:
        with patch.dict(
            os.environ,
            {"RAILWAY_ENVIRONMENT": "production", "ALLOW_MODEL_CONFIG_WRITE": "true"},
            clear=True,
        ):
            self.assertTrue(model_configuration_write_enabled())


if __name__ == "__main__":
    unittest.main()
