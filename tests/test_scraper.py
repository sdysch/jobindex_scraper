from jobindex_scraper.scraper import JobIndexScraper, JobPosting


class TestExtractTextFromHtml:
    def test_strips_html_tags(self):
        html = '<div>Hello world</div>'
        result = JobIndexScraper._extract_text_from_html(html)
        assert result == 'Hello world'

    def test_removes_script_and_style(self):
        html = '<div>Text<script>alert(1)</script><style>.cls{}</style></div>'
        result = JobIndexScraper._extract_text_from_html(html)
        assert result == 'Text'

    def test_handles_empty_string(self):
        assert JobIndexScraper._extract_text_from_html('') == ''

    def test_preserves_newlines(self):
        html = '<p>Line 1</p><p>Line 2</p>'
        result = JobIndexScraper._extract_text_from_html(html)
        assert result == 'Line 1\nLine 2'


class TestParseJob:
    scraper = JobIndexScraper()

    def test_parse_minimal(self):
        data = {
            'tid': 'h1234567',
            'share_url': '/job/something',
            'headline': 'Software Engineer',
            'companytext': 'Acme Corp',
            'area': 'Copenhagen',
            'html': '<p>Great job</p>',
        }
        job = self.scraper._parse_job(data)
        assert isinstance(job, JobPosting)
        assert job.external_id == '1234567'
        assert 'jobindex.dk/job/something' in job.url
        assert job.title == 'Software Engineer'
        assert job.company == 'Acme Corp'
        assert job.location == 'Copenhagen'
        assert job.description == 'Great job'
        assert job.posted_at is None

    def test_parse_with_posted_date(self):
        data = {
            'tid': 'h7654321',
            'share_url': 'https://www.jobindex.dk/job/other',
            'headline': 'Data Scientist',
            'companytext': 'Beta Inc',
            'area': 'Aarhus',
            'html': '<p>Data job</p>',
            'firstdate': '2026-07-01',
        }
        job = self.scraper._parse_job(data)
        assert job.external_id == '7654321'
        assert job.url == 'https://www.jobindex.dk/job/other'
        assert job.posted_at == '2026-07-01'

    def test_parse_handles_missing_fields(self):
        data = {'tid': 'h999'}
        job = self.scraper._parse_job(data)
        assert job.external_id == '999'
        assert job.title == ''
        assert job.company == ''
        assert job.location == ''
        assert job.description == ''
