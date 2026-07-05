import json
import re
import time
from dataclasses import dataclass
from enum import Enum

import httpx

from jobindex_scraper.config import LLMConfig
from jobindex_scraper.scraper import JobPosting


class Language(Enum):
    ENGLISH = 'english'
    DANISH = 'danish'
    UNKNOWN = 'unknown'


@dataclass
class MatchResult:
    is_match: bool
    reason: str


LANGUAGE_PROMPT = """You are a language classifier for job postings.
Determine whether the posting is written in English or Danish.

Respond with JSON: {"language": "english" | "danish" | "unknown"}"""

MATCH_PROMPT = """You are a job matching classifier. Determine whether the
job posting matches the user's search criteria.

Respond with JSON: {"is_match": true | false, "reason": "..."}"""


def _parse_json(content: str) -> dict:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            return json.loads(match.group())
    return {}


class LLMClassifier:
    def __init__(self, config: LLMConfig) -> None:
        self.api_key = config.api_key
        self.model = config.model
        self.base_url = config.base_url.rstrip('/')

    def _call(self, system_prompt: str, user_prompt: str) -> dict:
        for attempt in range(5):
            response = httpx.post(
                f'{self.base_url}/chat/completions',
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': self.model,
                    'messages': [
                        {'role': 'system', 'content': system_prompt},
                        {'role': 'user', 'content': user_prompt},
                    ],
                    'response_format': {'type': 'json_object'},
                    'temperature': 0.1,
                    'max_tokens': 300,
                },
                timeout=30.0,
            )

            if response.status_code == 429:
                wait = 2**attempt
                time.sleep(wait)
                continue

            response.raise_for_status()
            content = response.json()['choices'][0]['message']['content'] or ''
            return _parse_json(content)

        response.raise_for_status()
        return {}

    def classify_language(self, job: JobPosting) -> Language:
        result = self._call(
            LANGUAGE_PROMPT,
            f"""Job posting:
Title: {job.title}
Company: {job.company}
Location: {job.location}
Description:
{job.description[:3000]}""",
        )
        try:
            return Language(result.get('language', 'unknown'))
        except ValueError:
            return Language.UNKNOWN

    def match_criteria(self, job: JobPosting, criteria: str) -> MatchResult:
        result = self._call(
            MATCH_PROMPT,
            f"""Job posting:
Title: {job.title}
Company: {job.company}
Location: {job.location}
Description:
{job.description[:3000]}

User's search criteria:
{criteria}""",
        )
        return MatchResult(
            is_match=bool(result.get('is_match', False)),
            reason=result.get('reason', '') or '',
        )
