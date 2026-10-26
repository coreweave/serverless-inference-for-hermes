# SPDX-FileCopyrightText: 2026 CoreWeave, Inc.
# SPDX-License-Identifier: MIT
# SPDX-PackageName: serverless-inference-for-hermes

"""Run with the real Hermes registry in an approved Linux test workspace."""
import io
import json
import os
from pathlib import Path
import shutil
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

if sys.platform != "linux":
    raise SystemExit("Run Hermes integration checks in an approved Linux sandbox.")

PLUGIN = Path(__file__).resolve().parents[1]
TEST_KEY = "test-coreweave-key-not-a-real-credential"


class ProviderContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temporary = tempfile.TemporaryDirectory(prefix="coreweave-provider-test-")
        cls.addClassCleanup(temporary.cleanup)
        cls.home = Path(temporary.name)
        env = patch.dict(os.environ, {
            "PATH": os.environ.get("PATH", ""),
            "HOME": str(cls.home),
            "HERMES_HOME": str(cls.home),
            "COREWEAVE_API_KEY": TEST_KEY,
        }, clear=True)
        env.start()
        cls.addClassCleanup(env.stop)
        # The suite uses synthetic credentials and must never reach a real service.
        network = patch.object(socket.socket, "connect", side_effect=AssertionError("Network disabled"))
        network.start()
        cls.addClassCleanup(network.stop)
        installed = cls.home / "plugins" / "coreweave"
        installed.mkdir(parents=True)
        for name in ("__init__.py", "plugin.yaml"):
            shutil.copyfile(PLUGIN / name, installed / name)
        from providers import get_provider_profile
        cls.profile = get_provider_profile("coreweave")
        if cls.profile is None:
            raise AssertionError("Hermes did not discover the installed provider plugin")

    def test_installed_provider_is_listed(self):
        from providers import list_providers
        matches = [p for p in list_providers() if p.name == "coreweave"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].display_name, "CoreWeave Inference")
        self.assertTrue(matches[0].listed())

    def test_runtime_uses_coreweave_key_endpoint_and_transport(self):
        from hermes_cli.runtime_provider import resolve_runtime_provider
        runtime = resolve_runtime_provider(requested="coreweave")
        self.assertEqual(runtime["api_key"], TEST_KEY)
        self.assertEqual(runtime["base_url"], "https://api.inference.wandb.ai/v1")
        self.assertEqual(runtime["api_mode"], "chat_completions")

    def test_missing_key_fails_instead_of_selecting_another_provider(self):
        from hermes_cli.auth import AuthError
        from hermes_cli.runtime_provider import resolve_runtime_provider
        with patch.dict(os.environ, {"COREWEAVE_API_KEY": ""}):
            with self.assertRaises(AuthError) as result:
                resolve_runtime_provider(requested="coreweave")
        self.assertEqual(result.exception.code, "missing_api_key")

    def test_model_discovery_sends_bearer_key_and_reads_catalog(self):
        payload = {"data": [{"id": "test/chat-model", "object": "model"}]}
        with patch("hermes_cli.urllib_security.open_credentialed_url",
                   return_value=io.BytesIO(json.dumps(payload).encode())) as request:
            self.assertEqual(self.profile.fetch_models(api_key=TEST_KEY), ["test/chat-model"])
        sent = request.call_args.args[0]
        self.assertEqual(sent.full_url, "https://api.inference.wandb.ai/v1/models")
        self.assertEqual(sent.get_header("Authorization"), "Bearer " + TEST_KEY)

    def test_catalog_failure_does_not_invent_available_models(self):
        error = HTTPError("https://api.inference.wandb.ai/v1/models", 401, "Unauthorized", {}, None)
        with patch("hermes_cli.urllib_security.open_credentialed_url", side_effect=error):
            self.assertIsNone(self.profile.fetch_models(api_key=TEST_KEY))
        self.assertEqual(self.profile.fallback_models, ())

    def test_plugin_does_not_leak_to_another_hermes_profile(self):
        from providers import get_provider_profile
        with tempfile.TemporaryDirectory() as other:
            with patch.dict(os.environ, {"HERMES_HOME": other}):
                self.assertIsNone(get_provider_profile("coreweave"))
        self.assertIsNotNone(get_provider_profile("coreweave"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
