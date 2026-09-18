"""Convert AST back to LaTeX text."""

from .ast_nodes import *


class LatexSerializer:
    """Serialize AST back to LaTeX source."""

    def serialize(self, ast: LatexAST) -> str:
        """Serialize AST to LaTeX string."""
        parts = []
        for i, child in enumerate(ast.children):
            if i > 0 and self._needs_space_before(ast.children[i-1], child):
                parts.append(' ')
            parts.append(self._serialize_node(child))
        return ''.join(parts)

    @staticmethod
    def _needs_space_before(prev: ASTNode, curr: ASTNode) -> bool:
        """Check if a space is needed between two consecutive nodes.

        Needed when prev is an argumentless command ending with a letter
        and curr is a Text node starting with a letter, to prevent the
        command name from merging with the following text.
        
        Also handles Subscript/Superscript nodes whose content is a command
        ending with a letter (e.g., c_\\delta N needs a space to prevent
        \\deltaN from being parsed as a single command).
        """
        # Unwrap Subscript/Superscript to check their content
        if isinstance(prev, (Subscript, Superscript)):
            prev = prev.content
        
        if not isinstance(prev, Command):
            return False
        if prev.arguments or prev.optional_arguments:
            return False
        if not prev.name or not prev.name[-1].isalpha():
            return False
        if not isinstance(curr, Text):
            return False
        return bool(curr.content) and curr.content[0].isalpha()

    def _serialize_node(self, node: ASTNode) -> str:
        if node is None:
            return ''

        if isinstance(node, Text):
            return node.content

        if isinstance(node, Comment):
            return node.content

        if isinstance(node, Command):
            return self._serialize_command(node)

        if isinstance(node, Environment):
            return self._serialize_environment(node)

        if isinstance(node, MathEnvironment):
            return self._serialize_math_environment(node)

        if isinstance(node, InlineMath):
            return self._serialize_inline_math(node)

        if isinstance(node, DisplayMath):
            return self._serialize_display_math(node)

        if isinstance(node, Group):
            return self._serialize_group(node)

        if isinstance(node, OptionalGroup):
            return self._serialize_optional_group(node)

        if isinstance(node, SpecialChar):
            if node.escaped:
                return '\\' + node.char
            return node.char

        if isinstance(node, Superscript):
            return '^' + self._serialize_node(node.content)

        if isinstance(node, Subscript):
            return '_' + self._serialize_node(node.content)

        if isinstance(node, FontCommand):
            return '\\' + node.font_type + self._serialize_node(node.content)

        if isinstance(node, Section):
            return self._serialize_section(node)

        if isinstance(node, List):
            return self._serialize_list(node)

        if isinstance(node, ListItem):
            return self._serialize_list_item(node)

        if isinstance(node, Float):
            return self._serialize_float(node)

        if isinstance(node, Table):
            return self._serialize_table(node)

        if isinstance(node, Graphics):
            return self._serialize_graphics(node)

        if isinstance(node, Hyperlink):
            return self._serialize_hyperlink(node)

        if isinstance(node, Citation):
            return self._serialize_citation(node)

        if isinstance(node, Reference):
            return '\\' + node.ref_type + '{' + node.label + '}'

        if isinstance(node, Footnote):
            return '\\footnote' + self._serialize_node(node.content)

        if isinstance(node, Caption):
            return self._serialize_caption(node)

        if isinstance(node, Label):
            return '\\label{' + node.name + '}'

        if isinstance(node, Package):
            return self._serialize_package(node)

        if isinstance(node, DocumentClass):
            return self._serialize_documentclass(node)

        if isinstance(node, NewCommand):
            return self._serialize_new_command(node)

        if isinstance(node, NewEnvironment):
            return self._serialize_new_environment(node)

        if isinstance(node, Space):
            return self._serialize_space(node)

        if isinstance(node, Length):
            return f'{node.value}{node.unit}'

        if isinstance(node, Paragraph):
            return '\\par'

        if isinstance(node, LineBreak):
            return '\\\\'

        if isinstance(node, Accent):
            return '\\' + node.accent_type + self._serialize_node(node.content)

        if isinstance(node, Counter):
            return '\\value{' + node.name + '}'

        # Fallback: try to serialize children
        if hasattr(node, 'children') and node.children:
            return self._serialize_children_with_spaces(node.children)

        return ''

    def _serialize_children_with_spaces(self, children: list) -> str:
        """Serialize a list of children, adding spaces between consecutive
        nodes when needed to prevent command-name merging."""
        parts = []
        for i, child in enumerate(children):
            if i > 0 and self._needs_space_before(children[i-1], child):
                parts.append(' ')
            parts.append(self._serialize_node(child))
        return ''.join(parts)

    def _serialize_command(self, node: Command) -> str:
        parts = ['\\' + node.name]
        if node.star:
            parts.append('*')
        for opt in node.optional_arguments:
            parts.append(self._serialize_node(opt))
        for arg in node.arguments:
            parts.append(self._serialize_node(arg))
        return ''.join(parts)

    def _serialize_group(self, node: Group) -> str:
        parts = []
        for i, child in enumerate(node.children):
            if i > 0 and self._needs_space_before(node.children[i-1], child):
                parts.append(' ')
            parts.append(self._serialize_node(child))
        inner = ''.join(parts)
        return '{' + inner + '}'

    def _serialize_optional_group(self, node: OptionalGroup) -> str:
        inner = self._serialize_children_with_spaces(node.children)
        return '[' + inner + ']'

    def _serialize_environment(self, node: Environment) -> str:
        parts = ['\\begin{' + node.name + '}']
        for opt in node.optional_arguments:
            parts.append(self._serialize_node(opt))
        for arg in node.arguments:
            parts.append(self._serialize_node(arg))
        parts.append(self._serialize_children_with_spaces(node.children))
        parts.append('\\end{' + node.name + '}')
        return ''.join(parts)

    def _serialize_math_environment(self, node: MathEnvironment) -> str:
        parts = ['\\begin{' + node.name + '}']
        for opt in node.optional_arguments:
            parts.append(self._serialize_node(opt))
        for arg in node.arguments:
            parts.append(self._serialize_node(arg))
        parts.append(self._serialize_children_with_spaces(node.children))
        parts.append('\\end{' + node.name + '}')
        return ''.join(parts)

    def _serialize_inline_math(self, node: InlineMath) -> str:
        inner = self._serialize_children_with_spaces(node.children)
        return '$' + inner + '$'

    def _serialize_display_math(self, node: DisplayMath) -> str:
        inner = self._serialize_children_with_spaces(node.children)
        if node.delimiter == '$$':
            return '$$' + inner + '$$'
        elif node.delimiter == '\\[\\]':
            return '\\[' + inner + '\\]'
        else:
            return node.delimiter + inner + node.delimiter

    def _serialize_section(self, node: Section) -> str:
        level_names = {0: 'part', 1: 'chapter', 2: 'section', 3: 'subsection',
                       4: 'subsubsection', 5: 'paragraph', 6: 'subparagraph'}
        name = level_names.get(node.level, 'section')
        star = '*' if node.star else ''
        return '\\' + name + star + self._serialize_node(node.title)

    def _serialize_list(self, node: List) -> str:
        parts = ['\\begin{' + node.list_type + '}']
        for item in node.items:
            parts.append(self._serialize_node(item))
        parts.append('\\end{' + node.list_type + '}')
        return ''.join(parts)

    def _serialize_list_item(self, node: ListItem) -> str:
        parts = ['\\item']
        if node.label:
            parts.append(self._serialize_node(node.label))
        else:
            parts.append(' ')
        parts.append(self._serialize_children_with_spaces(node.children))
        return ''.join(parts)

    def _serialize_float(self, node: Float) -> str:
        parts = ['\\begin{' + node.float_type + '}']
        parts.append(self._serialize_children_with_spaces(node.children))
        parts.append('\\end{' + node.float_type + '}')
        return ''.join(parts)

    def _serialize_table(self, node: Table) -> str:
        parts = ['\\begin{tabular}{', node.alignment or '', '}']
        parts.append(self._serialize_children_with_spaces(node.children))
        parts.append('\\end{tabular}')
        return ''.join(parts)

    def _serialize_graphics(self, node: Graphics) -> str:
        parts = ['\\includegraphics']
        for opt in node.options:
            parts.append(self._serialize_node(opt))
        parts.append('{' + node.filename + '}')
        return ''.join(parts)

    def _serialize_hyperlink(self, node: Hyperlink) -> str:
        if node.href_type == 'url':
            return '\\url{' + node.url + '}'
        parts = ['\\href{' + node.url + '}']
        if node.text:
            parts.append(self._serialize_node(node.text))
        return ''.join(parts)

    def _serialize_citation(self, node: Citation) -> str:
        parts = ['\\cite']
        if node.optional:
            parts.append('[' + node.optional + ']')
        parts.append('{' + ', '.join(node.keys) + '}')
        return ''.join(parts)

    def _serialize_caption(self, node: Caption) -> str:
        parts = ['\\caption']
        if node.short_caption:
            parts.append(self._serialize_node(node.short_caption))
        parts.append(self._serialize_node(node.content))
        return ''.join(parts)

    def _serialize_package(self, node: Package) -> str:
        parts = ['\\usepackage']
        if node.options:
            parts.append('[' + ', '.join(node.options) + ']')
        parts.append('{' + node.name + '}')
        return ''.join(parts)

    def _serialize_documentclass(self, node: DocumentClass) -> str:
        parts = ['\\documentclass']
        if node.options:
            parts.append('[' + ', '.join(node.options) + ']')
        parts.append('{' + node.name + '}')
        return ''.join(parts)

    def _serialize_new_command(self, node: NewCommand) -> str:
        parts = ['\\newcommand{' + node.name + '}']
        if node.num_args > 0:
            parts.append('[' + str(node.num_args) + ']')
        if node.default:
            parts.append(self._serialize_node(node.default))
        parts.append(self._serialize_node(node.definition))
        return ''.join(parts)

    def _serialize_new_environment(self, node: NewEnvironment) -> str:
        parts = ['\\newenvironment{' + node.name + '}']
        if node.num_args > 0:
            parts.append('[' + str(node.num_args) + ']')
        if node.default:
            parts.append(self._serialize_node(node.default))
        parts.append(self._serialize_node(node.before))
        parts.append(self._serialize_node(node.after))
        return ''.join(parts)

    def _serialize_space(self, node: Space) -> str:
        parts = ['\\' + node.space_type]
        if node.length:
            parts.append('{' + self._serialize_node(node.length) + '}')
        return ''.join(parts)
