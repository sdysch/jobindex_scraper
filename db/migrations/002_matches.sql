CREATE TABLE IF NOT EXISTS matches (
    id BIGSERIAL PRIMARY KEY,
    job_id BIGINT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    language TEXT,
    is_match BOOLEAN DEFAULT FALSE,
    match_reason TEXT,
    criteria_used TEXT,
    classified_at TIMESTAMPTZ DEFAULT NOW(),
    notified BOOLEAN DEFAULT FALSE,
    notified_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_matches_job_id ON matches(job_id);
CREATE INDEX IF NOT EXISTS idx_matches_is_match ON matches(is_match);
CREATE INDEX IF NOT EXISTS idx_matches_notified ON matches(notified);
