"""
LLM service for script and prompt generation.
"""

import json
import re
from typing import Any, Dict, List, Optional

from loguru import logger
from openai import OpenAI

from app.config import config
from app.models.const import LLMProvider
from app.utils import utils


class LLMClient:
    """Client for LLM services."""

    def __init__(self):
        self.provider = config.llm.provider
        self.api_base = config.llm.api_base
        self.model = config.llm.model
        self.api_key = config.llm.api_key
        self.temperature = config.llm.temperature
        self.max_tokens = config.llm.max_tokens

        self._client = None
        self._setup_client()

    def _setup_client(self):
        """Setup LLM client based on provider."""
        if self.provider == LLMProvider.NINEROUTER:
            # 9router uses OpenAI-compatible API
            self._client = OpenAI(
                base_url=self.api_base,
                api_key=self.api_key or "not-needed",
                timeout=60.0,
            )
        elif self.provider == LLMProvider.OPENAI:
            self._client = OpenAI(
                base_url=config.openai.base_url if hasattr(config, "openai") else None,
                api_key=config.openai.api_key if hasattr(config, "openai") else "",
                timeout=60.0,
            )
        elif self.provider == LLMProvider.GOOGLE:
            # Google Gemini
            import google.generativeai as genai
            genai.configure(api_key=config.google.api_key if hasattr(config, "google") else "")
            self._client = genai
        elif self.provider == LLMProvider.GROQ:
            self._client = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=config.groq.api_key if hasattr(config, "groq") else "",
                timeout=60.0,
            )
        elif self.provider == LLMProvider.OLLAMA:
            self._client = OpenAI(
                base_url=config.ollama.base_url if hasattr(config, "ollama") else "http://localhost:11434/v1",
                api_key="ollama",  # not needed for Ollama
                timeout=120.0,  # Ollama can be slower
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    def _get_model(self) -> str:
        """Get model name based on provider."""
        if self.provider == LLMProvider.NINEROUTER:
            return self.model or "all-in-one"
        elif self.provider == LLMProvider.OPENAI:
            return config.openai.model if hasattr(config, "openai") else "gpt-4o-mini"
        elif self.provider == LLMProvider.GOOGLE:
            return config.google.model if hasattr(config, "google") else "gemini-2.0-flash-exp"
        elif self.provider == LLMProvider.GROQ:
            return config.groq.model if hasattr(config, "groq") else "llama3-70b-8192"
        elif self.provider == LLMProvider.OLLAMA:
            return config.ollama.model if hasattr(config, "ollama") else "llama3.1:8b"
        return self.model

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
    ) -> str:
        """Generate text from prompt."""
        logger.debug(f"Generating with {self.provider} ({self._get_model()})")

        if self.provider == LLMProvider.GOOGLE:
            return self._generate_google(prompt, system_prompt, temperature, max_tokens)

        # OpenAI-compatible providers
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = self._client.chat.completions.create(
                model=self._get_model(),
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                response_format={"type": "json_object"} if json_mode else None,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise

    def _generate_google(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate with Google Gemini."""
        try:
            model = self._client.GenerativeModel(
                model_name=self._get_model(),
                generation_config={
                    "temperature": temperature or self.temperature,
                    "max_output_tokens": max_tokens or self.max_tokens,
                },
            )

            full_prompt = ""
            if system_prompt:
                full_prompt += f"{system_prompt}\n\n"
            full_prompt += prompt

            response = model.generate_content(full_prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Google Gemini generation failed: {e}")
            raise

    def generate_script(
        self,
        video_subject: str,
        language: str = "vi",
        tone: str = "educational",
        length: int = 30,
        hook_type: str = "question",
        script_template: Optional[str] = None,
    ) -> str:
        """Generate video script."""
        system_prompt = f"""You are a professional video scriptwriter for Facebook Reels.
Create engaging, viral scripts optimized for {length}-second videos.
Tone: {tone}
Hook type: {hook_type}
Language: {language}

The script should be concise, with clear timing markers (0-3s, 3-10s, etc.).
Focus on retention hooks, clear value, and strong CTA."""

        prompt = f"""Create a Facebook Reels script about: {video_subject}

Script requirements:
- Length: {length} seconds
- Tone: {tone}
- Hook type: {hook_type}
- Target audience: general

Output format:
Start with the full script text, no additional commentary.
Script should be in {language} language.
"""

        if script_template:
            # If template is provided, we'll use templating service to fill it
            from .templating import engine
            template_vars = {
                "topic": video_subject,
                "language": language,
                "tone": tone,
                "length": str(length),
                "hook_type": hook_type,
            }
            # Let LLM fill template variables
            fill_prompt = f"""Fill in the template variables for a video script about: {video_subject}

Template variables to fill:
{json.dumps(template_vars, indent=2)}

Provide values for each variable that would create an engaging script.
Return as JSON with variable names as keys."""
            
            try:
                filled_vars = self.generate(fill_prompt, json_mode=True)
                filled_data = json.loads(filled_vars)
                template_vars.update(filled_data)
                
                # Render template
                script = engine.render_script_template(script_template, template_vars)
                if script:
                    return script
            except Exception as e:
                logger.warning(f"Failed to fill template {script_template}: {e}. Falling back to direct generation.")

        # Fallback: direct generation
        script = self.generate(prompt, system_prompt)
        return self._clean_script(script)

    def generate_prompts(
        self,
        script: str,
        num_prompts: int = 5,
        prompt_template: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Generate visual prompts from script."""
        context = context or {}
        
        system_prompt = """You are a visual director creating prompts for AI image generation.
Generate descriptive, vivid prompts that capture key moments from the script.
Each prompt should be self-contained and ready for AI image generation tools like Google Imagen, Midjourney, or Stable Diffusion.

Format each prompt as a single line with descriptive details about composition, lighting, style, and mood."""

        prompt = f"""Script:
{script}

Generate {num_prompts} visual prompts for key moments in this script.

Additional context:
{json.dumps(context, indent=2) if context else 'None'}

{'Prompt template/style: ' + prompt_template if prompt_template else ''}

Output format: Return a JSON array of prompt strings, like ["prompt 1", "prompt 2", ...]
Each prompt should be:
- 1-2 sentences max
- Descriptive and vivid
- Include visual style, composition, lighting
- No markdown, just plain text
"""

        try:
            response = self.generate(prompt, system_prompt, json_mode=True)
            data = json.loads(response)
            if isinstance(data, list):
                return [str(p).strip() for p in data[:num_prompts]]
            elif isinstance(data, dict) and "prompts" in data:
                return [str(p).strip() for p in data["prompts"][:num_prompts]]
        except Exception as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}. Trying text extraction.")

        # Fallback: extract from text
        response = self.generate(prompt, system_prompt)
        prompts = self._extract_prompts_from_text(response, num_prompts)
        return prompts

    def _extract_prompts_from_text(self, text: str, max_prompts: int) -> List[str]:
        """Extract prompts from unstructured text."""
        # Split by lines, numbers, bullets, etc.
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        
        prompts = []
        for line in lines:
            # Remove numbering, bullets, quotes
            line = re.sub(r'^[\d\.\-•\*"\'\[\]]+\s*', '', line)
            if line and len(line) > 10:  # Reasonable length
                prompts.append(line)
                if len(prompts) >= max_prompts:
                    break
        
        return prompts[:max_prompts]

    def _clean_script(self, script: str) -> str:
        """Clean script text."""
        # Remove markdown code blocks
        script = re.sub(r'```[\w]*\n', '', script)
        script = re.sub(r'\n```', '', script)
        
        # Remove excessive whitespace
        script = re.sub(r'\n\s*\n\s*\n', '\n\n', script)
        
        return script.strip()

    def generate_terms(
        self,
        video_subject: str,
        video_script: str,
        amount: int = 5,
        match_script_order: bool = False,
    ) -> List[str]:
        """Generate search terms for video materials."""
        system_prompt = """You are a video researcher generating search terms for stock footage.
Create specific, visual terms that match the content of the script.
Terms should be in English for compatibility with stock APIs like Pexels and Pixabay."""

        order_note = " in narrative order (first terms for beginning of script, later terms for end)" if match_script_order else ""
        
        prompt = f"""Script subject: {video_subject}

Script:
{video_script}

Generate {amount} search terms for stock footage{order_note}.
Each term should be:
- 1-3 words
- Visual and descriptive
- In English
- Relevant to specific moments in the script

Output format: JSON array of strings."""

        try:
            response = self.generate(prompt, system_prompt, json_mode=True)
            terms = json.loads(response)
            if isinstance(terms, list):
                return [str(t).strip() for t in terms[:amount]]
        except Exception as e:
            logger.warning(f"Failed to parse terms as JSON: {e}")
        
        # Fallback
        return [
            video_subject,
            "inspiration",
            "motivation",
            "success",
            "achievement",
        ][:amount]


# Global client instance
client = LLMClient()


# Public API functions
def generate_script(
    video_subject: str,
    language: str = "vi",
    tone: str = "educational",
    length: int = 30,
    hook_type: str = "question",
    script_template: Optional[str] = None,
) -> str:
    """Generate video script."""
    return client.generate_script(
        video_subject=video_subject,
        language=language,
        tone=tone,
        length=length,
        hook_type=hook_type,
        script_template=script_template,
    )


def generate_prompts(
    script: str,
    num_prompts: int = 5,
    prompt_template: str = "",
    context: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """Generate visual prompts from script."""
    return client.generate_prompts(
        script=script,
        num_prompts=num_prompts,
        prompt_template=prompt_template,
        context=context,
    )


def generate_terms(
    video_subject: str,
    video_script: str,
    amount: int = 5,
    match_script_order: bool = False,
) -> List[str]:
    """Generate search terms for video materials."""
    return client.generate_terms(
        video_subject=video_subject,
        video_script=video_script,
        amount=amount,
        match_script_order=match_script_order,
    )
