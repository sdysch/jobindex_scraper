import logging
import sys

from jobindex_scraper.config import Config
from jobindex_scraper.database import Database
from jobindex_scraper.scraper import JobIndexScraper

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)
log = logging.getLogger(__name__)


def main() -> None:
    config = Config.from_env()

    missing: list[str] = []
    if not config.supabase_url:
        missing.append('SUPABASE_URL')
    if not config.supabase_key:
        missing.append('SUPABASE_KEY')
    if not config.search_urls:
        log.warning('No SEARCH_URLS configured \u2013 nothing to do')

    if missing:
        log.error(
            'Missing required config: %s. Check your .env file.',
            ', '.join(missing),
        )
        sys.exit(1)

    scraper = JobIndexScraper()

    try:
        db = Database(config.supabase_url, config.supabase_key)
    except Exception:
        log.exception('Failed to connect to Supabase')
        sys.exit(1)

    total_new = 0

    for url in config.search_urls:
        log.info('Scraping: %s', url)

        try:
            jobs = scraper.search(url)
        except Exception:
            log.exception('Failed to scrape: %s', url)
            continue

        log.info('Found %d jobs', len(jobs))

        for job in jobs:
            try:
                if db.job_exists(job.external_id):
                    continue

                db.insert_job(job, url)
                total_new += 1
                log.debug('Stored: %s %s', job.external_id, job.title)
            except Exception:
                log.exception('Error storing job: %s', job.external_id)
                continue

    log.info('Done. Stored %d new jobs.', total_new)
