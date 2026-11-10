"""Tests for the logger context fallback."""

import logging
from contextvars import Context

from graphgen.utils.log import get_current_logger, logger


def test_context_aware_logger_handles_ray_context_without_operator_context(caplog):
    """LLM Ray actors may log without inheriting an operator's ContextVar."""
    with caplog.at_level(logging.WARNING):
        Context().run(logger.warning, "empty LLM response from actor")

    assert "empty LLM response from actor" in caplog.text


def test_get_current_logger_falls_back_without_context():
    # Outside a Ray worker context no logger is set; the helper must return a
    # usable fallback instead of raising.
    fallback = get_current_logger()
    assert isinstance(fallback, logging.Logger)
    assert fallback.name == "GraphGen"
