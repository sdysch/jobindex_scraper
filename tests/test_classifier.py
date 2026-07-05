from jobindex_scraper.classifier import Language, MatchResult, _parse_json


class TestParseJson:
    def test_valid_json(self):
        assert _parse_json('{"a": 1}') == {'a': 1}

    def test_extra_text_before_after(self):
        result = _parse_json('Some text\n{"a": 1}\ntrailing')
        assert result == {'a': 1}

    def test_invalid_no_braces(self):
        assert _parse_json('not json') == {}

    def test_empty_string(self):
        assert _parse_json('') == {}
