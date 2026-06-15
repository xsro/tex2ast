"""LaTeX lexer for tokenization."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Iterator


class TokenType(Enum):
    COMMAND = auto()         # \commandname
    BEGIN_ENV = auto()       # \begin{env}
    END_ENV = auto()         # \end{env}
    OPEN_BRACE = auto()      # {
    CLOSE_BRACE = auto()     # }
    OPEN_BRACKET = auto()    # [
    CLOSE_BRACKET = auto()   # ]
    TEXT = auto()             # plain text
    COMMENT = auto()          # %...
    MATH_SHIFT = auto()      # $ or $$
    SUPERSCRIPT = auto()     # ^
    SUBSCRIPT = auto()       # _
    AMPERSAND = auto()       # &
    NEWLINE = auto()          # \n
    BACKSLASH = auto()       # \\
    TILDE = auto()            # ~
    SPACE = auto()            # spaces
    EOF = auto()              # end of file


@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    column: int


class LatexLexer:
    """LaTeX lexer that tokenizes input text."""

    SPECIAL_CHARS = set('#$%&\\^_{}~[]')

    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: list[Token] = []
        self._tokenize()

    def _tokenize(self) -> None:
        """Tokenize the input text."""
        while self.pos < len(self.text):
            char = self.text[self.pos]

            if char == '\\':
                self._read_command_or_special()
            elif char == '%':
                self._read_comment()
            elif char == '{':
                self._add_token(TokenType.OPEN_BRACE, '{')
                self._advance()
            elif char == '}':
                self._add_token(TokenType.CLOSE_BRACE, '}')
                self._advance()
            elif char == '[':
                self._add_token(TokenType.OPEN_BRACKET, '[')
                self._advance()
            elif char == ']':
                self._add_token(TokenType.CLOSE_BRACKET, ']')
                self._advance()
            elif char == '$':
                self._read_math_shift()
            elif char == '^':
                self._add_token(TokenType.SUPERSCRIPT, '^')
                self._advance()
            elif char == '_':
                self._add_token(TokenType.SUBSCRIPT, '_')
                self._advance()
            elif char == '&':
                self._add_token(TokenType.AMPERSAND, '&')
                self._advance()
            elif char == '~':
                self._add_token(TokenType.TILDE, '~')
                self._advance()
            elif char == '#':
                self._add_token(TokenType.TEXT, '#')
                self._advance()
            elif char == '\n':
                self._add_token(TokenType.NEWLINE, '\n')
                self._advance()
                self.line += 1
                self.column = 1
            elif char.isspace():
                self._read_space()
            else:
                self._read_text()

        self._add_token(TokenType.EOF, '')

    def _advance(self) -> None:
        """Move to next character."""
        self.pos += 1
        self.column += 1

    def _peek(self, offset: int = 0) -> str:
        """Peek at character at current position + offset."""
        pos = self.pos + offset
        if pos < len(self.text):
            return self.text[pos]
        return ''

    def _add_token(self, type: TokenType, value: str) -> None:
        """Add a token to the token list."""
        self.tokens.append(Token(type, value, self.line, self.column))

    def _read_command_or_special(self) -> None:
        """Read a command or special character."""
        start_line = self.line
        start_col = self.column

        # Skip the backslash
        self._advance()

        if self.pos >= len(self.text):
            self._add_token(TokenType.BACKSLASH, '\\')
            return

        char = self._peek()

        # Special characters
        if char in '#$%&\\^_{}~':
            self._add_token(TokenType.COMMAND, '\\' + char)
            self._advance()
            return

        # Line break \\
        if char == '\\':
            self._advance()
            if self._peek() == '\n':
                self._add_token(TokenType.COMMAND, '\\\\')
                self._advance()
                self.line += 1
                self.column = 1
            else:
                self._add_token(TokenType.COMMAND, '\\\\')
            return

        # Regular command
        if char.isalpha() or char == '@':
            cmd_start = self.pos
            while self.pos < len(self.text) and (self._peek().isalpha() or self._peek() == '@'):
                self._advance()
            command = self.text[cmd_start:self.pos]

            # Check if this is \begin or \end
            if command == 'begin':
                self._skip_spaces()
                if self._peek() == '{':
                    self._advance()  # skip {
                    env_name = self._read_until('}')
                    self._advance()  # skip }
                    self._add_token(TokenType.BEGIN_ENV, env_name)
                    return
            elif command == 'end':
                self._skip_spaces()
                if self._peek() == '{':
                    self._advance()  # skip {
                    env_name = self._read_until('}')
                    self._advance()  # skip }
                    self._add_token(TokenType.END_ENV, env_name)
                    return

            self._add_token(TokenType.COMMAND, '\\' + command)
            return

        # Single non-alpha character command (like \, \; \! etc.)
        self._add_token(TokenType.COMMAND, '\\' + char)
        self._advance()

    def _read_comment(self) -> None:
        """Read a comment until end of line."""
        start = self.pos
        while self.pos < len(self.text) and self.text[self.pos] != '\n':
            self._advance()
        comment = self.text[start:self.pos]
        self._add_token(TokenType.COMMENT, comment)

    def _read_math_shift(self) -> None:
        """Read $ or $$."""
        self._advance()
        if self._peek() == '$':
            self._advance()
            self._add_token(TokenType.MATH_SHIFT, '$$')
        else:
            self._add_token(TokenType.MATH_SHIFT, '$')

    def _read_space(self) -> None:
        """Read whitespace (not newline)."""
        start = self.pos
        while self.pos < len(self.text) and self.text[self.pos].isspace() and self.text[self.pos] != '\n':
            self._advance()
        space = self.text[start:self.pos]
        if space:
            self._add_token(TokenType.SPACE, space)

    def _read_text(self) -> None:
        """Read plain text until special character."""
        start = self.pos
        while self.pos < len(self.text) and not self._is_special(self.text[self.pos]):
            self._advance()
        text = self.text[start:self.pos]
        if text:
            self._add_token(TokenType.TEXT, text)

    def _is_special(self, char: str) -> bool:
        """Check if character is special."""
        return char in self.SPECIAL_CHARS or char.isspace()

    def _skip_spaces(self) -> None:
        """Skip spaces (not newlines)."""
        while self.pos < len(self.text) and self.text[self.pos] == ' ':
            self._advance()

    def _read_until(self, char: str) -> str:
        """Read until specific character."""
        start = self.pos
        while self.pos < len(self.text) and self.text[self.pos] != char:
            if self.text[self.pos] == '\n':
                self.line += 1
                self.column = 1
            self._advance()
        return self.text[start:self.pos]

    def get_tokens(self) -> list[Token]:
        """Return all tokens."""
        return self.tokens
