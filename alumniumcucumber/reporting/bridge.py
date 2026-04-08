"""LLM Provider Bridge for the Alumnium reporter.

Routes text completion calls to whichever LLM provider the user has configured
for alumnium via the ALUMNIUM_MODEL environment variable.
"""

from __future__ import annotations

import os


class LlmBridgeError(Exception):
    """Raised when the LLM provider call fails."""
    pass


class LlmProviderBridge:
    """Thin abstraction that routes completion calls to the configured LLM provider.

    Reads ALUMNIUM_MODEL at instantiation time and selects the appropriate backend.
    Uses lazy imports so the reporter works even if provider libraries are not installed.
    """

    def __init__(self) -> None:
        """Initialise the bridge, reading ALUMNIUM_MODEL from the environment."""
        raw = os.environ.get("ALUMNIUM_MODEL", "").strip()
        self._raw_model = raw
        self._provider, self._model = self._parse_model_env(raw)

    def _parse_model_env(self, raw: str) -> tuple[str, str]:
        """Parse the ALUMNIUM_MODEL value into (provider, model_id).

        If the value contains '/', the part before is the provider and
        the part after is the model override.
        """
        lower = raw.lower()
        if not lower:
            return ("unset", "")

        if "/" in lower:
            provider_part, model_part = lower.split("/", 1)
            # Use original case for model (important for IDs like claude-3-5-sonnet...)
            _, model_part_original = raw.split("/", 1)
        else:
            provider_part = lower
            model_part = ""
            model_part_original = ""

        provider = provider_part.strip()
        model = model_part_original.strip()

        return (provider, model)

    @property
    def provider_name(self) -> str:
        """Human-readable provider name, e.g. 'anthropic', 'openai', 'ollama'."""
        return self._provider

    def complete(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 800,
    ) -> str:
        """Send a completion request to the configured LLM provider.

        Returns the response text.
        Raises LlmBridgeError on failure.
        """
        provider = self._provider
        if provider == "unset" or not provider:
            raise LlmBridgeError(
                "ALUMNIUM_MODEL is not set or unrecognised. "
                "Set it to: anthropic, openai, google, ollama, mistral, deepseek, xai, or aws."
            )

        _RECOGNIZED = {
            "anthropic", "openai", "google", "ollama",
            "mistral", "deepseek", "xai", "aws",
        }
        if provider not in _RECOGNIZED:
            raise LlmBridgeError(
                f"ALUMNIUM_MODEL '{self._raw_model}' is not recognised. "
                "Set it to: anthropic, openai, google, ollama, mistral, deepseek, xai, or aws."
            )

        try:
            if provider == "anthropic":
                return self._complete_anthropic(system_prompt, user_message, max_tokens)
            elif provider == "openai":
                return self._complete_openai(system_prompt, user_message, max_tokens)
            elif provider == "google":
                return self._complete_google(system_prompt, user_message, max_tokens)
            elif provider == "ollama":
                return self._complete_ollama(system_prompt, user_message, max_tokens)
            elif provider == "mistral":
                return self._complete_mistral(system_prompt, user_message, max_tokens)
            elif provider == "deepseek":
                return self._complete_deepseek(system_prompt, user_message, max_tokens)
            elif provider == "xai":
                return self._complete_xai(system_prompt, user_message, max_tokens)
            elif provider == "aws":
                return self._complete_aws(system_prompt, user_message, max_tokens)
        except LlmBridgeError:
            raise
        except Exception as e:
            raise LlmBridgeError(str(e)) from e

    def _complete_anthropic(self, system_prompt: str, user_message: str, max_tokens: int) -> str:
        """Complete using Anthropic Claude."""
        try:
            import anthropic  # noqa: PLC0415
        except ImportError as e:
            raise LlmBridgeError(f"anthropic package not installed: {e}") from e

        model = self._model or "claude-sonnet-4-20250514"
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text

    def _complete_openai(self, system_prompt: str, user_message: str, max_tokens: int) -> str:
        """Complete using OpenAI."""
        try:
            import openai  # noqa: PLC0415
        except ImportError as e:
            raise LlmBridgeError(f"openai package not installed: {e}") from e

        model = self._model or "gpt-4o"
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )
        return response.choices[0].message.content

    def _complete_google(self, system_prompt: str, user_message: str, max_tokens: int) -> str:
        """Complete using Google Gemini."""
        try:
            import google.generativeai as genai  # noqa: PLC0415
        except ImportError as e:
            raise LlmBridgeError(f"google-generativeai package not installed: {e}") from e

        model_name = self._model or "gemini-1.5-flash"
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_prompt,
        )
        response = model.generate_content(
            user_message,
            generation_config=genai.types.GenerationConfig(max_output_tokens=max_tokens),
        )
        return response.text

    def _complete_ollama(self, system_prompt: str, user_message: str, max_tokens: int) -> str:
        """Complete using Ollama (local HTTP API)."""
        import json  # noqa: PLC0415
        try:
            import urllib.request  # noqa: PLC0415
        except ImportError as e:
            raise LlmBridgeError(f"urllib not available: {e}") from e

        model = self._model or "mistral-small3.1"
        payload = json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "stream": False,
            "options": {"num_predict": max_tokens},
        }).encode("utf-8")

        req = urllib.request.Request(
            "http://localhost:11434/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        return result["message"]["content"]

    def _complete_mistral(self, system_prompt: str, user_message: str, max_tokens: int) -> str:
        """Complete using Mistral AI."""
        try:
            from mistralai import Mistral  # noqa: PLC0415
        except ImportError as e:
            raise LlmBridgeError(f"mistralai package not installed: {e}") from e

        model = self._model or "mistral-small-latest"
        client = Mistral()
        response = client.chat.complete(
            model=model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )
        return response.choices[0].message.content

    def _complete_deepseek(self, system_prompt: str, user_message: str, max_tokens: int) -> str:
        """Complete using DeepSeek (OpenAI-compatible endpoint)."""
        try:
            import openai  # noqa: PLC0415
        except ImportError as e:
            raise LlmBridgeError(f"openai package not installed: {e}") from e

        model = self._model or "deepseek-chat"
        api_key = os.environ.get("DEEPSEEK_API_KEY", os.environ.get("OPENAI_API_KEY", ""))
        client = openai.OpenAI(
            base_url="https://api.deepseek.com",
            api_key=api_key,
        )
        response = client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )
        return response.choices[0].message.content

    def _complete_xai(self, system_prompt: str, user_message: str, max_tokens: int) -> str:
        """Complete using xAI Grok (OpenAI-compatible endpoint)."""
        try:
            import openai  # noqa: PLC0415
        except ImportError as e:
            raise LlmBridgeError(f"openai package not installed: {e}") from e

        model = self._model or "grok-beta"
        api_key = os.environ.get("XAI_API_KEY", os.environ.get("OPENAI_API_KEY", ""))
        client = openai.OpenAI(
            base_url="https://api.x.ai/v1",
            api_key=api_key,
        )
        response = client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )
        return response.choices[0].message.content

    def _complete_aws(self, system_prompt: str, user_message: str, max_tokens: int) -> str:
        """Complete using AWS Bedrock."""
        import json  # noqa: PLC0415
        try:
            import boto3  # noqa: PLC0415
        except ImportError as e:
            raise LlmBridgeError(f"boto3 package not installed: {e}") from e

        model = self._model or "anthropic.claude-3-5-sonnet-20241022-v2:0"
        client = boto3.client("bedrock-runtime")
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_message}],
        })
        response = client.invoke_model(modelId=model, body=body)
        result = json.loads(response["body"].read())
        return result["content"][0]["text"]
