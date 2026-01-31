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
        pass

    def load_prompt(self, path: str):
        return prompty.load(self.PROMPTS_DIRECTORY / path)

    def load_tools(self, path: str):
        return json.loads(open(self.PROMPTS_DIRECTORY / path).read())

    def render_prompt(self, prompt, data) -> list[ChatCompletionMessageParam]:
        return prompty.prepare(prompt, data)
    
    def get_system_prompt_text(self, prompt_type: str) -> str | None:
        """Get system prompt text by type. Extracts and renders the system section from the prompty file."""
        prompt_files = {
            "cmo": "cmo_prompt.prompty",
            "public_cmo": "public_cmo_prompt.prompty",
            "test": "test_prompt.prompty"
        }

        filename = prompt_files.get(prompt_type)
        if not filename:
            return None

        filepath = self.PROMPTS_DIRECTORY / filename
        if not filepath.exists():
            return None

        # Read the file and extract system section
        content = filepath.read_text(encoding="utf-8")

        # Find the system section (after the YAML frontmatter)
        # Format is: ---\n...yaml...\n---\nsystem:\n...content...
        parts = content.split("---")
        if len(parts) >= 3:
            # Content after the second ---
            system_content = "---".join(parts[2:]).strip()
            if system_content.startswith("system:"):
                system_content = system_content[7:].strip()  # Remove "system:" prefix
            return system_content

        return None

    def get_system_prompt(self, prompt_type: str):
        """Get system prompt text by type (wrapper for backwards compatibility)"""
        return self.get_system_prompt_text(prompt_type)
