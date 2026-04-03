"""Tests for alumniumcucumber.reporting.bridge."""

import os
from unittest.mock import MagicMock, patch

import pytest

from alumniumcucumber.reporting.bridge import LlmBridgeError, LlmProviderBridge


class TestBridgeInit:
    def test_raises_when_model_unset(self, monkeypatch):
        monkeypatch.delenv("ALUMNIUM_MODEL", raising=False)
        bridge = LlmProviderBridge()
        with pytest.raises(LlmBridgeError, match="ALUMNIUM_MODEL is not set"):
            bridge.complete("sys", "user")

    def test_raises_for_unrecognised_value(self, monkeypatch):
        monkeypatch.setenv("ALUMNIUM_MODEL", "unknown_provider")
        bridge = LlmProviderBridge()
        with pytest.raises(LlmBridgeError, match="not recognised"):
            bridge.complete("sys", "user")

    def test_provider_name_anthropic(self, monkeypatch):
        monkeypatch.setenv("ALUMNIUM_MODEL", "anthropic")
        bridge = LlmProviderBridge()
        assert bridge.provider_name == "anthropic"

    def test_provider_name_openai(self, monkeypatch):
        monkeypatch.setenv("ALUMNIUM_MODEL", "openai")
        bridge = LlmProviderBridge()
        assert bridge.provider_name == "openai"

    def test_provider_name_google(self, monkeypatch):
        monkeypatch.setenv("ALUMNIUM_MODEL", "google")
        bridge = LlmProviderBridge()
        assert bridge.provider_name == "google"

    def test_provider_name_ollama(self, monkeypatch):
        monkeypatch.setenv("ALUMNIUM_MODEL", "ollama")
        bridge = LlmProviderBridge()
        assert bridge.provider_name == "ollama"

    def test_provider_name_mistral(self, monkeypatch):
        monkeypatch.setenv("ALUMNIUM_MODEL", "mistral")
        bridge = LlmProviderBridge()
        assert bridge.provider_name == "mistral"

    def test_provider_name_deepseek(self, monkeypatch):
        monkeypatch.setenv("ALUMNIUM_MODEL", "deepseek")
        bridge = LlmProviderBridge()
        assert bridge.provider_name == "deepseek"

    def test_provider_name_xai(self, monkeypatch):
        monkeypatch.setenv("ALUMNIUM_MODEL", "xai")
        bridge = LlmProviderBridge()
        assert bridge.provider_name == "xai"

    def test_provider_name_aws(self, monkeypatch):
        monkeypatch.setenv("ALUMNIUM_MODEL", "aws")
        bridge = LlmProviderBridge()
        assert bridge.provider_name == "aws"


class TestModelOverride:
    def test_model_override_anthropic(self, monkeypatch):
        monkeypatch.setenv("ALUMNIUM_MODEL", "anthropic/claude-opus-4-20250514")
        bridge = LlmProviderBridge()
        assert bridge.provider_name == "anthropic"
        assert bridge._model == "claude-opus-4-20250514"

    def test_model_override_openai(self, monkeypatch):
        monkeypatch.setenv("ALUMNIUM_MODEL", "openai/gpt-4-turbo")
        bridge = LlmProviderBridge()
        assert bridge.provider_name == "openai"
        assert bridge._model == "gpt-4-turbo"


class TestAnthropicComplete:
    def test_calls_anthropic_and_returns_text(self, monkeypatch):
        monkeypatch.setenv("ALUMNIUM_MODEL", "anthropic")
        bridge = LlmProviderBridge()

        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text="test response")]
        mock_client.messages.create.return_value = mock_msg

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            result = bridge.complete("system", "user msg", max_tokens=100)

        assert result == "test response"
        mock_client.messages.create.assert_called_once()

    def test_wraps_exception_as_llm_bridge_error(self, monkeypatch):
        monkeypatch.setenv("ALUMNIUM_MODEL", "anthropic")
        bridge = LlmProviderBridge()

        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_client.messages.create.side_effect = RuntimeError("API down")

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            with pytest.raises(LlmBridgeError, match="API down"):
                bridge.complete("system", "user")


class TestOpenAIComplete:
    def test_calls_openai_and_returns_text(self, monkeypatch):
        monkeypatch.setenv("ALUMNIUM_MODEL", "openai")
        bridge = LlmProviderBridge()

        mock_openai = MagicMock()
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client
        mock_choice = MagicMock()
        mock_choice.message.content = "openai response"
        mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

        with patch.dict("sys.modules", {"openai": mock_openai}):
            result = bridge.complete("sys", "user", max_tokens=200)

        assert result == "openai response"

    def test_wraps_exception_as_llm_bridge_error(self, monkeypatch):
        monkeypatch.setenv("ALUMNIUM_MODEL", "openai")
        bridge = LlmProviderBridge()

        mock_openai = MagicMock()
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client
        mock_client.chat.completions.create.side_effect = RuntimeError("timeout")

        with patch.dict("sys.modules", {"openai": mock_openai}):
            with pytest.raises(LlmBridgeError, match="timeout"):
                bridge.complete("sys", "user")
