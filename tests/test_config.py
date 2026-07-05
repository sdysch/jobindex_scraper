import json
from pathlib import Path

from jobindex_scraper.config import Config


class TestLoadJsonEnv:
    def test_from_single_line_env_var(self, monkeypatch):
        urls = ['https://example.com/1', 'https://example.com/2']
        monkeypatch.setenv('SEARCH_URLS', json.dumps(urls))
        result = Config._load_json_env('SEARCH_URLS', Path('.env'))
        assert result == urls

    def test_from_multi_line_env_file(self, tmp_path):
        env_file = tmp_path / '.env'
        env_file.write_text(
            'SEARCH_URLS=["https://example.com/1",\n  "https://example.com/2"\n]\n'
        )
        result = Config._load_json_env('SEARCH_URLS', env_file)
        assert result == ['https://example.com/1', 'https://example.com/2']

    def test_trailing_comma_cleaned(self, monkeypatch):
        monkeypatch.setenv('SEARCH_URLS', '["a", "b",]')
        result = Config._load_json_env('SEARCH_URLS', Path('.env'))
        assert result == ['a', 'b']

    def test_invalid_json_returns_empty(self, monkeypatch, tmp_path):
        monkeypatch.setenv('SEARCH_URLS', 'not json')
        result = Config._load_json_env('SEARCH_URLS', tmp_path / '.env')
        assert result == []
