"""Tests for the regex-based remove changes functionality."""

import pytest
from pathlib import Path
from tex2ast.remove_changes import (
    process_changes, expand_and_remove_changes,
    get_changes_commands, parse_changes_config,
    _find_matching_brace, _skip_optional_arg,
    _extract_brace_content, _is_full_line_delete,
    _remove_usepackage_changes, _remove_empty_math,
    BUILTIN_DEFAULT_COMMANDS,
)


class TestProcessChanges:
    """Test the process_changes function."""

    def test_added_new_mode(self):
        """\\added{} content is kept in new mode."""
        result = process_changes("\\begin{document}\\added{new}\\end{document}", "new")
        assert "new" in result
        assert "\\added" not in result

    def test_added_old_mode(self):
        """\\added{} content is removed in old mode."""
        result = process_changes("\\begin{document}\\added{new}\\end{document}", "old")
        assert "new" not in result

    def test_deleted_new_mode(self):
        """\\deleted{} content is removed in new mode."""
        result = process_changes("\\begin{document}\\deleted{old}\\end{document}", "new")
        assert "old" not in result

    def test_deleted_old_mode(self):
        """\\deleted{} content is kept in old mode."""
        result = process_changes("\\begin{document}\\deleted{old}\\end{document}", "old")
        assert "old" in result

    def test_replaced_new_mode(self):
        """\\replaced{new}{old} uses new in new mode."""
        result = process_changes("\\begin{document}\\replaced{new}{old}\\end{document}", "new")
        assert "new" in result
        assert "old" not in result

    def test_replaced_old_mode(self):
        """\\replaced{new}{old} uses old in old mode."""
        result = process_changes("\\begin{document}\\replaced{new}{old}\\end{document}", "old")
        assert "old" in result
        assert "new" not in result

    def test_comment_always_removed(self):
        """\\comment{} is always removed."""
        result = process_changes("\\begin{document}\\comment{text}\\end{document}", "new")
        assert "text" not in result

    def test_highlight_kept(self):
        """\\highlight{} content is kept in both modes."""
        result_new = process_changes("\\begin{document}\\highlight{text}\\end{document}", "new")
        result_old = process_changes("\\begin{document}\\highlight{text}\\end{document}", "old")
        assert "text" in result_new
        assert "text" in result_old


class TestScopeRestriction:
    """Test scope restriction (only document + title)."""

    def test_changes_in_document_processed(self):
        """Changes in document are processed."""
        text = "\\begin{document}\\added{new}\\end{document}"
        result = process_changes(text, "new")
        assert "new" in result

    def test_changes_in_preamble_not_processed(self):
        """Changes in preamble (outside title) are not processed."""
        text = "\\added{preamble}\\begin{document}\\end{document}"
        result = process_changes(text, "new")
        assert "\\added" in result  # Preserved

    def test_changes_in_title_processed(self):
        """Changes in title are processed."""
        text = "\\title{\\added{New} Title}"
        result = process_changes(text, "new")
        assert "New" in result


class TestFullLineDelete:
    """Test full-line delete preservation."""

    def test_full_line_delete_new_mode(self):
        """Full-line delete in new mode leaves %."""
        text = "Before.\n\\begin{document}\n\\deleted{full line}\n\\end{document}\nAfter."
        result = process_changes(text, "new")
        assert "%" in result
        assert "full line" not in result

    def test_full_line_delete_old_mode(self):
        """Full-line delete in old mode keeps content."""
        text = "Before.\n\\deleted{full line}\nAfter."
        result = process_changes(text, "old")
        assert "full line" in result

    def test_partial_line_no_percent(self):
        """Partial-line delete does not leave %."""
        text = "\\begin{document}Before \\deleted{delete} After.\\end{document}"
        result = process_changes(text, "new")
        assert "delete" not in result


