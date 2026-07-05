import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import dotenv

GITHUB_MODELS_URL = 'https://models.inference.ai.azure.com'


@dataclass
class LLMConfig:
    api_key: str
    model: str = 'gpt-4o-mini'
    base_url: str = GITHUB_MODELS_URL


@dataclass
class Config:
    supabase_url: str
    supabase_key: str
    telegram_bot_token: str
    telegram_chat_id: str
    llm: LLMConfig
    criteria: str
    search_urls: list[str] = field(default_factory=list)

    @classmethod
    def from_env(cls, env_path: Path | None = None) -> 'Config':
        env_file = env_path or Path('.env')
        dotenv.load_dotenv(dotenv_path=env_file)

        search_urls = cls._load_json_env('SEARCH_URLS', env_file)

        return cls(
            supabase_url=os.getenv('SUPABASE_URL', ''),
            supabase_key=os.getenv('SUPABASE_KEY', ''),
            telegram_bot_token=os.getenv('TELEGRAM_BOT_TOKEN', ''),
            telegram_chat_id=os.getenv('TELEGRAM_CHAT_ID', ''),
            llm=LLMConfig(
                api_key=os.getenv('GITHUB_TOKEN', ''),
                model=os.getenv('LLM_MODEL', 'gpt-4o-mini'),
                base_url=os.getenv('LLM_BASE_URL', GITHUB_MODELS_URL),
            ),
            criteria=os.getenv('JOB_CRITERIA', ''),
            search_urls=search_urls,
        )

    @staticmethod
    def _load_json_env(key: str, env_path: Path) -> list[str]:
        raw = os.getenv(key, '')
        if raw:
            cleaned = re.sub(r',\s*([}\]])', r'\1', raw)
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass

        if env_path.is_file():
            prefix = f'{key}='
            lines = env_path.read_text().splitlines()
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith(prefix):
                    parts = [stripped[len(prefix) :]]
                    depth = parts[0].count('[') - parts[0].count(']')
                    for next_line in lines[i + 1 :]:
                        parts.append(next_line)
                        depth += next_line.count('[') - next_line.count(']')
                        if depth <= 0:
                            break
                    raw = ''.join(parts).strip()
                    if not raw:
                        return []
                    raw = re.sub(r',\s*([}\]])', r'\1', raw)
                    return json.loads(raw)

        return []

    # ... rest of config
