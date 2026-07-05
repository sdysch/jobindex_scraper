from datetime import UTC, datetime

from supabase import Client, create_client

from jobindex_scraper.scraper import JobPosting


class Database:
    def __init__(self, url: str, key: str) -> None:
        self.client: Client = create_client(url, key)

    def job_exists(self, external_id: str) -> bool:
        result = (
            self.client.table('jobs')
            .select('id')
            .eq('external_id', external_id)
            .limit(1)
            .execute()
        )
        return len(result.data) > 0

    def insert_job(self, job: JobPosting, search_url: str) -> dict:
        now = datetime.now(UTC).isoformat()
        data = {
            'external_id': job.external_id,
            'url': job.url,
            'title': job.title,
            'company': job.company,
            'location': job.location,
            'description': job.description,
            'search_url': search_url,
            'posted_at': job.posted_at,
            'updated_at': now,
        }

        result = (
            self.client.table('jobs').upsert(data, on_conflict='external_id').execute()
        )
        return result.data[0] if result.data else {}

    def get_unclassified_jobs(self) -> list[dict]:
        match_rows = self.client.table('matches').select('job_id').execute()
        classified_ids = [r['job_id'] for r in match_rows.data]

        query = self.client.table('jobs').select('*').order('scraped_at', desc=True)
        if classified_ids:
            query = query.not_.in_('id', classified_ids)
        result = query.execute()
        return result.data

    def insert_match(
        self,
        job_id: int,
        language: str,
        is_match: bool,
        reason: str,
        criteria: str,
    ) -> dict:
        data = {
            'job_id': job_id,
            'language': language,
            'is_match': is_match,
            'match_reason': reason,
            'criteria_used': criteria,
        }

        result = self.client.table('matches').insert(data).execute()
        return result.data[0] if result.data else {}

    def get_unnotified_matches(self) -> list[dict]:
        result = (
            self.client.table('matches')
            .select('*, jobs(*)')
            .eq('is_match', True)
            .eq('notified', False)
            .order('classified_at', desc=True)
            .execute()
        )
        return result.data

    def mark_matches_notified(self, match_ids: list[int]) -> None:
        now = datetime.now(UTC).isoformat()
        self.client.table('matches').update({'notified': True, 'notified_at': now}).in_(
            'id', match_ids
        ).execute()
