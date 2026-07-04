import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from bs4 import BeautifulSoup


STASH_PATTERN = re.compile(r'var Stash = ({.*?});', re.DOTALL)


@dataclass
class JobPosting:
    external_id: str
    url: str
    title: str
    company: str
    location: str
    description: str
    posted_at: Optional[str] = None
    scraped_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'da-DK,da;q=0.9,en;q=0.8',
}


class JobIndexScraper:
    BASE_URL = 'https://www.jobindex.dk'

    def __init__(self) -> None:
        self.client = httpx.Client(
            headers=HEADERS,
            follow_redirects=True,
            timeout=30.0,
        )

    def search(self, url: str) -> list[JobPosting]:
        response = self.client.get(url)
        response.raise_for_status()

        match = STASH_PATTERN.search(response.text)
        if not match:
            return []

        stash: dict[str, Any] = json.loads(match.group(1))
        results: list[dict] = (
            stash
            .get('jobsearch/result_app', {})
            .get('storeData', {})
            .get('searchResponse', {})
            .get('results', [])
        )

        return [self._parse_job(j) for j in results if j.get('tid')]

    def _parse_job(self, data: dict) -> JobPosting:
        tid: str = data['tid']  # e.g. "h1678430"
        external_id = tid.lstrip('h')

        share_url = data.get('share_url', '')
        job_url = (
            share_url
            if share_url.startswith('http')
            else f'{self.BASE_URL}{share_url}'
        )

        title = data.get('headline') or ''
        company = data.get('companytext') or ''
        location = data.get('area') or ''

        firstdate = data.get('firstdate')  # e.g. "2026-06-30"

        html = data.get('html') or ''
        description = self._extract_text_from_html(html)

        return JobPosting(
            external_id=external_id,
            url=job_url,
            title=title,
            company=company,
            location=location,
            description=description,
            posted_at=firstdate,
        )

    def fetch_description(self, url: str) -> str:
        response = self.client.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'lxml')
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'noscript']):
            tag.decompose()

        body = soup.find('body')
        if not body:
            return ''

        lines = body.get_text(strip=True, separator='\n').split('\n')
        meaningful = [l.strip() for l in lines if len(l.strip()) > 40]
        return '\n'.join(meaningful)

    @staticmethod
    def _extract_text_from_html(html: str) -> str:
        soup = BeautifulSoup(html, 'lxml')
        for tag in soup(['script', 'style', 'nav', 'header', 'footer']):
            tag.decompose()
        return soup.get_text(strip=True, separator='\n')
