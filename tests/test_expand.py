"""Tests for the expand functionality."""

import pytest
from pathlib import Path
from tex2ast.expand import expand_latex


class TestExpandLatex:
    """Test the expand_latex function."""

    def test_single_file_no_includes(self, tmp_path):
        """File without includes is returned as-is."""
        tex_file = tmp_path / "test.tex"
        tex_file.write_text("Hello world")

        result = expand_latex(tex_file)
        assert "Hello world" in result

    def test_input_include(self, tmp_path):
        """\\input{file} is replaced with file contents."""
        main = tmp_path / "main.tex"
        included = tmp_path / "included.tex"

        main.write_text("Before \\input{included} After")
        included.write_text("Included content")

        result = expand_latex(main)
        assert "Before" in result
        assert "After" in result
        assert "Included content" in result
        assert "\\input" not in result

    def test_include_without_extension(self, tmp_path):
        """\\input works without .tex extension."""
        main = tmp_path / "main.tex"
        included = tmp_path / "included.tex"

        main.write_text("\\input{included}")
        included.write_text("content")

        result = expand_latex(main)
        assert "content" in result

    def test_include_with_extension(self, tmp_path):
        """\\input works with .tex extension."""
        main = tmp_path / "main.tex"
        included = tmp_path / "included.tex"

        main.write_text("\\input{included.tex}")
        included.write_text("content")

        result = expand_latex(main)
        assert "content" in result

    def test_include_command(self, tmp_path):
        """\\include is replaced with \\clearpage wrappers."""
        main = tmp_path / "main.tex"
        included = tmp_path / "included.tex"

        main.write_text("\\include{included}")
        included.write_text("content")

        result = expand_latex(main)
        assert "content" in result
        assert "\\clearpage" in result

    def test_nested_includes(self, tmp_path):
        """Nested includes are expanded recursively."""
        a = tmp_path / "a.tex"
        b = tmp_path / "b.tex"
        c = tmp_path / "c.tex"

        a.write_text("A: \\input{b}")
        b.write_text("B: \\input{c}")
        c.write_text("C: content")

        result = expand_latex(a)
        assert "A:" in result
        assert "B:" in result
        assert "C:" in result
        assert "content" in result

    def test_circular_include(self, tmp_path):
        """Circular includes are detected and skipped."""
        a = tmp_path / "a.tex"
        b = tmp_path / "b.tex"

        a.write_text("A: \\input{b}")
        b.write_text("B: \\input{a}")

        result = expand_latex(a)
        # Should not infinite loop
        assert "A:" in result

    def test_missing_file(self, tmp_path):
        """Missing included file produces error comment."""
        main = tmp_path / "main.tex"
        main.write_text("\\input{nonexistent}")

        result = expand_latex(main)
        assert "not found" in result.lower() or "file not found" in result.lower()

    def test_relative_path_resolution(self, tmp_path):
        """Relative paths are resolved from main file's directory."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        main = subdir / "main.tex"
        included = subdir / "included.tex"

        main.write_text("\\input{included}")
        included.write_text("content")

        result = expand_latex(main)
        assert "content" in result

    def test_multiple_includes(self, tmp_path):
        """Multiple includes in one file are all expanded."""
        main = tmp_path / "main.tex"
        inc1 = tmp_path / "inc1.tex"
        inc2 = tmp_path / "inc2.tex"

        main.write_text("\\input{inc1}\\input{inc2}")
        inc1.write_text("first")
        inc2.write_text("second")

        result = expand_latex(main)
        assert "first" in result
        assert "second" in result

    def test_preserve_other_content(self, tmp_path):
        """Non-include content is preserved."""
        tex_file = tmp_path / "test.tex"
        tex_file.write_text("\\documentclass{article}\n\\begin{document}\nHello\n\\end{document}")

        result = expand_latex(tex_file)
        assert "\\documentclass" in result
        assert "Hello" in result
        assert "\\begin{document}" in result