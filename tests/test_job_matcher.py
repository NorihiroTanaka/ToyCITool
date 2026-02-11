import pytest
from src.core.job_matcher import JobMatcher

def test_match_files_empty_patterns():
    matcher = JobMatcher()
    assert matcher.match_files([], {"file.txt"}) is False

def test_match_files_no_match():
    matcher = JobMatcher()
    assert matcher.match_files(["*.py"], {"file.txt", "image.png"}) is False

def test_match_files_match():
    matcher = JobMatcher()
    assert matcher.match_files(["*.py"], {"main.py", "image.png"}) is True

def test_match_job_config_match():
    matcher = JobMatcher()
    job_config = {"watch_files": ["src/*.py"]}
    changed_files = {"src/main.py", "readme.md"}
    assert matcher.match(job_config, changed_files) is True

def test_match_job_config_no_match():
    matcher = JobMatcher()
    job_config = {"watch_files": ["tests/*.py"]}
    changed_files = {"src/main.py", "readme.md"}
    assert matcher.match(job_config, changed_files) is False
