import json
import unittest
from unittest.mock import MagicMock, patch

from modules.services.llm_service import LLMSettings, check_llm_readiness, request_llm_chat


class AzureLLMTests(unittest.TestCase):
    def setUp(self):
        self.settings = LLMSettings(
            provider="azure",
            model="test-deployment",
            api_key=None,
            base_url=None,
            azure_api_key="test-key",
            azure_responses_url="https://example.invalid/openai/responses?existing=1",
            azure_api_version="2025-04-01-preview",
            timeout_seconds=15,
        )

    @patch("modules.services.llm_service.urlopen")
    @patch("modules.services.llm_service.get_llm_settings")
    def test_readiness_uses_azure_responses(self, get_settings, urlopen):
        get_settings.return_value = self.settings
        response = MagicMock()
        response.read.return_value = json.dumps({
            "output": [{"type": "message", "content": [{"type": "output_text", "text": "ready"}]}]
        }).encode("utf-8")
        urlopen.return_value.__enter__.return_value = response

        check_llm_readiness()

        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_method(), "POST")
        self.assertIn("existing=1", request.full_url)
        self.assertIn("api-version=2025-04-01-preview", request.full_url)
        self.assertEqual(request.get_header("Api-key"), "test-key")
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 15)
        self.assertEqual(json.loads(request.data)["model"], "test-deployment")

    @patch("modules.services.llm_service.urlopen")
    @patch("modules.services.llm_service.get_llm_settings")
    def test_chat_returns_azure_output_text(self, get_settings, urlopen):
        get_settings.return_value = self.settings
        response = MagicMock()
        response.read.return_value = b'{"output_text": "analysis complete"}'
        urlopen.return_value.__enter__.return_value = response

        result = request_llm_chat([{"role": "user", "content": "analyze"}], temperature=0.4)

        self.assertEqual(result, "analysis complete")
        payload = json.loads(urlopen.call_args.args[0].data)
        self.assertEqual(payload["input"][0]["content"][0]["text"], "analyze")
        self.assertEqual(payload["temperature"], 0.4)


if __name__ == "__main__":
    unittest.main()
