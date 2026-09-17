"""AST-based remove changes package markup from LaTeX files.

This module provides an alternative to the regex-based remove_changes.py
that operates on the AST instead of raw text.
"""

from pathlib import Path
from typing import Optional

from .lexer import LatexLexer
from .parser import LatexParser
from .serializer import LatexSerializer
from .ast_nodes import (
    LatexAST, ASTNode, Command, Environment, Group, OptionalGroup, Package,
    Comment, Text, SpecialChar,
    MathEnvironment, InlineMath, DisplayMath,
    List, ListItem, Float, Caption,
    FontCommand, Section, Footnote, Hyperlink, Accent,
    NewCommand, NewEnvironment, Space, Length,
    Table, TableRow, TableCell, Superscript, Subscript,
)
from .expand import expand_latex
from .remove_changes import _remove_empty_math


def parse_changes_list(content: str) -> dict[str, str]:
    """Parse changes list content into a dict mapping command names to types.

    Uses the same format as remove-changes:
    \\command{old}     - delete content
    \\command{new}     - keep content
    \\command{new}{old} - replace (keep new, delete old)

    Returns:
        Dict mapping command names (without backslash) to types:
        'added', 'deleted', 'replaced'
    """
    result = {}

    for line in content.splitlines():
        # Strip inline comments
        line = line.split('#')[0].strip()
        if not line:
            continue

        # Must start with backslash
        if not line.startswith('\\'):
            continue

        # Determine behavior based on placeholders
        has_new = '{new}' in line
        has_old = '{old}' in line

        if not has_new and not has_old:
            continue

        # Extract command name (everything before first {, [, or whitespace)
        cmd_end = len(line)
        for i, ch in enumerate(line):
            if ch in '{[' or ch.isspace():
                cmd_end = i
                break

        cmd_name = line[:cmd_end]
        if not cmd_name.startswith('\\'):
            continue

        # Strip backslash for the dict key
        name = cmd_name[1:] if cmd_name.startswith('\\') else cmd_name

        if has_new and has_old:
            result[name] = 'replaced'
        elif has_new:
            result[name] = 'added'
        elif has_old:
            result[name] = 'deleted'

    return result


def ast_remove_changes(
    main_file: Path,
    mode: str,
    changes_list: dict[str, str] | None = None,
    remove_empty: bool = False,
) -> str:
    """Remove changes package markup using AST-based approach.

    Args:
        main_file: Path to the main .tex file
        mode: 'new' or 'old'
        changes_list: Dict mapping command names to types (default: built-in changes commands)
        remove_empty: If True, remove empty \\[...\\] and equation environments

    Returns:
        Processed LaTeX text with changes markup removed
    """
    # Step 1: Expand includes
    expanded = expand_latex(main_file)

    # Step 2: Parse to AST
    lexer = LatexLexer(expanded)
    tokens = lexer.get_tokens()
    parser = LatexParser(tokens)
    ast = parser.parse()
    ast.source = expanded

    # Step 3: Transform AST
    transformer = ChangesTransformer(mode, changes_list or {}, expanded)
    new_ast = transformer.transform(ast)

    # Step 4: Serialize
    serializer = LatexSerializer()
    result = serializer.serialize(new_ast)

    # Step 5: Remove empty math
    if remove_empty:
        result = _remove_empty_math(result)

    return result


