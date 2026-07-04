import logging
import sys

from jobindex_scraper.config import Config
from jobindex_scraper.database import Database
from jobindex_scraper.notifier import TelegramNotifier

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)
log = logging.getLogger(__name__)


def _match_to_notification(match: dict) -> dict:
    job = match.get('jobs') or {}
    return {
        'title': job.get('title', '?'),
        'url': job.get('url', ''),
        'company': job.get('company', '?'),
        'location': job.get('location', '?'),
        'language': match.get('language', '?'),
        'match_reason': match.get('match_reason', ''),
    }


def main() -> None:
    config = Config.from_env()

    missing: list[str] = []
    if not config.supabase_url:
        missing.append('SUPABASE_URL')
    if not config.supabase_key:
        missing.append('SUPABASE_KEY')
    if not config.telegram_bot_token:
        missing.append('TELEGRAM_BOT_TOKEN')
    if not config.telegram_chat_id:
        missing.append('TELEGRAM_CHAT_ID')

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

    notifier = TelegramNotifier(config.telegram_bot_token, config.telegram_chat_id)

    matches = db.get_unnotified_matches()
    log.info('Found %d unnotified matches', len(matches))

    if not matches:
        log.info('No new matches to report.')
        return

    notifications = [_match_to_notification(m) for m in matches]

    try:
        notifier.send_match_summary(notifications)
    except Exception:
        log.exception('Failed to send Telegram notification')
        sys.exit(1)

    match_ids = [m['id'] for m in matches]
    db.mark_matches_notified(match_ids)

    log.info('Done. Sent %d match notifications.', len(matches))
