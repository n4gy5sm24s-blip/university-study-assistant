import os
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from app.model_config import ModelConfigurationError, model_status, save_model_configuration


class ModelConfigurationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).parent / ".tmp" / uuid4().hex
        self.root.mkdir(parents=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def test_status_never_exposes_key(self) -> None:
        with patch.dict(os.environ, {"OPENAI_API_KEY": "secret", "OPENAI_MODEL": "test-model"}, clear=False):
            payload = model_status().to_dict()
        self.assertEqual(payload, {"configured": True, "model": "test-model", "provider": "OpenAI"})
        self.assertNotIn("secret", repr(payload))

    def test_save_configuration_writes_local_env_and_reloads_it(self) -> None:
        env_path = self.root / ".env"
        with patch.dict(os.environ, {}, clear=True):
            status = save_model_configuration(env_path, "sk-test", "test-model")
            self.assertTrue(status.configured)
            self.assertEqual(os.environ["OPENAI_MODEL"], "test-model")
        contents = env_path.read_text(encoding="utf-8")
        self.assertIn("OPENAI_API_KEY='sk-test'", contents)

    def test_first_configuration_requires_key(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ModelConfigurationError):
                save_model_configuration(self.root / ".env", "", "test-model")


if __name__ == "__main__":
    unittest.main()
