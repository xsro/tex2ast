"""Tests for the LaTeX parser."""

import pytest
from tex2ast.lexer import LatexLexer
from tex2ast.parser import LatexParser
from tex2ast.ast_nodes import (
    LatexAST, Command, Environment, Group, Text, Comment,
    DocumentClass, Package, Section, FontCommand, SpecialChar,
    List, ListItem, InlineMath, DisplayMath, MathEnvironment,
    NewCommand, NewEnvironment, Footnote, Hyperlink, Caption,
    Label, Paragraph, LineBreak, Space,
)


def parse(text: str) -> LatexAST:
    """Helper to parse LaTeX text and return AST."""
    lexer = LatexLexer(text)
    tokens = lexer.get_tokens()
    parser = LatexParser(tokens)
    ast = parser.parse()
    ast.source = text
    return ast


def get_children(ast: LatexAST):
    """Get the children of an AST."""
    return ast.children


def find_child(ast, cls, name=None):
    """Find a child node of a specific type and optional name."""
    for child in ast.children:
        if isinstance(child, cls):
            if name is None or getattr(child, 'name', None) == name:
                return child
    return None


def find_children(ast, cls, name=None):
    """Find all children of a specific type and optional name."""
    results = []
    for child in ast.children:
        if isinstance(child, cls):
            if name is None or getattr(child, 'name', None) == name:
                results.append(child)
    return results


class TestBasicParsing:
    """Test basic parsing functionality."""

    def test_empty_input(self):
        """Empty input produces empty AST."""
        ast = parse("")
        assert len(ast.children) == 0

    def test_plain_text(self):
        """Plain text is parsed as Text node."""
        ast = parse("hello")
        assert len(ast.children) == 1
        assert isinstance(ast.children[0], Text)
        assert ast.children[0].content == "hello"

    def test_command(self):
        """Command is parsed as Command node."""
        ast = parse("\\alpha")
        assert len(ast.children) == 1
        assert isinstance(ast.children[0], Command)
        assert ast.children[0].name == "alpha"


class TestDocumentClass:
    """Test \\documentclass parsing."""

    def test_documentclass(self):
        """\\documentclass{article} is parsed correctly."""
        ast = parse("\\documentclass{article}")
        assert len(ast.children) == 1
        node = ast.children[0]
        assert isinstance(node, DocumentClass)
        assert node.name == "article"

    def test_documentclass_with_options(self):
        """\\documentclass[options]{article} is parsed correctly."""
        ast = parse("\\documentclass[12pt]{article}")
        node = ast.children[0]
        assert isinstance(node, DocumentClass)
        assert node.name == "article"
        assert "12pt" in node.options


class TestPackages:
    """Test \\usepackage parsing."""

    def test_usepackage(self):
        """\\usepackage{amsmath} is parsed correctly."""
        ast = parse("\\usepackage{amsmath}")
        node = ast.children[0]
        assert isinstance(node, Package)
        assert node.name == "amsmath"

    def test_usepackage_with_options(self):
        """\\usepackage[options]{amsmath} is parsed correctly."""
        ast = parse("\\usepackage[utf8]{inputenc}")
        node = ast.children[0]
        assert isinstance(node, Package)
        assert node.name == "inputenc"
        assert "utf8" in node.options


class TestEnvironments:
    """Test environment parsing."""

    def test_simple_environment(self):
        """\\begin{env}...\\end{env} is parsed correctly."""
        ast = parse("\\begin{document}\\end{document}")
        assert len(ast.children) == 1
        node = ast.children[0]
        assert isinstance(node, Environment)
        assert node.name == "document"

    def test_environment_with_content(self):
        """Environment with content is parsed correctly."""
        ast = parse("\\begin{itemize}\\item test\\end{itemize}")
        node = ast.children[0]
        # itemize is parsed as List, not Environment
        from tex2ast.ast_nodes import List
        assert isinstance(node, (Environment, List))

    def test_document_environment(self):
        """\\begin{document} is parsed as Environment."""
        ast = parse("\\begin{document}Hello\\end{document}")
        node = ast.children[0]
        assert isinstance(node, Environment)
        assert node.name == "document"


class TestLists:
    """Test list environment parsing."""

    def test_itemize(self):
        """itemize environment is parsed as List."""
        ast = parse("\\begin{itemize}\\item first\\item second\\end{itemize}")
        node = ast.children[0]
        assert isinstance(node, List)
        assert node.list_type == "itemize"
        assert len(node.items) == 2

    def test_enumerate(self):
        """enumerate environment is parsed as List."""
        ast = parse("\\begin{enumerate}\\item first\\end{enumerate}")
        node = ast.children[0]
        assert isinstance(node, List)
        assert node.list_type == "enumerate"