class ChangesTransformer:
    """Transforms AST to remove changes package markup.

    Only processes changes commands inside \\begin{document}...\\end{document}
    and inside \\title{} in the preamble. Other content is left unchanged.

    Returns lists of nodes because changes commands may expand to multiple nodes
    (the content inside braces, without the command wrapper).
    """

    def __init__(self, mode: str, changes_list: dict[str, str], source_text: str):
        self.mode = mode
        self.changes_list = changes_list
        self.source_text = source_text

    def transform(self, ast: LatexAST) -> LatexAST:
        """Transform the AST."""
        # Find document environment
        document_env = None
        doc_index = -1

        for i, child in enumerate(ast.children):
            if isinstance(child, Environment) and child.name == 'document':
                document_env = child
                doc_index = i
                break

        # Build new children
        new_children = []
        for i, child in enumerate(ast.children):
            if i == doc_index:
                # Process document environment
                new_nodes = self._transform_env(child)
                new_children.extend(new_nodes)
            elif isinstance(child, Command) and child.name == 'title':
                # Process title in preamble
                new_nodes = self._transform_title(child)
                new_children.extend(new_nodes)
            elif isinstance(child, Package) and child.name == 'changes':
                # Remove \usepackage{changes}
                continue
            else:
                new_children.append(child)

        return LatexAST(children=new_children, metadata=ast.metadata, source=ast.source)

    def _transform_env(self, env: Environment) -> list[ASTNode]:
        """Transform an environment's children."""
        new_children = self._transform_children(env.children)
        # Environment is kept as a single node
        return [Environment(
            name=env.name,
            arguments=env.arguments,
            optional_arguments=env.optional_arguments,
            children=new_children,
            pos=env.pos,
        )]

    def _transform_children(self, children: list[ASTNode]) -> list[ASTNode]:
        """Transform a list of children, flattening results."""
        result = []
        for child in children:
            result.extend(self._transform_node(child))
        return result

    def _transform_node(self, node: ASTNode) -> list[ASTNode]:
        """Transform a single node. Returns a list of replacement nodes."""
        if isinstance(node, Command):
            return self._transform_command(node)
        elif isinstance(node, Group):
            # Keep group wrapper but transform children
            new_children = self._transform_children(node.children)
            return [Group(new_children, pos=node.pos)]
        elif isinstance(node, OptionalGroup):
            new_children = self._transform_children(node.children)
            return [OptionalGroup(new_children, pos=node.pos)]
        elif isinstance(node, Environment):
            new_children = self._transform_children(node.children)
            return [Environment(
                name=node.name,
                arguments=node.arguments,
                optional_arguments=node.optional_arguments,
                children=new_children,
                pos=node.pos,
            )]
        elif isinstance(node, MathEnvironment):
            new_children = self._transform_children(node.children)
            return [MathEnvironment(
                name=node.name,
                children=new_children,
                mode=node.mode,
                arguments=node.arguments,
                optional_arguments=node.optional_arguments,
                pos=node.pos,
            )]
        elif isinstance(node, InlineMath):
            new_children = self._transform_children(node.children)
            return [InlineMath(children=new_children, delimiter=node.delimiter, pos=node.pos)]
        elif isinstance(node, DisplayMath):
            new_children = self._transform_children(node.children)
            return [DisplayMath(children=new_children, delimiter=node.delimiter, pos=node.pos)]
        elif isinstance(node, List):
            new_items = []
            for item in node.items:
                new_item_children = self._transform_children(item.children)
                new_label = None
                if item.label:
                    label_nodes = self._transform_node(item.label)
                    if label_nodes:
                        new_label = label_nodes[0]
                new_items.append(ListItem(
                    children=new_item_children,
                    label=new_label,
                    pos=item.pos,
                ))
            return [List(list_type=node.list_type, items=new_items, pos=node.pos)]
        elif isinstance(node, Float):
            new_children = self._transform_children(node.children)
            new_caption = node.caption
            if node.caption:
                new_content = None
                if node.caption.content:
                    content_nodes = self._transform_node(node.caption.content)
                    if content_nodes:
                        new_content = content_nodes[0] if len(content_nodes) == 1 else Group(content_nodes)
                new_short = None
                if node.caption.short_caption:
                    short_nodes = self._transform_node(node.caption.short_caption)
                    if short_nodes:
                        new_short = short_nodes[0] if len(short_nodes) == 1 else Group(short_nodes)
                if new_content is None:
                    new_caption = None
                else:
                    new_caption = Caption(
                        content=new_content,
                        short_caption=new_short,
                        pos=node.caption.pos,
                    )
            return [Float(
                float_type=node.float_type,
                children=new_children,
                caption=new_caption,
                label=node.label,
                pos=node.pos,
            )]
        elif isinstance(node, FontCommand):
            if node.content:
                content_nodes = self._transform_node(node.content)
                if not content_nodes:
                    return []
                # Wrap in Group to preserve command structure
                return [FontCommand(font_type=node.font_type, content=Group(content_nodes), pos=node.pos)]
            return [node]
        elif isinstance(node, Section):
            if node.title:
                title_nodes = self._transform_node(node.title)
                if not title_nodes:
                    return []
                return [Section(
                    level=node.level,
                    title=title_nodes[0] if len(title_nodes) == 1 else Group(title_nodes),
                    number=node.number,
                    star=node.star,
                    pos=node.pos,
                )]
            return [node]
        elif isinstance(node, Footnote):
            if node.content:
                content_nodes = self._transform_node(node.content)
                if not content_nodes:
                    return []
                return [Footnote(content=content_nodes[0] if len(content_nodes) == 1 else Group(content_nodes), number=node.number, pos=node.pos)]
            return [node]
        elif isinstance(node, Caption):
            new_content = None
            if node.content:
                content_nodes = self._transform_node(node.content)
                if content_nodes:
                    new_content = content_nodes[0] if len(content_nodes) == 1 else Group(content_nodes)
            if new_content is None:
                return []
            new_short = None
            if node.short_caption:
                short_nodes = self._transform_node(node.short_caption)
                if short_nodes:
                    new_short = short_nodes[0] if len(short_nodes) == 1 else Group(short_nodes)
            return [Caption(content=new_content, short_caption=new_short, pos=node.pos)]
        elif isinstance(node, Hyperlink):
            new_text = None
            if node.text:
                text_nodes = self._transform_node(node.text)
                if text_nodes:
                    new_text = text_nodes[0] if len(text_nodes) == 1 else Group(text_nodes)
            return [Hyperlink(url=node.url, text=new_text, href_type=node.href_type, pos=node.pos)]
        elif isinstance(node, Accent):
            if node.content:
                content_nodes = self._transform_node(node.content)
                if not content_nodes:
                    return []
                return [Accent(accent_type=node.accent_type, content=content_nodes[0] if len(content_nodes) == 1 else Group(content_nodes), pos=node.pos)]
            return [node]
        elif isinstance(node, NewCommand):
            new_definition = None
            if node.definition:
                def_nodes = self._transform_node(node.definition)
                if def_nodes:
                    new_definition = def_nodes[0] if len(def_nodes) == 1 else Group(def_nodes)
                else:
                    new_definition = Group([], pos=node.definition.pos)
            new_default = None
            if node.default:
                default_nodes = self._transform_node(node.default)
                if default_nodes:
                    new_default = default_nodes[0] if len(default_nodes) == 1 else Group(default_nodes)
            return [NewCommand(
                name=node.name,
                definition=new_definition,
                num_args=node.num_args,
                default=new_default,
                pos=node.pos,
            )]
        elif isinstance(node, NewEnvironment):
            new_before = None
            if node.before:
                before_nodes = self._transform_node(node.before)
                if before_nodes:
                    new_before = before_nodes[0] if len(before_nodes) == 1 else Group(before_nodes)
                else:
                    new_before = Group([], pos=node.before.pos)
            new_after = None
            if node.after:
                after_nodes = self._transform_node(node.after)
                if after_nodes:
                    new_after = after_nodes[0] if len(after_nodes) == 1 else Group(after_nodes)
                else:
                    new_after = Group([], pos=node.after.pos)
            new_default = None
            if node.default:
                default_nodes = self._transform_node(node.default)
                if default_nodes:
                    new_default = default_nodes[0] if len(default_nodes) == 1 else Group(default_nodes)
            return [NewEnvironment(
                name=node.name,
                before=new_before,
                after=new_after,
                num_args=node.num_args,
                default=new_default,
                pos=node.pos,
            )]
        elif isinstance(node, Table):
            new_children = self._transform_children(node.children)
            return [Table(children=new_children, alignment=node.alignment, pos=node.pos)]
        elif isinstance(node, TableRow):
            new_cells = []
            for cell in node.cells:
                cell_nodes = self._transform_node(cell)
                new_cells.extend(cell_nodes)
            return [TableRow(cells=new_cells, pos=node.pos)]
        elif isinstance(node, TableCell):
            new_children = self._transform_children(node.children)
            return [TableCell(children=new_children, pos=node.pos)]
        elif isinstance(node, Superscript):
            if node.content:
                content_nodes = self._transform_node(node.content)
                if not content_nodes:
                    return []
                return [Superscript(content=content_nodes[0] if len(content_nodes) == 1 else Group(content_nodes), pos=node.pos)]
            return [node]
        elif isinstance(node, Subscript):
            if node.content:
                content_nodes = self._transform_node(node.content)
                if not content_nodes:
                    return []
                return [Subscript(content=content_nodes[0] if len(content_nodes) == 1 else Group(content_nodes), pos=node.pos)]
            return [node]
        elif isinstance(node, (Space, Length)):
            return [node]

        # For leaf nodes (Text, Comment, SpecialChar, etc.), return as-is
        return [node]

    def _transform_title(self, cmd: Command) -> list[ASTNode]:
        """Transform a \\title{} command, processing changes in its argument."""
        new_args = []
        for arg in cmd.arguments:
            new_args.extend(self._transform_node(arg))
        if not new_args:
            return []
        return [Command(
            name=cmd.name,
            arguments=new_args,
            optional_arguments=cmd.optional_arguments,
            star=cmd.star,
            pos=cmd.pos,
        )]

    def _transform_command(self, cmd: Command) -> list[ASTNode]:
        """Transform a command node, processing changes commands."""
        cmd_name = cmd.name

        # Standard changes commands
        if cmd_name == 'added':
            return self._process_added(cmd)
        elif cmd_name == 'deleted':
            return self._process_deleted(cmd)
        elif cmd_name == 'replaced':
            return self._process_replaced(cmd)
        elif cmd_name == 'comment':
            return []  # Always remove
        elif cmd_name == 'highlight':
            return self._process_highlight(cmd)

        # Check if this is a custom changes command
        if cmd_name in self.changes_list:
            cmd_type = self.changes_list[cmd_name]
            return self._process_custom_command(cmd, cmd_type)

        # Regular command - recursively process arguments
        new_args = []
        for arg in cmd.arguments:
            arg_nodes = self._transform_node(arg)
            # Wrap multiple nodes back into a Group to preserve command structure
            if len(arg_nodes) == 1:
                new_args.append(arg_nodes[0])
            elif len(arg_nodes) > 1:
                new_args.append(Group(arg_nodes))
        new_opts = []
        for opt in cmd.optional_arguments:
            opt_nodes = self._transform_node(opt)
            if len(opt_nodes) == 1:
                new_opts.append(opt_nodes[0])
            elif len(opt_nodes) > 1:
                new_opts.append(OptionalGroup(opt_nodes))

        return [Command(
            name=cmd_name,
            arguments=new_args,
            optional_arguments=new_opts,
            star=cmd.star,
            pos=cmd.pos,
        )]

    def _process_added(self, cmd: Command) -> list[ASTNode]:
        """Process \\added{} command."""
        if self.mode == 'new':
            # Keep content, remove command and braces
            if cmd.arguments:
                arg = cmd.arguments[0]
                if isinstance(arg, Group):
                    return self._transform_children(arg.children)
            return []
        else:
            # Remove in 'old' mode
            if self._is_full_line_delete(cmd):
                return [Comment('%', pos=cmd.pos)]
            return []

    def _process_deleted(self, cmd: Command) -> list[ASTNode]:
        """Process \\deleted{} command."""
        if self.mode == 'old':
            # Keep content, remove command and braces
            if cmd.arguments:
                arg = cmd.arguments[0]
                if isinstance(arg, Group):
                    return self._transform_children(arg.children)
            return []
        else:
            # Remove in 'new' mode
            if self._is_full_line_delete(cmd):
                return [Comment('%', pos=cmd.pos)]
            return []

    def _process_replaced(self, cmd: Command) -> list[ASTNode]:
        """Process \\replaced{new}{old} command."""
        if len(cmd.arguments) >= 2:
            new_arg = cmd.arguments[0] if self.mode == 'new' else cmd.arguments[1]
            if isinstance(new_arg, Group):
                return self._transform_children(new_arg.children)
            return self._transform_node(new_arg)
        else:
            # Malformed command, keep as-is
            return [cmd]

    def _process_highlight(self, cmd: Command) -> list[ASTNode]:
        """Process \\highlight{} command - keep content, remove command and braces."""
        if cmd.arguments:
            arg = cmd.arguments[0]
            if isinstance(arg, Group):
                return self._transform_children(arg.children)
        return []

    def _process_custom_command(self, cmd: Command, cmd_type: str) -> list[ASTNode]:
        """Process a custom changes command.

        Args:
            cmd: The command node
            cmd_type: The type of the command ('added', 'deleted', 'replaced', etc.)
        """
        if cmd_type == 'replaced':
            # Replace: {new}{old}
            if len(cmd.arguments) >= 2:
                new_arg = cmd.arguments[0] if self.mode == 'new' else cmd.arguments[1]
                if isinstance(new_arg, Group):
                    return self._transform_children(new_arg.children)
                return self._transform_node(new_arg)
            else:
                return [cmd]
        elif cmd_type == 'added':
            if self.mode == 'new':
                # Keep: {new}
                if cmd.arguments:
                    arg = cmd.arguments[0]
                    if isinstance(arg, Group):
                        return self._transform_children(arg.children)
                return []
            else:
                # Remove in 'old' mode
                if self._is_full_line_delete(cmd):
                    return [Comment('%', pos=cmd.pos)]
                return []
        elif cmd_type == 'deleted':
            if self.mode == 'old':
                # Keep: {old}
                if cmd.arguments:
                    arg = cmd.arguments[0]
                    if isinstance(arg, Group):
                        return self._transform_children(arg.children)
                return []
            else:
                # Remove in 'new' mode
                if self._is_full_line_delete(cmd):
                    return [Comment('%', pos=cmd.pos)]
                return []
        elif cmd_type == 'comment':
            # Always remove
            return []
        elif cmd_type == 'highlight':
            # Keep content, remove command and braces
            if cmd.arguments:
                arg = cmd.arguments[0]
                if isinstance(arg, Group):
                    return self._transform_children(arg.children)
            return []
        else:
            return [cmd]

    def _is_full_line_delete(self, cmd: Command) -> bool:
        """Check if a command spans an entire line in the source text.

        Returns True if there's only whitespace before the command on its line
        and only whitespace after the command until the next newline.
        """
        if cmd.pos is None:
            return False

        source = self.source_text
        lines = source.split('\n')

        # Get the line number (1-indexed)
        line_no = cmd.pos.start.line
        if line_no < 1 or line_no > len(lines):
            return False

        line = lines[line_no - 1]

        # Get the column range of the command on this line
        start_col = cmd.pos.start.column
        end_col = cmd.pos.end.column

        # Check if there's only whitespace before the command on this line
        before = line[:start_col - 1]  # -1 because column is 1-indexed
        if before.strip():
            return False

        # Check if there's only whitespace after the command until end of line
        after = line[end_col - 1:]  # -1 because column is 1-indexed
        if after.strip():
            return False

        return True