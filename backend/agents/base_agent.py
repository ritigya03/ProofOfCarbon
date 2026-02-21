import os
import json
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class BaseAgent:
    """
    Base class for all ProofOfCarbon agents.
    All specialized agents inherit from this and override run().
    """

    def __init__(
        self,
        name: str,
        system_prompt: str,
        model: str = "gpt-4o-mini",
        max_retries: int = 3,
    ):
        self.name = name
        self.system_prompt = system_prompt
        self.model = model
        self.max_retries = max_retries
        self._init_client()

    def _init_client(self):
        """Initialize LLM client. Supports OpenAI or Groq via env vars."""
        groq_key = os.getenv("LLM_API_KEY")
        # openai_key = os.getenv("LLM_API_KEY")

        if groq_key:
            from groq import Groq

            self.client = Groq(api_key=groq_key)
            if self.model == "gpt-4o-mini":
                self.model = "llama-3.3-70b-versatile"  # Groq default
            logger.info(f"[{self.name}] Using Groq client with model {self.model}")
        # if openai_key:
        #     from openai import OpenAI

        #     self.client = OpenAI(api_key=openai_key)
        #     logger.info(f"[{self.name}] Using OpenAI client with model {self.model}")
        else:
            raise EnvironmentError(
                "Neither GROQ_API_KEY nor LLM_API_KEY found in environment."
            )

    def run(self, input_data: dict) -> dict:
        """Override this in subclasses."""
        raise NotImplementedError(f"{self.name} must implement run()")

    def _call_llm(self, user_input: str, json_mode: bool = True) -> str:
        """
        Call the LLM with retry logic.
        Returns raw string response content.
        """
        for attempt in range(self.max_retries):
            try:
                kwargs = dict(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": user_input},
                    ],
                    temperature=0.1,
                )
                # JSON mode — OpenAI specific, skip for Groq
                if json_mode and os.getenv("LLM_API_KEY"):
                    kwargs["response_format"] = {"type": "json_object"}

                response = self.client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content
                logger.debug(f"[{self.name}] LLM raw response: {content[:200]}")
                return content

            except Exception as e:
                wait = 2**attempt
                logger.warning(
                    f"[{self.name}] LLM call failed (attempt {attempt+1}): {e}. Retrying in {wait}s"
                )
                time.sleep(wait)

        raise RuntimeError(
            f"[{self.name}] LLM call failed after {self.max_retries} retries"
        )

    def _parse_json(self, raw: str) -> dict:
        """
        Safely parse JSON from LLM response.
        Handles markdown code fences that LLMs sometimes wrap output in.
        """
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Strip ```json ... ``` fences
            clean = raw.strip()
            if clean.startswith("```"):
                lines = clean.split("\n")
                # Remove first and last fence lines
                clean = "\n".join(
                    lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
                )
            try:
                return json.loads(clean.strip())
            except json.JSONDecodeError as e:
                logger.error(
                    f"[{self.name}] Failed to parse JSON: {e}\nRaw: {raw[:500]}"
                )
                raise ValueError(f"LLM returned invalid JSON: {e}")

    def _build_prompt(self, **kwargs) -> str:
        """
        Helper to build a structured prompt string from keyword args.
        Subclasses can use this or build their own.
        """
        parts = []
        for key, value in kwargs.items():
            label = key.replace("_", " ").title()
            if isinstance(value, dict):
                parts.append(f"## {label}\n{json.dumps(value, indent=2)}")
            else:
                parts.append(f"## {label}\n{value}")
        return "\n\n".join(parts)