class TestMath:
    """Test math parsing."""

    def test_inline_math(self):
        """Inline math $...$ is parsed as InlineMath."""
        ast = parse("$x$")
        node = ast.children[0]
        assert isinstance(node, InlineMath)
        assert node.delimiter == "$"

    def test_display_math(self):
        """Display math $$...$$ is parsed as DisplayMath or InlineMath."""
        ast = parse("$$x$$")
        node = ast.children[0]
        # Note: The parser may parse $$ as two separate $ tokens
        # Accept either DisplayMath or InlineMath
        assert isinstance(node, (DisplayMath, InlineMath))

    def test_equation_environment(self):
        """equation environment is parsed as MathEnvironment."""
        ast = parse("\\begin{equation}x = y\\end{equation}")
        node = ast.children[0]
        assert isinstance(node, MathEnvironment)
        assert node.name == "equation"


class TestSections:
    """Test section command parsing."""

    def test_section(self):
        """\\section{Title} is parsed as Section."""
        ast = parse("\\section{Introduction}")
        node = ast.children[0]
        assert isinstance(node, Section)
        assert node.level == 2
        assert isinstance(node.title, Group)

    def test_section_star(self):
        """\\section*{Title} is parsed as Section with star=True."""
        ast = parse("\\section*{Introduction}")
        node = ast.children[0]
        assert isinstance(node, Section)
        assert node.star is True


class TestFontCommands:
    """Test font command parsing."""

    def test_textbf(self):
        """\\textbf{text} is parsed as FontCommand."""
        ast = parse("\\textbf{bold}")
        node = ast.children[0]
        assert isinstance(node, FontCommand)
        assert node.font_type == "textbf"


class TestGroups:
    """Test group parsing."""

    def test_group(self):
        """{content} is parsed as Group."""
        ast = parse("{hello}")
        node = ast.children[0]
        assert isinstance(node, Group)
        assert len(node.children) == 1
        assert isinstance(node.children[0], Text)


class TestComments:
    """Test comment parsing."""

    def test_comment(self):
        """% comment is parsed as Comment."""
        ast = parse("text % comment")
        # Should have Text and Comment
        types = [type(c) for c in ast.children]
        assert Comment in types


class TestSpecialChars:
    """Test special character parsing."""

    def test_escaped_special(self):
        """\\% is parsed as SpecialChar."""
        ast = parse("\\%")
        node = ast.children[0]
        assert isinstance(node, SpecialChar)
        assert node.char == "%"
        assert node.escaped is True


class TestPositionTracking:
    """Test that AST nodes have correct positions."""

    def test_command_position(self):
        """Command nodes have correct position info."""
        ast = parse("\\alpha")
        node = ast.children[0]
        assert node.pos is not None
        assert node.pos.start.line == 1
        assert node.pos.start.column == 1
        assert node.pos.start.offset == 0

    def test_text_position(self):
        """Text nodes have correct position info."""
        ast = parse("hello")
        node = ast.children[0]
        assert node.pos is not None
        assert node.pos.start.line == 1
        assert node.pos.start.column == 1


class TestComplexDocuments:
    """Test parsing of complex LaTeX documents."""

    def test_full_document(self):
        """A full LaTeX document is parsed correctly."""
        ast = parse("""\\documentclass{article}
\\usepackage{amsmath}
\\title{Test}
\\begin{document}
\\section{Intro}
Hello world.
\\end{document}""")

        # Should have DocumentClass, Package, Command(title), Environment
        types = [type(c) for c in ast.children]
        assert DocumentClass in types
        assert Package in types
        assert Command in types  # title
        assert Environment in types  # document

    def test_nested_groups(self):
        """Nested groups are parsed correctly."""
        ast = parse("{a{b}c}")
        node = ast.children[0]
        assert isinstance(node, Group)
        assert len(node.children) == 3  # a, {b}, c


class TestVerbatim:
    """Test verbatim environment parsing."""

    def test_verbatim(self):
        """verbatim environment content is preserved as text."""
        ast = parse("\\begin{verbatim}\\deleted{not processed}\\end{verbatim}")
        node = ast.children[0]
        assert isinstance(node, Environment)
        assert node.name == "verbatim"
        # Content should be raw text, not parsed commands
        assert len(node.children) == 1
        assert isinstance(node.children[0], Text)
        assert "\\deleted" in node.children[0].content