class TestHelperFunctions:
    """Test helper functions."""

    def test_find_matching_brace(self):
        """Find matching brace correctly."""
        assert _find_matching_brace("{abc}", 0) == 4
        assert _find_matching_brace("{a{b}c}", 0) == 6
        assert _find_matching_brace("{", 0) == -1

    def test_skip_optional_arg(self):
        """Skip optional argument correctly."""
        assert _skip_optional_arg("[option]", 0) == 8  # [option] has 8 chars
        assert _skip_optional_arg("text", 0) == 0

    def test_extract_brace_content(self):
        """Extract brace content correctly."""
        content, end = _extract_brace_content("{hello}", 0)
        assert content == "hello"
        assert end == 7

    def test_is_full_line_delete(self):
        """Check full-line delete correctly."""
        text = "Before.\n\\deleted{full}\nAfter."
        # Find the position of \\deleted
        start = text.index("\\deleted")
        end = start + len("\\deleted{full}")
        assert _is_full_line_delete(text, start, end) is True

    def test_is_not_full_line_delete(self):
        """Check partial-line delete correctly."""
        text = "Before \\deleted{full} After."
        start = text.index("\\deleted")
        end = start + len("\\deleted{full}")
        assert _is_full_line_delete(text, start, end) is False

    def test_remove_usepackage_changes(self):
        """Remove \\usepackage{changes} correctly."""
        text = "\\usepackage{changes}\nHello"
        result = _remove_usepackage_changes(text)
        assert "\\usepackage" not in result
        assert "Hello" in result

    def test_remove_usepackage_changes_with_options(self):
        """Remove \\usepackage[options]{changes} correctly."""
        text = "\\usepackage[utf8]{changes}\nHello"
        result = _remove_usepackage_changes(text)
        assert "\\usepackage" not in result

    def test_remove_empty_math(self):
        """Remove empty math environments."""
        text = "\\begin{document}\nbefore\n\\[\\]\nafter\n\\end{document}"
        result = _remove_empty_math(text)
        assert "\\[" not in result


class TestGetChangesCommands:
    """Test the get_changes_commands function."""

    def test_default_commands(self):
        """Default commands are returned when no config specified."""
        commands = get_changes_commands(None)
        assert len(commands) > 0
        names = [c['name'] for c in commands]
        assert '\\cancel' in names

    def test_none_commands(self):
        """Empty list returned when 'none' specified."""
        commands = get_changes_commands('none')
        assert commands == []

    def test_custom_config(self, tmp_path):
        """Custom config file is parsed correctly."""
        config = tmp_path / "config.txt"
        config.write_text("\\custom{old}\n\\another{new}\n")
        commands = get_changes_commands(str(config))
        assert len(commands) == 2
        names = [c['name'] for c in commands]
        assert '\\custom' in names
        assert '\\another' in names


class TestExpandAndRemoveChanges:
    """Test the expand_and_remove_changes function."""

    def test_single_file(self, tmp_path):
        """Process a single file without includes."""
        tex_file = tmp_path / "test.tex"
        tex_file.write_text("\\begin{document}\\added{new}\\end{document}")

        result = expand_and_remove_changes(tex_file, "new")
        assert "new" in result
        assert "\\added" not in result

    def test_with_include(self, tmp_path):
        """Process file with \\input includes."""
        main = tmp_path / "main.tex"
        included = tmp_path / "included.tex"

        main.write_text("\\begin{document}\\input{included}\\end{document}")
        included.write_text("\\added{new}")

        result = expand_and_remove_changes(main, "new")
        assert "new" in result
        assert "\\input" not in result

    def test_with_include_recursive(self, tmp_path):
        """Process file with recursive includes."""
        a = tmp_path / "a.tex"
        b = tmp_path / "b.tex"
        c = tmp_path / "c.tex"

        a.write_text("\\input{b}")
        b.write_text("\\input{c}")
        c.write_text("\\added{deep}")

        result = expand_and_remove_changes(a, "new")
        assert "deep" in result


class TestBuiltinDefaults:
    """Test built-in default commands."""

    def test_builtin_defaults_exist(self):
        """BUILTIN_DEFAULT_COMMANDS has expected entries."""
        assert len(BUILTIN_DEFAULT_COMMANDS) > 0
        names = [c['name'] for c in BUILTIN_DEFAULT_COMMANDS]
        assert '\\cancel' in names
        assert '\\tG' in names

    def test_cancel_is_delete(self):
        """\\cancel is a delete command."""
        cmd = next(c for c in BUILTIN_DEFAULT_COMMANDS if c['name'] == '\\cancel')
        assert cmd['has_old'] is True
        assert cmd['has_new'] is False