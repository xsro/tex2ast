"""Shared fixtures for tests."""

import pytest
from pathlib import Path


@pytest.fixture
def tmp_tex_file(tmp_path):
    """Create a temporary .tex file."""
    def _create(name: str, content: str) -> Path:
        path = tmp_path / name
        path.write_text(content, encoding='utf-8')
        return path
    return _create