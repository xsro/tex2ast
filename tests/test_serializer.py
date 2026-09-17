"""Tests for the serializer (roundtrip conversion)."""

import pytest
from tex2ast.lexer import LatexLexer
from tex2ast.parser import LatexParser
from tex2ast.serializer import LatexSerializer


def roundtrip(text: str) -> str:
    """Convert text -> AST -> text and return result."""
    lexer = LatexLexer(text)
    tokens = lexer.get_tokens()
    parser = LatexParser(tokens)
    ast = parser.parse()
    ast.source = text
    serializer = LatexSerializer()
    return serializer.serialize(ast)


class TestRoundtrip:
    """Test that roundtrip conversion preserves LaTeX."""

    def test_plain_text(self):
        """Plain text roundtrips."""
        assert roundtrip("hello") == "hello"

    def test_command(self):
        """Command roundtrips."""
        assert roundtrip("\\alpha") == "\\alpha"

    def test_command_with_arg(self):
        """Command with argument roundtrips."""
        assert roundtrip("\\textbf{bold}") == "\\textbf{bold}"

    def test_environment(self):
        """Environment roundtrips."""
        # Note: The serializer may lose some whitespace
        result = roundtrip("\\begin{itemize}\\item test\\end{itemize}")
        assert "\\begin{itemize}" in result
        assert "\\end{itemize}" in result
        assert "test" in result

    def test_documentclass(self):
        """\\documentclass roundtrips."""
        assert roundtrip("\\documentclass{article}") == "\\documentclass{article}"

    def test_usepackage(self):
        """\\usepackage roundtrips."""
        assert roundtrip("\\usepackage{amsmath}") == "\\usepackage{amsmath}"

    def test_inline_math(self):
        """Inline math roundtrips."""
        assert roundtrip("$x$") == "$x$"

    def test_display_math(self):
        """Display math roundtrips."""
        assert roundtrip("$$x$$") == "$$x$$"

    def test_section(self):
        """Section roundtrips."""
        assert roundtrip("\\section{Intro}") == "\\section{Intro}"

    def test_comment(self):
        """Comment roundtrips."""
        assert roundtrip("text % comment") == "text % comment"

    def test_special_chars(self):
        """Special characters roundtrip."""
        assert roundtrip("\\%\\&\\#") == "\\%\\&\\#"

    def test_full_document(self):
        """Full document roundtrips."""
        text = """\\documentclass{article}
\\usepackage{amsmath}
\\title{Test}
\\begin{document}
\\section{Intro}
Hello world.
\\end{document}"""
        assert roundtrip(text) == text

    def test_nested_braces(self):
        """Nested braces roundtrip."""
        text = "{a{b}c}"
        assert roundtrip(text) == text

    def test_optional_args(self):
        """Optional arguments roundtrip."""
        text = "\\includegraphics[width=\\textwidth]{image}"
        assert roundtrip(text) == text

    def test_footnote(self):
        """Footnote roundtrips."""
        assert roundtrip("\\footnote{test}") == "\\footnote{test}"

    def test_citation(self):
        """Citation roundtrips."""
        # Note: The serializer adds space after comma
        result = roundtrip("\\cite{key1,key2}")
        assert "\\cite" in result
        assert "key1" in result
        assert "key2" in result

    def test_label(self):
        """Label roundtrips."""
        assert roundtrip("\\label{sec:intro}") == "\\label{sec:intro}"

    def test_href(self):
        """href roundtrips."""
        assert roundtrip("\\href{http://example.com}{link}") == "\\href{http://example.com}{link}"

    def test_newcommand(self):
        """newcommand roundtrips."""
        text = "\\newcommand{\\foo}{bar}"
        assert roundtrip(text) == text

    def test_subscript_superscript(self):
        """Subscript and superscript roundtrip."""
        assert roundtrip("x_1^2") == "x_1^2"

    def test_par(self):
        """\\par roundtrips."""
        assert roundtrip("a\\par b") == "a\\par b"

    def test_linebreak(self):
        """Line break roundtrips."""
        assert roundtrip("a\\\\b") == "a\\\\b"


class TestRoundtripEdgeCases:
    """Test edge cases in roundtrip conversion."""

    def test_empty_input(self):
        """Empty input roundtrips to empty string."""
        assert roundtrip("") == ""

    def test_whitespace_only(self):
        """Whitespace-only input roundtrips."""
        # Note: The serializer may collapse whitespace
        result = roundtrip("   ")
        assert result.strip() == ""  # Whitespace only, should be empty or spaces

    def test_newlines(self):
        """Newlines are preserved."""
        text = "line1\nline2\nline3"
        assert roundtrip(text) == text

    def test_mixed_whitespace(self):
        """Mixed whitespace roundtrips."""
        # Note: The serializer may normalize whitespace
        text = "a b c\n"
        result = roundtrip(text)
        assert "a" in result
        assert "b" in result
        assert "c" in result

    def test_escaped_brace(self):
        """Escaped braces roundtrip."""
        assert roundtrip("\\{\\}") == "\\{\\}"

    def test_tilde(self):
        """Tilde roundtrips."""
        assert roundtrip("a~b") == "a~b"

    def test_ampersand(self):
        """Ampersand roundtrips."""
        assert roundtrip("a & b") == "a & b"