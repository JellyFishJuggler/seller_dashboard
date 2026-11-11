import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from seller_dashboard import api as api_module
from seller_dashboard import bot
from seller_dashboard import sarvam_credentials
from seller_dashboard.assistant_style import ENGLISH_RESPONSE_PROMPT, FEMININE_VOICE_PROMPT


class EmptyRetriever:
    def retrieve(self, _query, k=4):
        return []


class SarvamBrowserProfileKeyTests(unittest.TestCase):
    def test_two_deployment_keys_fall_back_after_key_rejection(self):
        client_id = "two-deployment-keys-test"
        sarvam_credentials._CLIENT_KEY_INDEX.pop(client_id, None)
        with patch.dict(
            os.environ,
            {
                "SARVAM_API_KEY_1": "primary-test-key",
                "SARVAM_API_KEY_2": "backup-test-key",
                "SARVAM_API_KEY": "",
            },
            clear=True,
        ):
            self.assertEqual(
                sarvam_credentials.get_client_sarvam_api_keys(client_id),
                ["primary-test-key", "backup-test-key"],
            )
            self.assertEqual(
                sarvam_credentials.advance_client_sarvam_api_key(
                    client_id, "primary-test-key"
                ),
                "backup-test-key",
            )
            self.assertEqual(
                sarvam_credentials.get_client_sarvam_api_key(client_id),
                "backup-test-key",
            )
            self.assertTrue(
                sarvam_credentials.is_sarvam_credential_error(
                    RuntimeError("error 1003: invalid subscription key")
                )
            )
            self.assertTrue(
                sarvam_credentials.is_sarvam_credential_error(
                    RuntimeError("quota exceeded")
                )
            )
            self.assertFalse(
                sarvam_credentials.is_sarvam_credential_error(
                    RuntimeError("temporary network issue")
                )
            )
        sarvam_credentials._CLIENT_KEY_INDEX.pop(client_id, None)

    def test_custom_key_isolated_per_browser_profile_and_persists(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "credentials.json"
            with patch.dict(os.environ, {
                "SARVAM_API_KEY": "deployment-key",
                "SARVAM_CREDENTIALS_PATH": str(path),
            }):
                first_status = sarvam_credentials.set_client_sarvam_api_key(
                    "browser-one", "private-one"
                )
                self.assertEqual(first_status["source"], "custom")
                self.assertEqual(
                    sarvam_credentials.get_client_sarvam_api_key("browser-one"),
                    "private-one",
                )
                self.assertEqual(
                    sarvam_credentials.get_client_sarvam_api_key("browser-two"),
                    "deployment-key",
                )
                self.assertNotIn("private-one", str(first_status))

                self.assertEqual(
                    sarvam_credentials.get_client_sarvam_api_key("browser-one"),
                    "private-one",
                )
                cleared = sarvam_credentials.set_client_sarvam_api_key(
                    "browser-one", ""
                )
                self.assertEqual(cleared["source"], "env")
                self.assertEqual(
                    sarvam_credentials.get_client_sarvam_api_key("browser-one"),
                    "deployment-key",
                )

    def test_settings_routes_only_change_the_requesting_browser_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "credentials.json"
            with patch.dict(os.environ, {
                "SARVAM_API_KEY": "deployment-key",
                "SARVAM_CREDENTIALS_PATH": str(path),
            }):
                with TestClient(api_module.app) as client:
                    saved = client.post(
                        "/settings/sarvam-key",
                        json={"client_id": "browser-one", "api_key": "custom-one"},
                    )
                    self.assertEqual(saved.status_code, 200)
                    self.assertEqual(saved.json()["source"], "custom")
                    self.assertNotIn("custom-one", saved.text)

                    first = client.get(
                        "/settings/sarvam-key",
                        params={"client_id": "browser-one"},
                    )
                    second = client.get(
                        "/settings/sarvam-key",
                        params={"client_id": "browser-two"},
                    )
                    self.assertEqual(first.json()["source"], "custom")
                    self.assertEqual(second.json()["source"], "env")

    def test_graph_uses_english_for_text_and_hindi_for_voice(self):
        class FakeModel:
            def bind_tools(self, _tools):
                return self

            def invoke(self, messages):
                policy = next(
                    message.content
                    for message in messages
                    if message.content in {
                        ENGLISH_RESPONSE_PROMPT,
                        FEMININE_VOICE_PROMPT,
                    }
                )
                self.policies.append(policy)
                return bot.AIMessage(
                    content=(
                        "Your sales changed this month."
                        if policy == ENGLISH_RESPONSE_PROMPT
                        else "इस महीने आपकी sales में बदलाव आया है।"
                    )
                )

            def __init__(self):
                self.policies = []

        fake_model = FakeModel()
        with (
            patch.object(bot, "llm", fake_model),
            patch.object(bot, "_llm_key", "unit-test-key"),
            patch.object(bot, "_rag_retriever", EmptyRetriever()),
            patch.object(
                bot,
                "get_client_sarvam_api_key",
                return_value="unit-test-key",
            ),
            patch.object(
                bot,
                "get_client_sarvam_api_keys",
                return_value=["unit-test-key"],
            ),
        ):
            graph = bot.build_graph()
            text = graph.invoke(
                {"messages": [bot.HumanMessage(content="What changed in sales?")]},
                {"configurable": {"thread_id": "text-mode-session", "voice_mode": False}},
            )
            voice = graph.invoke(
                {"messages": [bot.HumanMessage(content="What changed in sales?")]},
                {"configurable": {"thread_id": "voice-mode-session", "voice_mode": True}},
            )

        self.assertIn("Your sales", text["messages"][-1].content)
        self.assertIn("इस महीने", voice["messages"][-1].content)
        self.assertEqual(
            fake_model.policies,
            [ENGLISH_RESPONSE_PROMPT, FEMININE_VOICE_PROMPT],
        )

    def test_graph_uses_each_browser_profiles_llm_key_without_global_rotation(self):
        class FakeModel:
            def __init__(self):
                self.calls = 0

            def bind_tools(self, _tools):
                return self

            def invoke(self, _messages):
                self.calls += 1
                return bot.AIMessage(content="A clear English response.")

        deployment_model = FakeModel()
        custom_model = FakeModel()
        with (
            patch.object(bot, "llm", deployment_model),
            patch.object(bot, "_llm_key", "unit-test-key"),
            patch.object(bot, "_rag_retriever", EmptyRetriever()),
            patch.object(
                bot,
                "get_client_sarvam_api_key",
                side_effect=lambda client_id: (
                    "custom-browser-key"
                    if client_id == "browser-custom"
                    else "unit-test-key"
                ),
            ),
            patch.object(
                bot,
                "get_client_sarvam_api_keys",
                side_effect=lambda client_id: (
                    ["custom-browser-key"]
                    if client_id == "browser-custom"
                    else ["unit-test-key"]
                ),
            ),
            patch.object(
                bot,
                "build_sarvam_llm",
                return_value=custom_model,
            ) as build_custom_llm,
        ):
            graph = bot.build_graph()
            graph.invoke(
                {"messages": [bot.HumanMessage(content="How are sales?")]},
                {"configurable": {
                    "thread_id": "custom-session",
                    "client_id": "browser-custom",
                }},
            )
            graph.invoke(
                {"messages": [bot.HumanMessage(content="How are sales?")]},
                {"configurable": {
                    "thread_id": "deployment-session",
                    "client_id": "browser-default",
                }},
            )

        build_custom_llm.assert_called_once_with("custom-browser-key")
        self.assertEqual(custom_model.calls, 1)
        self.assertEqual(deployment_model.calls, 1)

    def test_graph_falls_back_to_second_deployment_key_after_auth_error(self):
        class FakeModel:
            def __init__(self, error=None):
                self.error = error
                self.calls = 0

            def bind_tools(self, _tools):
                return self

            def invoke(self, _messages):
                self.calls += 1
                if self.error:
                    raise self.error
                return bot.AIMessage(content="मैं आपकी मदद कर सकती हूँ।")

        deployment_model = FakeModel()
        primary_model = FakeModel(RuntimeError("1003 invalid subscription key"))
        backup_model = FakeModel()
        with (
            patch.object(bot, "llm", deployment_model),
            patch.object(bot, "_rag_retriever", EmptyRetriever()),
            patch.object(
                bot,
                "get_client_sarvam_api_key",
                return_value="primary-test-key",
            ),
            patch.object(
                bot,
                "get_client_sarvam_api_keys",
                return_value=["primary-test-key", "backup-test-key"],
            ),
            patch.object(
                bot,
                "advance_client_sarvam_api_key",
            ) as advance_key,
            patch.object(
                bot,
                "build_sarvam_llm",
                side_effect=[primary_model, backup_model],
            ) as build_model,
        ):
            graph = bot.build_graph()
            result = graph.invoke(
                {"messages": [bot.HumanMessage(content="मेरी बिक्री कैसी है?")]},
                {"configurable": {
                    "thread_id": "key-fallback-session",
                    "client_id": "key-fallback-browser",
                    "voice_mode": True,
                }},
            )

        self.assertIn("मदद", result["messages"][-1].content)
        self.assertEqual(primary_model.calls, 1)
        self.assertEqual(backup_model.calls, 1)
        self.assertEqual(build_model.call_args_list[0].args, ("primary-test-key",))
        self.assertEqual(build_model.call_args_list[1].args, ("backup-test-key",))
        advance_key.assert_called_once_with(
            "key-fallback-browser", "primary-test-key"
        )


if __name__ == "__main__":
    unittest.main()
