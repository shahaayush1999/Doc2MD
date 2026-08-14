#!/usr/bin/env python3

import json
import sys
from pathlib import Path
from typing import Any

from markitdown import MarkItDown
from openai import OpenAI


class UsageMeter:
    def __init__(self) -> None:
        self.attempted_calls = 0
        self.successful_calls = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.cached_input_tokens = 0
        self.errors: list[str] = []

    def record(self, response: Any) -> None:
        self.successful_calls += 1
        usage = getattr(response, "usage", None)
        if usage is None:
            return
        self.input_tokens += int(getattr(usage, "prompt_tokens", 0) or 0)
        self.output_tokens += int(getattr(usage, "completion_tokens", 0) or 0)
        details = getattr(usage, "prompt_tokens_details", None)
        self.cached_input_tokens += int(getattr(details, "cached_tokens", 0) or 0)


class RecordingCompletions:
    def __init__(self, inner: Any, meter: UsageMeter) -> None:
        self._inner = inner
        self._meter = meter

    def create(self, *args: Any, **kwargs: Any) -> Any:
        self._meter.attempted_calls += 1
        try:
            response = self._inner.create(*args, **kwargs)
        except Exception as error:
            self._meter.errors.append(f"{type(error).__name__}: {error}")
            raise
        self._meter.record(response)
        return response


class RecordingChat:
    def __init__(self, inner: Any, meter: UsageMeter) -> None:
        self.completions = RecordingCompletions(inner.completions, meter)


class RecordingClient:
    def __init__(self, inner: Any, meter: UsageMeter) -> None:
        self._inner = inner
        self.chat = RecordingChat(inner.chat, meter)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: run_markitdown_ocr.py INPUT.pdf PROMPT.md METADATA.json")

    source, prompt_path, metadata_path = sys.argv[1:]
    meter = UsageMeter()
    client = RecordingClient(OpenAI(), meter)
    converter = MarkItDown(
        enable_plugins=True,
        llm_client=client,
        llm_model="gpt-5.6-luna",
        llm_prompt=Path(prompt_path).read_text(encoding="utf-8").strip(),
    )
    result = converter.convert(source)
    Path(metadata_path).write_text(
        json.dumps(
            {
                "attemptedVisionCalls": meter.attempted_calls,
                "successfulVisionCalls": meter.successful_calls,
                "errors": meter.errors,
                "usage": {
                    "inputTokens": meter.input_tokens,
                    "outputTokens": meter.output_tokens,
                    "inputTokenDetails": {
                        "cacheReadTokens": meter.cached_input_tokens,
                    },
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    sys.stdout.write(result.text_content)


if __name__ == "__main__":
    main()
