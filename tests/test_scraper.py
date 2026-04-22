import pytest
from scraper import extract_domain, normalize_url

@pytest.mark.parametrize("url, expected", [
    ("https://www.example.com/", "example.com"),
    ("http://example.com", "example.com"),
    ("https://sub.example.com", "sub.example.com"),
    ("https://www.sub.example.com", "sub.example.com"),
    ("example.com/path?query=1#frag", "example.com"),
    ("https://example.com/trailing/", "example.com"),
    ("", ""),
    ("https://example.com", "example.com"),
])
def test_extract_domain(url, expected):
    assert extract_domain(url) == expected

@pytest.mark.parametrize("url, expected", [
    ("example.com", "https://example.com"),
    ("http://example.com", "http://example.com"),
    ("https://example.com", "https://example.com"),
    ("https://example.com/", "https://example.com"),
    ("https://example.com/path/?q=1#f", "https://example.com/path/?q=1#f"),
    ("", ""),
    ("   ", ""),
    ("sub.example.com", "https://sub.example.com"),
])
def test_normalize_url(url, expected):
    assert normalize_url(url) == expected
