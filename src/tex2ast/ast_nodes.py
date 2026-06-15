"""AST node definitions for LaTeX parsing."""

from dataclasses import dataclass, field
from typing import Optional, Union
from enum import Enum


class MathMode(Enum):
    INLINE = "inline"       # $...$
    DISPLAY = "display"     # $$...$$ or \[...\]
    TEXT = "text"           # \(...\)
    ENVIRONMENT = "environment"  # \begin{equation} etc.


@dataclass
class ASTNode:
    """Base AST node."""
    pass


@dataclass
class LatexAST:
    """Root AST node."""
    children: list[ASTNode] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class Text(ASTNode):
    """Plain text content."""
    content: str


@dataclass
class Command(ASTNode):
    """LaTeX command: \\commandname[opt]{arg1}{arg2}"""
    name: str
    arguments: list[ASTNode] = field(default_factory=list)
    optional_arguments: list[ASTNode] = field(default_factory=list)
    star: bool = False  # \\command*


@dataclass
class Environment(ASTNode):
    """LaTeX environment: \\begin{name}...\\end{name}"""
    name: str
    arguments: list[ASTNode] = field(default_factory=list)
    optional_arguments: list[ASTNode] = field(default_factory=list)
    children: list[ASTNode] = field(default_factory=list)
    star: bool = False  # \\begin*{name}


@dataclass
class MathEnvironment(ASTNode):
    """Math environment: \begin{equation} etc."""
    name: str
    children: list[ASTNode] = field(default_factory=list)
    mode: MathMode = MathMode.ENVIRONMENT


@dataclass
class InlineMath(ASTNode):
    """Inline math: $...$ or \\(...\\)"""
    children: list[ASTNode] = field(default_factory=list)
    delimiter: str = "$"


@dataclass
class DisplayMath(ASTNode):
    """Display math: $$...$$ or \\[...\\]"""
    children: list[ASTNode] = field(default_factory=list)
    delimiter: str = "$$"


@dataclass
class Group(ASTNode):
    """Group: {...}"""
    children: list[ASTNode] = field(default_factory=list)


@dataclass
class OptionalGroup(ASTNode):
    """Optional group: [...]"""
    children: list[ASTNode] = field(default_factory=list)


@dataclass
class Comment(ASTNode):
    """Comment: %..."""
    content: str
    inline: bool = False


@dataclass
class SpecialChar(ASTNode):
    """Special character: #, $, %, &, _, {, }, ~, ^"""
    char: str
    escaped: bool = False


@dataclass
class Superscript(ASTNode):
    """Superscript: ^"""
    content: ASTNode


@dataclass
class Subscript(ASTNode):
    """Subscript: _"""
    content: ASTNode


@dataclass
class Accent(ASTNode):
    """Accent command: \\', \\", \\^, etc."""
    accent_type: str
    content: ASTNode


@dataclass
class FontCommand(ASTNode):
    """Font command: \textbf, \textit, etc."""
    font_type: str
    content: ASTNode


@dataclass
class Length(ASTNode):
    """Length value: 1cm, 2pt, etc."""
    value: float
    unit: str


@dataclass
class Counter(ASTNode):
    """Counter: \\value{counter}"""
    name: str


@dataclass
class Reference(ASTNode):
    """Reference: \\ref{label}, \\pageref{label}"""
    ref_type: str
    label: str


@dataclass
class Citation(ASTNode):
    """Citation: \\cite{key}"""
    keys: list[str]
    optional: Optional[str] = None


@dataclass
class Footnote(ASTNode):
    """Footnote: \\footnote{text}"""
    content: ASTNode
    number: Optional[int] = None


@dataclass
class Hyperlink(ASTNode):
    """Hyperlink: \\href{url}{text} or \\url{url}"""
    url: str
    text: Optional[ASTNode] = None
    href_type: str = "href"


@dataclass
class Graphics(ASTNode):
    """Graphics: \\includegraphics[opts]{file}"""
    filename: str
    options: list[ASTNode] = field(default_factory=list)


@dataclass
class Table(ASTNode):
    """Table environment."""
    children: list[ASTNode] = field(default_factory=list)
    alignment: Optional[str] = None


@dataclass
class TableRow(ASTNode):
    """Table row."""
    cells: list[ASTNode] = field(default_factory=list)


@dataclass
class TableCell(ASTNode):
    """Table cell."""
    children: list[ASTNode] = field(default_factory=list)


@dataclass
class List(ASTNode):
    """List environment: itemize, enumerate, description."""
    list_type: str
    items: list[ASTNode] = field(default_factory=list)


@dataclass
class ListItem(ASTNode):
    """List item."""
    children: list[ASTNode] = field(default_factory=list)
    label: Optional[ASTNode] = None


@dataclass
class Section(ASTNode):
    """Section command: \\section, \\subsection, etc."""
    level: int
    title: ASTNode
    number: Optional[str] = None
    star: bool = False


@dataclass
class Float(ASTNode):
    """Float environment: figure, table."""
    float_type: str
    children: list[ASTNode] = field(default_factory=list)
    caption: Optional[ASTNode] = None
    label: Optional[str] = None


@dataclass
class Caption(ASTNode):
    """Caption command."""
    content: ASTNode
    short_caption: Optional[ASTNode] = None


@dataclass
class Label(ASTNode):
    """Label command."""
    name: str


@dataclass
class NewCommand(ASTNode):
    """New command definition: \\newcommand{name}[args]{def}"""
    name: str
    definition: ASTNode
    num_args: int = 0
    default: Optional[ASTNode] = None


@dataclass
class NewEnvironment(ASTNode):
    """New environment definition."""
    name: str
    before: ASTNode
    after: ASTNode
    num_args: int = 0
    default: Optional[ASTNode] = None


@dataclass
class Package(ASTNode):
    """Package loading: \\usepackage[opts]{pkg}"""
    name: str
    options: list[str] = field(default_factory=list)


@dataclass
class DocumentClass(ASTNode):
    """Document class: \\documentclass[opts]{class}"""
    name: str
    options: list[str] = field(default_factory=list)


@dataclass
class Paragraph(ASTNode):
    """Paragraph break."""
    pass


@dataclass
class LineBreak(ASTNode):
    """Line break: \\\\ or \\newline"""
    pass


@dataclass
class Space(ASTNode):
    """Horizontal or vertical space."""
    space_type: str  # hspace, vspace, quad, qquad, etc.
    length: Optional[Length] = None
