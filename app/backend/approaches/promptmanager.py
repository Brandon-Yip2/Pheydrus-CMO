import json
import pathlib

import prompty
from openai.types.chat import ChatCompletionMessageParam


class PromptManager:

    def load_prompt(self, path: str):
        raise NotImplementedError

    def load_tools(self, path: str):
        raise NotImplementedError

    def render_prompt(self, prompt, data) -> list[ChatCompletionMessageParam]:
        raise NotImplementedError


class PromptyManager(PromptManager):

    PROMPTS_DIRECTORY = pathlib.Path(__file__).parent / "prompts"

    def __init__(self):
        # Initialize system prompts as None - will be loaded lazily
        self._cmo_prompt = None
        self._test_prompt = None

    def load_prompt(self, path: str):
        return prompty.load(self.PROMPTS_DIRECTORY / path)

    def load_tools(self, path: str):
        return json.loads(open(self.PROMPTS_DIRECTORY / path).read())

    def render_prompt(self, prompt, data) -> list[ChatCompletionMessageParam]:
        return prompty.prepare(prompt, data)
    
    def get_system_prompt(self, prompt_type: str):
        """Get system prompt by type with lazy loading"""
        if prompt_type == "cmo" and self._cmo_prompt is None:
            self._cmo_prompt = self.load_prompt("cmo_prompt.prompty")
        elif prompt_type == "test" and self._test_prompt is None:
            self._test_prompt = self.load_prompt("test_prompt.prompty")
        
        prompts = {
            "cmo": self._cmo_prompt,
            "test": self._test_prompt
        }
        return prompts.get(prompt_type, None)
