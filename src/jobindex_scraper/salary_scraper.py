import argparse
import json
import re
import time
from pathlib import Path

import httpx
import yaml

BASE_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (X11; Linux x86_64; rv:152.0) Gecko/20100101 Firefox/152.0'
    ),
    'Accept-Language': 'en-US,en;q=0.9',
}


def load_config(path: str | Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def load_slugs(path: str | Path) -> list[str]:
    slugs = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                slugs.append(line)
    return slugs


def create_client(cookies: dict | None = None) -> httpx.Client:
    client = httpx.Client(headers=BASE_HEADERS)
    if cookies:
        client.cookies.update(cookies)
    return client


def get_stash_config(client: httpx.Client, job_slug: str) -> dict:
    url = f'https://www.jobindex.dk/tjek-din-loen/{job_slug}?lang=en'
    resp = client.get(url, timeout=15)
    resp.raise_for_status()
    match = re.search(r'var Stash = (\{.*?\});', resp.text, re.DOTALL)
    if not match:
        raise ValueError(
            f'Could not find Stash config block in page for {job_slug!r}. '
            'Jobindex may have changed their frontend structure.'
        )
    return json.loads(match.group(1))


def resolve_jobtitle_id(stash: dict, job_slug: str) -> int:
    titles = stash.get('salaryindex/default', {}).get('initialJobtitles', [])
    for title in titles:
        if title.get('seo_name') == job_slug:
            return title['id']
    raise ValueError(f'Could not resolve jobtitle id for slug {job_slug!r}.')


def call_salary_api(
    client: httpx.Client,
    key: str,
    api_path: str,
    job_slug: str,
    jobtitle_id: int,
    geoarea_id: int,
    education_level: int,
) -> dict:
    api_url = f'https://www.jobindex.dk{api_path}'
    params = {
        'key': key,
        'jobtitle': jobtitle_id,
        'geoareaid': geoarea_id,
        'educationlevel': education_level,
    }
    headers = {
        **BASE_HEADERS,
        'Accept': '*/*',
        'Referer': f'https://www.jobindex.dk/tjek-din-loen/{job_slug}?lang=en&geoarea={geoarea_id}',
        'X-Requested-With': 'XMLHttpRequest',
    }
    resp = client.get(api_url, params=params, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()


def scrape_job_title(
    client: httpx.Client,
    job_slug: str,
    key: str,
    api_path: str,
    geoarea_ids: list[int],
    education_levels: list[int],
    delay: float = 1.5,
) -> list[dict]:
    stash = get_stash_config(client, job_slug)
    jobtitle_id = resolve_jobtitle_id(stash, job_slug)

    rows = []
    for geoarea_id in geoarea_ids:
        for education_level in education_levels:
            data = call_salary_api(
                client,
                key,
                api_path,
                job_slug,
                jobtitle_id,
                geoarea_id,
                education_level,
            )
            rows.append(
                {
                    'job_slug': job_slug,
                    'jobtitle_id': jobtitle_id,
                    'geoarea_id': geoarea_id,
                    'education_level': education_level,
                    'data': data,
                }
            )
            time.sleep(delay)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description='Scrape salary data from Jobindex.')
    parser.add_argument('config', type=Path, help='YAML config file path')
    parser.add_argument('slugs', type=Path, help='File with job slugs, one per line')
    args = parser.parse_args()

    config = load_config(args.config)
    slugs = load_slugs(args.slugs)

    key = config['api_key']
    api_path = config.get('api_path', '/api/salaryindex/v2/salarylevel')
    output_path = Path(config.get('output_path', 'salary_results.json'))
    geoarea_ids = config.get('geoarea_ids')
    education_levels = config.get('education_levels')
    delay = config.get('delay', 1.5)
    cookies = config.get('cookies')

    client = create_client(cookies)

    all_results = []
    for slug in slugs:
        try:
            rows = scrape_job_title(
                client,
                slug,
                key,
                api_path,
                geoarea_ids,
                education_levels,
                delay,
            )
            all_results.extend(rows)
        except Exception as e:
            print(f'  Skipped {slug!r}: {e}')
        time.sleep(2)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f'Done. {len(all_results)} data points saved to {output_path}')
