import logging

from termlint.cli import resolve_logging_level


def test_resolve_logging_level_uses_explicit_level_first():
    assert resolve_logging_level("WARNING", verbose=2, quiet=2, explicit_level="INFO") == logging.INFO


def test_resolve_logging_level_uses_quiet_over_verbose():
    assert resolve_logging_level("DEBUG", verbose=2, quiet=1, explicit_level=None) == logging.ERROR


def test_resolve_logging_level_uses_verbose_when_no_quiet():
    assert resolve_logging_level("WARNING", verbose=2, quiet=0, explicit_level=None) == logging.DEBUG


def test_resolve_logging_level_falls_back_to_config():
    assert resolve_logging_level("WARNING", verbose=0, quiet=0, explicit_level=None) == logging.WARNING
