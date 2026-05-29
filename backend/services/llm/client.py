import json
from typing import Any, Literal, cast

from openai import AsyncOpenAI

from settings import Settings

LLMRole = Literal["system", "user", "assistant"]


class LLMMessage(dict[str, str]):
    role: LLMRole
    content: str


class LLMClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def enabled(self) -> bool:
        return not self._settings.mock_llm

    async def complete_json(
        self,
        *,
        provider: Literal["openai", "deepseek"],
        model: str,
        messages: list[dict[str, str]],
    ) -> dict[str, Any]:
        if provider == "openai":
            if not self._settings.openai_api_key:
                raise RuntimeError("OPENAI_API_KEY is required for OpenAI calls")
            client = AsyncOpenAI(api_key=self._settings.openai_api_key)
        else:
            if not self._settings.deepseek_api_key:
                raise RuntimeError("DEEPSEEK_API_KEY is required for DeepSeek calls")
            client = AsyncOpenAI(
                api_key=self._settings.deepseek_api_key,
                base_url="https://api.deepseek.com/v1",
            )

        completions = cast(Any, client.chat.completions)
        response = await completions.create(
            model=model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        content = response.choices[0].message.content or "{}"
        return json.loads(content)
