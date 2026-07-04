import logging
import sys

from jobindex_scraper.config import Config
from jobindex_scraper.database import Database
from jobindex_scraper.classifier import LLMClassifier
from jobindex_scraper.scraper import JobPosting

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)
log = logging.getLogger(__name__)


def _row_to_posting(row: dict) -> JobPosting:
    return JobPosting(
        external_id=row['external_id'],
        url=row['url'],
        title=row['title'],
        company=row.get('company') or '',
        location=row.get('location') or '',
        description=row.get('description') or '',
        posted_at=row.get('posted_at'),
    )


def main() -> None:
    config = Config.from_env()

    missing: list[str] = []
    if not config.supabase_url:
        missing.append('SUPABASE_URL')
    if not config.supabase_key:
        missing.append('SUPABASE_KEY')
    if not config.llm.api_key:
        missing.append('GITHUB_TOKEN')
    if not config.criteria:
        missing.append('JOB_CRITERIA')

    if missing:
        log.error(
            'Missing required config: %s. Check your .env file.',
            ', '.join(missing),
        )
        sys.exit(1)

    try:
        db = Database(config.supabase_url, config.supabase_key)
    except Exception:
        log.exception('Failed to connect to Supabase')
        sys.exit(1)

    classifier = LLMClassifier(config.llm)

    jobs = db.get_unclassified_jobs()
    log.info('Found %d unclassified jobs', len(jobs))

    classified = 0
    for row in jobs:
        try:
            posting = _row_to_posting(row)

            language = classifier.classify_language(posting)
            match = classifier.match_criteria(posting, config.criteria)

            db.insert_match(
                job_id=row['id'],
                language=language.value,
                is_match=match.is_match,
                reason=match.reason,
                criteria=config.criteria,
            )

            log.info(
                '%s | lang=%s match=%s',
                posting.title,
                language.value,
                match.is_match,
            )
            classified += 1
        except Exception:
            log.exception('Error classifying job %s', row.get('external_id', '?'))
            continue

    log.info('Done. Classified %d jobs.', classified)
