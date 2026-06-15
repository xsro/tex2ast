"""LaTeX parser for AST generation."""

from typing import Optional
from .lexer import LatexLexer, Token, TokenType
from .ast_nodes import *


class LatexParser:
    """LaTeX parser that generates AST from tokens."""

    SECTION_LEVELS = {
        'part': 0, 'chapter': 1, 'section': 2, 'subsection': 3,
        'subsubsection': 4, 'paragraph': 5, 'subparagraph': 6,
    }

    MATH_ENVS = {
        'equation', 'equation*', 'align', 'align*', 'alignat', 'alignat*',
        'flalign', 'flalign*', 'gather', 'gather*', 'multline', 'multline*',
        'eqnarray', 'eqnarray*', 'math', 'displaymath', 'array',
        'split', 'cases', 'dcases', 'rcases',
        'matrix', 'pmatrix', 'bmatrix', 'Bmatrix', 'vmatrix', 'Vmatrix',
        'smallmatrix',
    }

    VERBATIM_ENVS = {
        'verbatim', 'verbatim*', 'lstlisting', 'lstlisting*',
        'minted', 'algorithmic', 'algorithm',
    }

    LIST_ENVS = {'itemize', 'enumerate', 'description', 'list'}
    FLOAT_ENVS = {'figure', 'figure*', 'table', 'table*'}
    TABLE_ENVS = {'tabular', 'tabular*', 'tabularx', 'longtable', 'array'}

    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0
        self.ast = LatexAST()

    def parse(self) -> LatexAST:
        """Parse tokens into AST."""
        self.ast.children = self._parse_until_eof()
        return self.ast

    def _cur_pos(self) -> SourcePos:
        """Get current source position."""
        tok = self._current()
        return SourcePos(line=tok.line, column=tok.column, offset=self.pos)

    def _make_range(self, start: SourcePos) -> SourceRange:
        """Make a source range from start to current position."""
        end = self._cur_pos()
        return SourceRange(start=start, end=end)

    def _current(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return Token(TokenType.EOF, '', 0, 0)

    def _peek(self, offset: int = 0) -> Token:
        pos = self.pos + offset
        if pos < len(self.tokens):
            return self.tokens[pos]
        return Token(TokenType.EOF, '', 0, 0)

    def _advance(self) -> Token:
        token = self._current()
        self.pos += 1
        return token

    def _expect(self, type: TokenType) -> Token:
        token = self._current()
        if token.type != type:
            raise SyntaxError(f"Expected {type}, got {token.type} at line {token.line}")
        return self._advance()

    def _skip_spaces_and_newlines(self) -> None:
        while self._current().type in (TokenType.SPACE, TokenType.NEWLINE):
            self._advance()

    def _skip_spaces(self) -> None:
        while self._current().type == TokenType.SPACE:
            self._advance()

    def _parse_until_eof(self) -> list[ASTNode]:
        nodes = []
        while self._current().type != TokenType.EOF:
            prev_pos = self.pos
            node = self._parse_node()
            if node:
                nodes.append(node)
            if self.pos == prev_pos and self._current().type != TokenType.EOF:
                self._advance()
        return nodes

    def _parse_node(self) -> Optional[ASTNode]:
        token = self._current()

        if token.type == TokenType.EOF:
            return None

        if token.type == TokenType.COMMENT:
            return self._parse_comment()

        if token.type == TokenType.COMMAND:
            return self._parse_command()

        if token.type == TokenType.BEGIN_ENV:
            return self._parse_environment()

        if token.type == TokenType.OPEN_BRACE:
            return self._parse_group()

        if token.type == TokenType.MATH_SHIFT:
            return self._parse_math()

        if token.type == TokenType.TEXT:
            return self._parse_text()

        if token.type == TokenType.SPACE:
            start = self._cur_pos()
            self._advance()
            return Text(' ', pos=self._make_range(start))

        if token.type == TokenType.NEWLINE:
            start = self._cur_pos()
            self._advance()
            return Text('\n', pos=self._make_range(start))

        if token.type == TokenType.SUPERSCRIPT:
            return self._parse_superscript()

        if token.type == TokenType.SUBSCRIPT:
            return self._parse_subscript()

        if token.type == TokenType.AMPERSAND:
            start = self._cur_pos()
            self._advance()
            return SpecialChar('&', pos=self._make_range(start))

        if token.type == TokenType.TILDE:
            start = self._cur_pos()
            self._advance()
            return SpecialChar('~', pos=self._make_range(start))

        if token.type == TokenType.OPEN_BRACKET:
            return self._parse_optional_group()

        self._advance()
        return None

    def _parse_comment(self) -> Comment:
        start = self._cur_pos()
        token = self._advance()
        return Comment(token.value, pos=self._make_range(start))

    def _parse_text(self) -> Text:
        start = self._cur_pos()
        token = self._advance()
        return Text(token.value, pos=self._make_range(start))

    def _parse_group(self) -> Group:
        start = self._cur_pos()
        self._advance()  # skip {
        children = []
        while self._current().type != TokenType.CLOSE_BRACE and self._current().type != TokenType.EOF:
            prev_pos = self.pos
            node = self._parse_node()
            if node:
                children.append(node)
            if self.pos == prev_pos and self._current().type not in (TokenType.CLOSE_BRACE, TokenType.EOF):
                self._advance()
        if self._current().type == TokenType.CLOSE_BRACE:
            self._advance()  # skip }
        return Group(children, pos=self._make_range(start))

    def _parse_optional_group(self) -> OptionalGroup:
        start = self._cur_pos()
        self._advance()  # skip [
        children = []
        while self._current().type != TokenType.CLOSE_BRACKET and self._current().type != TokenType.EOF:
            prev_pos = self.pos
            node = self._parse_node()
            if node:
                children.append(node)
            if self.pos == prev_pos and self._current().type not in (TokenType.CLOSE_BRACKET, TokenType.EOF):
                self._advance()
        if self._current().type == TokenType.CLOSE_BRACKET:
            self._advance()  # skip ]
        return OptionalGroup(children, pos=self._make_range(start))

    def _parse_command(self) -> ASTNode:
        start = self._cur_pos()
        token = self._advance()
        cmd_name = token.value

        if cmd_name.startswith('\\'):
            cmd_name = cmd_name[1:]

        if cmd_name in self.SECTION_LEVELS:
            return self._parse_section(cmd_name, start)

        if cmd_name in ('textbf', 'textit', 'texttt', 'textsl', 'textsc',
                        'textrm', 'textsf', 'underline', 'emph', 'text'):
            return self._parse_font_command(cmd_name, start)

        if cmd_name in ('ref', 'pageref', 'eqref', 'autoref', 'nameref'):
            return self._parse_reference(cmd_name, start)

        if cmd_name == 'cite':
            return self._parse_citation(start)

        if cmd_name == 'footnote':
            return self._parse_footnote(start)

        if cmd_name in ('href', 'url', 'nolinkurl'):
            return self._parse_hyperlink(cmd_name, start)

        if cmd_name == 'includegraphics':
            return self._parse_graphics(start)

        if cmd_name == 'caption':
            return self._parse_caption(start)

        if cmd_name == 'label':
            return self._parse_label(start)

        if cmd_name in ('newcommand', 'renewcommand', 'NewDocumentCommand'):
            return self._parse_new_command(cmd_name, start)

        if cmd_name in ('newenvironment', 'renewenvironment', 'NewDocumentEnvironment'):
            return self._parse_new_environment(cmd_name, start)

        if cmd_name == 'usepackage':
            return self._parse_usepackage(start)

        if cmd_name == 'documentclass':
            return self._parse_documentclass(start)

        if cmd_name in ('hspace', 'vspace', 'hfill', 'vfill'):
            return self._parse_space(cmd_name, start)

        if cmd_name in ('item',):
            return self._parse_item(start)

        if cmd_name == 'verb':
            return self._parse_verb(start)

        if len(cmd_name) == 1 and cmd_name in '#$%&\\^_{}~':
            return SpecialChar(cmd_name, escaped=True, pos=self._make_range(start))

        if cmd_name == '\\':
            return LineBreak(pos=self._make_range(start))

        if cmd_name == 'par':
            return Paragraph(pos=self._make_range(start))

        return self._parse_regular_command(cmd_name, start)

    def _parse_regular_command(self, cmd_name: str, start: SourcePos) -> Command:
        star = False
        if self._current().type == TokenType.TEXT and self._current().value == '*':
            self._advance()
            star = True

        optional_args = []
        required_args = []

        while self._current().type == TokenType.OPEN_BRACKET:
            optional_args.append(self._parse_optional_group())

        while self._current().type == TokenType.OPEN_BRACE:
            required_args.append(self._parse_group())

        return Command(name=cmd_name, arguments=required_args,
                       optional_arguments=optional_args, star=star,
                       pos=self._make_range(start))

    def _parse_section(self, cmd_name: str, start: SourcePos) -> Section:
        star = False
        if self._current().type == TokenType.TEXT and self._current().value == '*':
            self._advance()
            star = True

        self._skip_spaces()
        title = self._parse_group()

        return Section(level=self.SECTION_LEVELS[cmd_name], title=title,
                       star=star, pos=self._make_range(start))

    def _parse_font_command(self, cmd_name: str, start: SourcePos) -> FontCommand:
        self._skip_spaces()
        content = self._parse_group()
        return FontCommand(font_type=cmd_name, content=content, pos=self._make_range(start))

    def _parse_reference(self, cmd_name: str, start: SourcePos) -> Reference:
        self._skip_spaces()
        self._expect(TokenType.OPEN_BRACE)
        label = self._read_until_close_brace()
        return Reference(ref_type=cmd_name, label=label, pos=self._make_range(start))

    def _parse_citation(self, start: SourcePos) -> Citation:
        optional = None
        if self._current().type == TokenType.OPEN_BRACKET:
            optional_group = self._parse_optional_group()
            optional = self._extract_text(optional_group.children)

        self._skip_spaces()
        self._expect(TokenType.OPEN_BRACE)
        keys_text = self._read_until_close_brace()
        keys = [k.strip() for k in keys_text.split(',')]

        return Citation(keys=keys, optional=optional, pos=self._make_range(start))

    def _parse_footnote(self, start: SourcePos) -> Footnote:
        self._skip_spaces()
        content = self._parse_group()
        return Footnote(content=content, pos=self._make_range(start))

    def _parse_hyperlink(self, cmd_name: str, start: SourcePos) -> Hyperlink:
        self._skip_spaces()
        self._expect(TokenType.OPEN_BRACE)
        url = self._read_until_close_brace()

        text = None
        if cmd_name == 'href' and self._current().type == TokenType.OPEN_BRACE:
            text = self._parse_group()

        return Hyperlink(url=url, text=text, href_type=cmd_name, pos=self._make_range(start))

    def _parse_graphics(self, start: SourcePos) -> Graphics:
        options = []
        if self._current().type == TokenType.OPEN_BRACKET:
            options.append(self._parse_optional_group())

        self._skip_spaces()
        self._expect(TokenType.OPEN_BRACE)
        filename = self._read_until_close_brace()

        return Graphics(filename=filename, options=options, pos=self._make_range(start))

    def _parse_caption(self, start: SourcePos) -> Caption:
        short_caption = None
        if self._current().type == TokenType.OPEN_BRACKET:
            short_caption = self._parse_optional_group()

        self._skip_spaces()
        content = self._parse_group()

        return Caption(content=content, short_caption=short_caption, pos=self._make_range(start))

    def _parse_label(self, start: SourcePos) -> Label:
        self._skip_spaces()
        self._expect(TokenType.OPEN_BRACE)
        name = self._read_until_close_brace()
        return Label(name=name, pos=self._make_range(start))

    def _parse_new_command(self, cmd_name: str, start: SourcePos) -> NewCommand:
        self._skip_spaces()
        self._expect(TokenType.OPEN_BRACE)
        name = self._read_until_close_brace()

        num_args = 0
        default = None

        if self._current().type == TokenType.OPEN_BRACKET:
            num_args_group = self._parse_optional_group()
            num_args = int(self._extract_text(num_args_group.children).strip())

        if self._current().type == TokenType.OPEN_BRACKET:
            default = self._parse_optional_group()

        self._skip_spaces()
        definition = self._parse_group()

        return NewCommand(name=name, definition=definition, num_args=num_args,
                          default=default, pos=self._make_range(start))

    def _parse_new_environment(self, cmd_name: str, start: SourcePos) -> NewEnvironment:
        self._skip_spaces()
        self._expect(TokenType.OPEN_BRACE)
        name = self._read_until_close_brace()

        num_args = 0
        default = None

        if self._current().type == TokenType.OPEN_BRACKET:
            num_args_group = self._parse_optional_group()
            num_args = int(self._extract_text(num_args_group.children).strip())

        if self._current().type == TokenType.OPEN_BRACKET:
            default = self._parse_optional_group()

        self._skip_spaces()
        before = self._parse_group()
        self._skip_spaces()
        after = self._parse_group()

        return NewEnvironment(name=name, before=before, after=after,
                              num_args=num_args, default=default,
                              pos=self._make_range(start))

    def _parse_usepackage(self, start: SourcePos) -> Package:
        options = []
        if self._current().type == TokenType.OPEN_BRACKET:
            opt_group = self._parse_optional_group()
            opt_text = self._extract_text(opt_group.children)
            options = [o.strip() for o in opt_text.split(',')]

        self._skip_spaces()
        self._expect(TokenType.OPEN_BRACE)
        name = self._read_until_close_brace()

        return Package(name=name, options=options, pos=self._make_range(start))

    def _parse_documentclass(self, start: SourcePos) -> DocumentClass:
        options = []
        if self._current().type == TokenType.OPEN_BRACKET:
            opt_group = self._parse_optional_group()
            opt_text = self._extract_text(opt_group.children)
            options = [o.strip() for o in opt_text.split(',')]

        self._skip_spaces()
        self._expect(TokenType.OPEN_BRACE)
        name = self._read_until_close_brace()

        return DocumentClass(name=name, options=options, pos=self._make_range(start))

    def _parse_space(self, cmd_name: str, start: SourcePos) -> Space:
        length = None
        if cmd_name in ('hspace', 'vspace') and self._current().type == TokenType.OPEN_BRACE:
            self._advance()
            length_text = self._read_until_close_brace()
            length = self._parse_length(length_text)

        return Space(space_type=cmd_name, length=length, pos=self._make_range(start))

    def _parse_item(self, start: SourcePos) -> ListItem:
        label = None
        if self._current().type == TokenType.OPEN_BRACKET:
            label = self._parse_optional_group()

        self._skip_spaces()
        children = []
        while self._current().type not in (TokenType.COMMAND, TokenType.BEGIN_ENV, TokenType.END_ENV, TokenType.EOF):
            if self._current().type == TokenType.COMMAND and self._current().value == '\\item':
                break
            node = self._parse_node()
            if node:
                children.append(node)

        return ListItem(children=children, label=label, pos=self._make_range(start))

    def _parse_verb(self, start: SourcePos) -> Text:
        raw_parts = []
        while self._current().type == TokenType.SPACE:
            raw_parts.append(self._current().value)
            self._advance()

        if self._current().type == TokenType.EOF:
            return Text('', pos=self._make_range(start))

        delimiter = self._current().value
        self._advance()

        content_parts = []
        while self._current().type != TokenType.EOF:
            token = self._current()
            if token.type == TokenType.TEXT and delimiter in token.value:
                idx = token.value.index(delimiter)
                content_parts.append(token.value[:idx])
                self._advance()
                break
            elif token.value == delimiter:
                self._advance()
                break
            else:
                content_parts.append(token.value)
                self._advance()

        return Text(''.join(content_parts), pos=self._make_range(start))

    def _parse_math(self) -> ASTNode:
        start = self._cur_pos()
        token = self._advance()

        if token.value == '$':
            if self._current().type == TokenType.MATH_SHIFT and self._current().value == '$':
                self._advance()
                children = self._parse_math_content()
                if self._current().type == TokenType.MATH_SHIFT:
                    self._advance()
                    if self._current().type == TokenType.MATH_SHIFT:
                        self._advance()
                return DisplayMath(children=children, delimiter='$$', pos=self._make_range(start))
            else:
                children = self._parse_math_content()
                if self._current().type == TokenType.MATH_SHIFT:
                    self._advance()
                return InlineMath(children=children, delimiter='$', pos=self._make_range(start))

        return InlineMath(children=[], delimiter='$', pos=self._make_range(start))

    def _parse_math_content(self) -> list[ASTNode]:
        nodes = []
        while self._current().type not in (TokenType.MATH_SHIFT, TokenType.EOF):
            prev_pos = self.pos
            token = self._current()

            if token.type == TokenType.COMMAND:
                node = self._parse_command()
                if node:
                    nodes.append(node)
            elif token.type == TokenType.TEXT:
                nodes.append(self._parse_text())
            elif token.type == TokenType.SUPERSCRIPT:
                nodes.append(self._parse_superscript())
            elif token.type == TokenType.SUBSCRIPT:
                nodes.append(self._parse_subscript())
            elif token.type == TokenType.OPEN_BRACE:
                nodes.append(self._parse_group())
            elif token.type == TokenType.SPACE:
                self._advance()
            elif token.type == TokenType.NEWLINE:
                self._advance()
            else:
                self._advance()
            if self.pos == prev_pos and self._current().type not in (TokenType.MATH_SHIFT, TokenType.EOF):
                self._advance()

        return nodes

    def _parse_superscript(self) -> Superscript:
        start = self._cur_pos()
        self._advance()
        self._skip_spaces()
        content = self._parse_group() if self._current().type == TokenType.OPEN_BRACE else self._parse_atom()
        return Superscript(content=content, pos=self._make_range(start))

    def _parse_subscript(self) -> Subscript:
        start = self._cur_pos()
        self._advance()
        self._skip_spaces()
        content = self._parse_group() if self._current().type == TokenType.OPEN_BRACE else self._parse_atom()
        return Subscript(content=content, pos=self._make_range(start))

    def _parse_atom(self) -> ASTNode:
        token = self._current()

        if token.type == TokenType.TEXT:
            self._advance()
            return Text(token.value)
        elif token.type == TokenType.COMMAND:
            return self._parse_command()
        elif token.type == TokenType.OPEN_BRACE:
            return self._parse_group()

        self._advance()
        return Text(token.value)

    def _parse_environment(self) -> ASTNode:
        start = self._cur_pos()
        token = self._advance()
        env_name = token.value

        optional_args = []
        required_args = []

        self._skip_spaces()
        while self._current().type == TokenType.OPEN_BRACKET:
            optional_args.append(self._parse_optional_group())
            self._skip_spaces()

        while self._current().type == TokenType.OPEN_BRACE:
            required_args.append(self._parse_group())
            self._skip_spaces()

        if env_name in self.VERBATIM_ENVS:
            children = self._parse_verbatim_environment(env_name)
            return Environment(name=env_name, arguments=required_args,
                               optional_arguments=optional_args, children=children,
                               pos=self._make_range(start))

        children = self._parse_environment_content(env_name)

        if env_name in self.MATH_ENVS:
            return MathEnvironment(name=env_name, children=children, pos=self._make_range(start))
        elif env_name in self.LIST_ENVS:
            items = [node for node in children if isinstance(node, ListItem)]
            return List(list_type=env_name, items=items, pos=self._make_range(start))
        elif env_name in self.FLOAT_ENVS:
            caption = None
            label = None
            content = []
            for child in children:
                if isinstance(child, Caption):
                    caption = child
                elif isinstance(child, Label):
                    label = child
                else:
                    content.append(child)
            return Float(float_type=env_name, children=content, caption=caption,
                         label=label.name if label else None, pos=self._make_range(start))
        elif env_name in self.TABLE_ENVS:
            return Table(children=children, pos=self._make_range(start))
        else:
            return Environment(name=env_name, arguments=required_args,
                               optional_arguments=optional_args, children=children,
                               pos=self._make_range(start))

    def _parse_verbatim_environment(self, env_name: str) -> list[ASTNode]:
        nodes = []
        raw_text = []

        while self._current().type != TokenType.EOF:
            token = self._current()
            if token.type == TokenType.END_ENV and token.value == env_name:
                self._advance()
                break
            raw_text.append(token.value)
            self._advance()

        if raw_text:
            nodes.append(Text(''.join(raw_text)))

        return nodes

    def _parse_environment_content(self, env_name: str) -> list[ASTNode]:
        nodes = []
        depth = 1

        while depth > 0 and self._current().type != TokenType.EOF:
            prev_pos = self.pos
            token = self._current()

            if token.type == TokenType.BEGIN_ENV:
                if token.value == env_name:
                    depth += 1
                node = self._parse_environment()
                if node:
                    nodes.append(node)
            elif token.type == TokenType.END_ENV:
                if token.value == env_name:
                    depth -= 1
                    if depth == 0:
                        self._advance()
                        break
                else:
                    self._advance()
            else:
                node = self._parse_node()
                if node:
                    nodes.append(node)
            if self.pos == prev_pos and self._current().type != TokenType.EOF:
                self._advance()

        return nodes

    def _parse_until_close_brace(self) -> str:
        text = []
        depth = 1

        while depth > 0 and self._current().type != TokenType.EOF:
            token = self._current()

            if token.type == TokenType.OPEN_BRACE:
                depth += 1
                text.append('{')
                self._advance()
            elif token.type == TokenType.CLOSE_BRACE:
                depth -= 1
                if depth > 0:
                    text.append('}')
                self._advance()
            elif token.type == TokenType.TEXT:
                text.append(token.value)
                self._advance()
            elif token.type == TokenType.SPACE:
                text.append(' ')
                self._advance()
            elif token.type == TokenType.NEWLINE:
                text.append('\n')
                self._advance()
            elif token.type == TokenType.COMMAND:
                text.append(token.value)
                self._advance()
            else:
                text.append(token.value)
                self._advance()

        return ''.join(text)

    def _read_until_close_brace(self) -> str:
        text = []

        while self._current().type not in (TokenType.CLOSE_BRACE, TokenType.EOF):
            token = self._current()

            if token.type == TokenType.TEXT:
                text.append(token.value)
            elif token.type == TokenType.SPACE:
                text.append(' ')
            elif token.type == TokenType.NEWLINE:
                text.append('\n')
            elif token.type == TokenType.COMMAND:
                text.append(token.value)
            else:
                text.append(token.value)

            self._advance()

        if self._current().type == TokenType.CLOSE_BRACE:
            self._advance()

        return ''.join(text)

    def _extract_text(self, nodes: list[ASTNode]) -> str:
        text = []
        for node in nodes:
            if isinstance(node, Text):
                text.append(node.content)
            elif isinstance(node, Group):
                text.append(self._extract_text(node.children))
            elif isinstance(node, SpecialChar):
                if node.escaped:
                    text.append('\\' + node.char)
                else:
                    text.append(node.char)
        return ''.join(text)

    def _parse_length(self, text: str) -> Optional[Length]:
        import re
        match = re.match(r'([0-9.]+)\s*(cm|mm|in|pt|em|ex|bp|pc|dd|cc|sp)', text.strip())
        if match:
            return Length(value=float(match.group(1)), unit=match.group(2))
        return None
