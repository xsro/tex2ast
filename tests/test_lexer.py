"""Tests for the LaTeX lexer."""

import pytest
from tex2ast.lexer import LatexLexer, TokenType, Token


class TestBasicTokenization:
    """Test basic tokenization of LaTeX text."""

    def test_empty_input(self):
        """Empty input produces only EOF token."""
        lexer = LatexLexer("")
        tokens = lexer.get_tokens()
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.EOF

    def test_plain_text(self):
        """Plain text is tokenized as TEXT."""
        lexer = LatexLexer("hello")
        tokens = lexer.get_tokens()
        assert len(tokens) == 2  # TEXT + EOF
        assert tokens[0].type == TokenType.TEXT
        assert tokens[0].value == "hello"
        assert tokens[1].type == TokenType.EOF

    def test_newline(self):
        """Newline is tokenized as NEWLINE."""
        lexer = LatexLexer("line1\nline2")
        tokens = lexer.get_tokens()
        types = [t.type for t in tokens]
        assert TokenType.NEWLINE in types
        assert TokenType.TEXT in types

    def test_space(self):
        """Spaces are tokenized as SPACE."""
        lexer = LatexLexer("a b c")
        tokens = lexer.get_tokens()
        types = [t.type for t in tokens]
        assert TokenType.SPACE in types


class TestCommands:
    """Test command tokenization."""

    def test_simple_command(self):
        """Simple command like \\alpha is tokenized as COMMAND."""
        lexer = LatexLexer("\\alpha")
        tokens = lexer.get_tokens()
        assert tokens[0].type == TokenType.COMMAND
        assert tokens[0].value == "\\alpha"

    def test_command_with_text(self):
        """Command followed by text."""
        lexer = LatexLexer("\\alpha + 1")
        tokens = lexer.get_tokens()
        assert tokens[0].type == TokenType.COMMAND
        assert tokens[0].value == "\\alpha"

    def test_begin_env(self):
        """\\begin{env} is tokenized as BEGIN_ENV."""
        lexer = LatexLexer("\\begin{document}")
        tokens = lexer.get_tokens()
        assert tokens[0].type == TokenType.BEGIN_ENV
        assert tokens[0].value == "document"

    def test_end_env(self):
        """\\end{env} is tokenized as END_ENV."""
        lexer = LatexLexer("\\end{document}")
        tokens = lexer.get_tokens()
        assert tokens[0].type == TokenType.END_ENV
        assert tokens[0].value == "document"

    def test_special_command(self):
        """Special commands like \\{, \\}, \\% are tokenized as COMMAND."""
        lexer = LatexLexer("\\{\\}\\%\\&")
        tokens = lexer.get_tokens()
        # Filter out EOF token
        cmd_tokens = [t for t in tokens if t.type != TokenType.EOF]
        types = [t.type for t in cmd_tokens]
        assert all(t == TokenType.COMMAND for t in types)
        assert cmd_tokens[0].value == "\\{"
        assert cmd_tokens[1].value == "\\}"
        assert cmd_tokens[2].value == "\\%"
        assert cmd_tokens[3].value == "\\&"

    def test_line_break(self):
        """\\\\ is tokenized as COMMAND."""
        lexer = LatexLexer("line1\\\\line2")
        tokens = lexer.get_tokens()
        types = [t.type for t in tokens]
        assert TokenType.COMMAND in types


class TestBraces:
    """Test brace tokenization."""

    def test_open_brace(self):
        """{ is tokenized as OPEN_BRACE."""
        lexer = LatexLexer("{")
        tokens = lexer.get_tokens()
        assert tokens[0].type == TokenType.OPEN_BRACE

    def test_close_brace(self):
        """} is tokenized as CLOSE_BRACE."""
        lexer = LatexLexer("}")
        tokens = lexer.get_tokens()
        assert tokens[0].type == TokenType.CLOSE_BRACE

    def test_open_bracket(self):
        """[ is tokenized as OPEN_BRACKET."""
        lexer = LatexLexer("[")
        tokens = lexer.get_tokens()
        assert tokens[0].type == TokenType.OPEN_BRACKET

    def test_close_bracket(self):
        """] is tokenized as CLOSE_BRACKET."""
        lexer = LatexLexer("]")
        tokens = lexer.get_tokens()
        assert tokens[0].type == TokenType.CLOSE_BRACKET


class TestMath:
    """Test math tokenization."""

    def test_inline_math(self):
        """$ is tokenized as MATH_SHIFT."""
        lexer = LatexLexer("$x$")
        tokens = lexer.get_tokens()
        types = [t.type for t in tokens]
        assert types.count(TokenType.MATH_SHIFT) == 2

    def test_display_math(self):
        """$$ is tokenized as MATH_SHIFT with value $$."""
        lexer = LatexLexer("$$x$$")
        tokens = lexer.get_tokens()
        assert tokens[0].type == TokenType.MATH_SHIFT
        assert tokens[0].value == "$$"


class TestComments:
    """Test comment tokenization."""

    def test_comment(self):
        """% is tokenized as COMMENT."""
        lexer = LatexLexer("text % comment")
        tokens = lexer.get_tokens()
        types = [t.type for t in tokens]
        assert TokenType.COMMENT in types
        comment_token = next(t for t in tokens if t.type == TokenType.COMMENT)
        assert "comment" in comment_token.value


class TestPositionTracking:
    """Test that token positions are tracked correctly."""

    def test_token_line_column(self):
        """Tokens have correct line and column."""
        lexer = LatexLexer("abc\\alpha")
        tokens = lexer.get_tokens()
        assert tokens[0].line == 1
        assert tokens[0].column == 1
        assert tokens[1].line == 1
        assert tokens[1].column == 4  # \\alpha starts at column 4

    def test_token_offset(self):
        """Tokens have correct offset."""
        lexer = LatexLexer("abc\\alpha")
        tokens = lexer.get_tokens()
        assert tokens[0].offset == 0  # "abc"
        assert tokens[1].offset == 3  # "\\alpha"

    def test_multiline_positions(self):
        """Tokens on different lines have correct line numbers."""
        lexer = LatexLexer("line1\n\\alpha")
        tokens = lexer.get_tokens()
        # Find the command token
        cmd_token = next(t for t in tokens if t.type == TokenType.COMMAND)
        assert cmd_token.line == 2


class TestSpecialTokens:
    """Test special token types."""

    def test_superscript(self):
        """^ is tokenized as SUPERSCRIPT."""
        lexer = LatexLexer("x^2")
        tokens = lexer.get_tokens()
        types = [t.type for t in tokens]
        assert TokenType.SUPERSCRIPT in types

    def test_subscript(self):
        """_ is tokenized as SUBSCRIPT."""
        lexer = LatexLexer("x_1")
        tokens = lexer.get_tokens()
        types = [t.type for t in tokens]
        assert TokenType.SUBSCRIPT in types

    def test_ampersand(self):
        """& is tokenized as AMPERSAND."""
        lexer = LatexLexer("a & b")
        tokens = lexer.get_tokens()
        types = [t.type for t in tokens]
        assert TokenType.AMPERSAND in types

    def test_tilde(self):
        """~ is tokenized as TILDE."""
        lexer = LatexLexer("a~b")
        tokens = lexer.get_tokens()
        types = [t.type for t in tokens]
        assert TokenType.TILDE in types