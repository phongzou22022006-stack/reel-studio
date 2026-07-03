"""
Template system for scripts and prompts.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from app.config import config
from app.models.schema import ScriptTemplate, PromptTemplate, StyleConfig
from app.utils import utils


class TemplateEngine:
    """Engine for loading and rendering templates."""

    def __init__(self):
        self.root = utils.root_dir()
        self.template_dirs = {
            "script": self.root / "templates" / "scripts",
            "prompt": self.root / "templates" / "prompts",
            "style": self.root / "styles",
        }

        # Ensure directories exist
        for dir_path in self.template_dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)

        # Create default templates if missing
        self._create_default_templates()

    def _create_default_templates(self):
        """Create default templates if they don't exist."""
        # Default script template
        default_script = self.template_dirs["script"] / "default.md"
        if not default_script.exists():
            content = """# {topic}

## Hook (0-3s)
{question}

## Problem (3-10s)
Most people think {common_misconception}, but actually {truth}.

## Twist (10-20s)
Here's what you're missing: {insight}.

## Solution (20-30s)
{actionable_tip}

## CTA (30-35s)
{call_to_action}
"""
            utils.write_text(default_script, content)

        # Default prompt template
        default_prompt = self.template_dirs["prompt"] / "default.txt"
        if not default_prompt.exists():
            content = """Cinematic, 16:9, realistic photo, dramatic lighting, {scene_description}, shallow depth of field, color grading warm"""
            utils.write_text(default_prompt, content)

        # Default style config
        default_style = self.template_dirs["style"] / "default.yaml"
        if not default_style.exists():
            content = """name: default
script_template: default
prompt_template: default
video_aspect: 16:9
visual_source: ai
tone: educational
length: 30
"""
            utils.save_yaml(default_style, {"name": "default", "script_template": "default", "prompt_template": "default", "video_aspect": "16:9", "visual_source": "ai", "tone": "educational", "length": 30})

    def list_script_templates(self) -> List[ScriptTemplate]:
        """List all available script templates."""
        templates = []
        for file_path in self.template_dirs["script"].iterdir():
            if file_path.suffix.lower() in {".md", ".txt"}:
                content = utils.read_text(file_path)
                # Extract variables from template
                variables = re.findall(r"\{(\w+)\}", content)
                templates.append(
                    ScriptTemplate(
                        name=file_path.stem,
                        path=str(file_path),
                        description="",
                        variables=list(set(variables)),
                    )
                )
        return sorted(templates, key=lambda t: t.name)

    def list_prompt_templates(self) -> List[PromptTemplate]:
        """List all available prompt templates."""
        templates = []
        for file_path in self.template_dirs["prompt"].iterdir():
            if file_path.suffix.lower() in {".txt", ".md"}:
                content = utils.read_text(file_path)
                variables = re.findall(r"\{(\w+)\}", content)
                templates.append(
                    PromptTemplate(
                        name=file_path.stem,
                        path=str(file_path),
                        description="",
                        variables=list(set(variables)),
                    )
                )
        return sorted(templates, key=lambda t: t.name)

    def list_style_configs(self) -> List[StyleConfig]:
        """List all available style configs."""
        configs = []
        for file_path in self.template_dirs["style"].iterdir():
            if file_path.suffix.lower() == ".yaml":
                try:
                    data = utils.load_yaml(file_path)
                    configs.append(
                        StyleConfig(
                            name=data.get("name", file_path.stem),
                            script_template=data.get("script_template", "default"),
                            prompt_template=data.get("prompt_template", "default"),
                            video_aspect=data.get("video_aspect", "16:9"),
                            visual_source=data.get("visual_source", "ai"),
                            tone=data.get("tone", "educational"),
                            length=data.get("length", 30),
                        )
                    )
                except Exception as e:
                    logger.error(f"Failed to load style config {file_path}: {e}")
        return sorted(configs, key=lambda c: c.name)

    def load_script_template(self, name: str) -> Optional[str]:
        """Load script template content."""
        # Try .md first, then .txt
        for ext in [".md", ".txt"]:
            file_path = self.template_dirs["script"] / f"{name}{ext}"
            if file_path.exists():
                return utils.read_text(file_path)
        logger.warning(f"Script template not found: {name}")
        return None

    def load_prompt_template(self, name: str) -> Optional[str]:
        """Load prompt template content."""
        # Try .txt first, then .md
        for ext in [".txt", ".md"]:
            file_path = self.template_dirs["prompt"] / f"{name}{ext}"
            if file_path.exists():
                return utils.read_text(file_path)
        logger.warning(f"Prompt template not found: {name}")
        return None

    def load_style_config(self, name: str) -> Optional[StyleConfig]:
        """Load style config."""
        if name == "default":
            # Return default config
            return StyleConfig(
                name="default",
                script_template="default",
                prompt_template="default",
                video_aspect="16:9",
                visual_source="ai",
                tone="educational",
                length=30,
            )

        file_path = self.template_dirs["style"] / f"{name}.yaml"
        if not file_path.exists():
            logger.warning(f"Style config not found: {name}")
            return None

        try:
            data = utils.load_yaml(file_path)
            return StyleConfig(
                name=data.get("name", name),
                script_template=data.get("script_template", "default"),
                prompt_template=data.get("prompt_template", "default"),
                video_aspect=data.get("video_aspect", "16:9"),
                visual_source=data.get("visual_source", "ai"),
                tone=data.get("tone", "educational"),
                length=data.get("length", 30),
            )
        except Exception as e:
            logger.error(f"Failed to parse style config {name}: {e}")
            return None

    def render_script_template(
        self, template_name: str, variables: Dict[str, str]
    ) -> str:
        """Render script template with variables."""
        template = self.load_script_template(template_name)
        if not template:
            return ""

        # Replace variables
        for key, value in variables.items():
            placeholder = "{" + key + "}"
            template = template.replace(placeholder, value)

        # Remove any remaining placeholders (optional)
        # template = re.sub(r"\{\w+\}", "[MISSING]", template)

        return template.strip()

    def render_prompt_template(
        self, template_name: str, variables: Dict[str, str]
    ) -> str:
        """Render prompt template with variables."""
        template = self.load_prompt_template(template_name)
        if not template:
            return ""

        for key, value in variables.items():
            placeholder = "{" + key + "}"
            template = template.replace(placeholder, value)

        return template.strip()

    def generate_prompts_from_script(
        self,
        script: str,
        prompt_template_name: str,
        num_prompts: int = 5,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """
        Generate visual prompts from script using LLM.
        
        Args:
            script: The video script
            prompt_template_name: Name of prompt template to use
            num_prompts: Number of prompts to generate
            context: Additional context (topic, tone, etc.)
            
        Returns:
            List of prompt strings
        """
        from .llm import generate_prompts

        # Load prompt template
        prompt_template = self.load_prompt_template(prompt_template_name)
        if not prompt_template:
            logger.warning(f"Using default prompt template (failed to load {prompt_template_name})")
            prompt_template = self.load_prompt_template("default") or ""

        # Extract template variables
        template_vars = re.findall(r"\{(\w+)\}", prompt_template)
        if not template_vars:
            # No variables in template, use as-is
            return [prompt_template] * num_prompts

        # Generate prompts using LLM
        prompts = generate_prompts(
            script=script,
            num_prompts=num_prompts,
            prompt_template=prompt_template,
            context=context or {},
        )

        return prompts[:num_prompts]

    def apply_style_config(
        self, style_config: StyleConfig, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply style config to video parameters.
        
        Returns:
            Updated parameters
        """
        updated = params.copy()
        
        # Apply style settings
        if "video_aspect" not in updated:
            updated["video_aspect"] = style_config.video_aspect
            
        if "tone" not in updated:
            updated["tone"] = style_config.tone
            
        if "length" not in updated:
            updated["length"] = style_config.length
            
        # Set templates
        updated["script_template"] = style_config.script_template
        updated["prompt_template"] = style_config.prompt_template
        
        # Visual source
        if "visual_source" not in updated:
            updated["visual_source"] = style_config.visual_source
            
        return updated


# Global instance
engine = TemplateEngine()
