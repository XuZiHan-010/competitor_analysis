import json
from typing import Any, Literal, cast

from openai import AsyncOpenAI

from services.llm.usage import record_usage
from settings import Settings

LLMRole = Literal["system", "user", "assistant"]
Provider = Literal["openai", "deepseek", "gemini"]


class LLMClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def enabled(self) -> bool:
        return not self._settings.mock_llm

    def _openai_client(self, provider: Literal["openai", "deepseek"]) -> AsyncOpenAI:
        if provider == "openai":
            if not self._settings.openai_api_key:
                raise RuntimeError("OPENAI_API_KEY is required for OpenAI calls")
            return AsyncOpenAI(api_key=self._settings.openai_api_key)
        if not self._settings.deepseek_api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is required for DeepSeek calls")
        return AsyncOpenAI(
            api_key=self._settings.deepseek_api_key,
            base_url="https://api.deepseek.com/v1",
        )

    async def complete_text(
        self,
        *,
        provider: Provider,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
    ) -> str:
        if provider == "gemini":
            return await self._gemini_complete(
                model=model, messages=messages, temperature=temperature, json_mode=False
            )
        client = self._openai_client(provider)
        completions = cast(Any, client.chat.completions)
        response = await completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
        )
        self._record_openai_usage(response)
        return response.choices[0].message.content or ""

    async def complete_json(
        self,
        *,
        provider: Provider,
        model: str,
        messages: list[dict[str, str]],
    ) -> dict[str, Any]:
        if provider == "gemini":
            content = await self._gemini_complete(
                model=model, messages=messages, temperature=0.2, json_mode=True
            )
            return json.loads(content or "{}")
        client = self._openai_client(provider)
        completions = cast(Any, client.chat.completions)
        response = await completions.create(
            model=model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        self._record_openai_usage(response)
        content = response.choices[0].message.content or "{}"
        return json.loads(content)

    async def _gemini_complete(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        json_mode: bool,
    ) -> str:
        if not self._settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is required for Gemini calls")
        # Lazy import: google-genai pulls in heavy transitive deps and is only
        # needed on the real Gemini path (CollectorAgent), never under mock LLM.
        from google import genai
        from google.genai import types

        client = cast(Any, genai).Client(api_key=self._settings.gemini_api_key)
        system_instruction = "\n".join(
            message["content"] for message in messages if message["role"] == "system"
        )
        contents = [message["content"] for message in messages if message["role"] != "system"]
        config = cast(Any, types).GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_instruction or None,
            response_mime_type="application/json" if json_mode else None,
        )
        response = await client.aio.models.generate_content(
            model=model, contents=contents, config=config
        )
        usage = getattr(response, "usage_metadata", None)
        if usage is not None:
            record_usage(
                int(getattr(usage, "prompt_token_count", 0) or 0),
                int(getattr(usage, "candidates_token_count", 0) or 0),
            )
        return response.text or ""

    def _record_openai_usage(self, response: Any) -> None:
        usage = getattr(response, "usage", None)
        if usage is not None:
            record_usage(
                int(getattr(usage, "prompt_tokens", 0) or 0),
                int(getattr(usage, "completion_tokens", 0) or 0),
            )
