"""AST node definitions for LaTeX parsing."""

from dataclasses import dataclass, field
from typing import Optional, Union
from enum import Enum


class MathMode(Enum):
    INLINE = "inline"
    DISPLAY = "display"
    TEXT = "text"
    ENVIRONMENT = "environment"


@dataclass
class SourcePos:
    """Source position info."""
    line: int = 0
    column: int = 0
    offset: int = 0

@dataclass
class SourceRange:
    """Source range (start and end positions)."""
    start: SourcePos = field(default_factory=SourcePos)
    end: SourcePos = field(default_factory=SourcePos)


@dataclass
class ASTNode:
    """Base AST node."""
    pos: Optional[SourceRange] = field(default=None, kw_only=True)


@dataclass
class LatexAST:
    """Root AST node."""
    children: list[ASTNode] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    source: str = ""


@dataclass
class Text(ASTNode):
    """Plain text content."""
    content: str = ""


@dataclass
class Command(ASTNode):
    """LaTeX command."""
    name: str = ""
    arguments: list[ASTNode] = field(default_factory=list)
    optional_arguments: list[ASTNode] = field(default_factory=list)
    star: bool = False


@dataclass
class Environment(ASTNode):
    """LaTeX environment."""
    name: str = ""
    arguments: list[ASTNode] = field(default_factory=list)
    optional_arguments: list[ASTNode] = field(default_factory=list)
    children: list[ASTNode] = field(default_factory=list)
    star: bool = False


@dataclass
class MathEnvironment(ASTNode):
    """Math environment."""
    name: str = ""
    children: list[ASTNode] = field(default_factory=list)
    mode: MathMode = MathMode.ENVIRONMENT


@dataclass
class InlineMath(ASTNode):
    """Inline math: $...$"""
    children: list[ASTNode] = field(default_factory=list)
    delimiter: str = "$"


@dataclass
class DisplayMath(ASTNode):
    """Display math: $$...$$"""
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
    content: str = ""
    inline: bool = False


@dataclass
class SpecialChar(ASTNode):
    """Special character."""
    char: str = ""
    escaped: bool = False


@dataclass
class Superscript(ASTNode):
    """Superscript: ^"""
    content: ASTNode = field(default=None)


@dataclass
class Subscript(ASTNode):
    """Subscript: _"""
    content: ASTNode = field(default=None)


@dataclass
class Accent(ASTNode):
    """Accent command."""
    accent_type: str = ""
    content: ASTNode = field(default=None)


@dataclass
class FontCommand(ASTNode):
    """Font command."""
    font_type: str = ""
    content: ASTNode = field(default=None)


@dataclass
class Length(ASTNode):
    """Length value: 1cm, 2pt, etc."""
    value: float = 0.0
    unit: str = ""


@dataclass
class Counter(ASTNode):
    """Counter."""
    name: str = ""


@dataclass
class Reference(ASTNode):
    """Reference."""
    ref_type: str = ""
    label: str = ""


@dataclass
class Citation(ASTNode):
    """Citation."""
    keys: list[str] = field(default_factory=list)
    optional: Optional[str] = None


@dataclass
class Footnote(ASTNode):
    """Footnote."""
    content: ASTNode = field(default=None)
    number: Optional[int] = None


@dataclass
class Hyperlink(ASTNode):
    """Hyperlink."""
    url: str = ""
    text: Optional[ASTNode] = None
    href_type: str = "href"


@dataclass
class Graphics(ASTNode):
    """Graphics."""
    filename: str = ""
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
    """List environment."""
    list_type: str = ""
    items: list[ASTNode] = field(default_factory=list)


@dataclass
class ListItem(ASTNode):
    """List item."""
    children: list[ASTNode] = field(default_factory=list)
    label: Optional[ASTNode] = None


@dataclass
class Section(ASTNode):
    """Section command."""
    level: int = 0
    title: ASTNode = field(default=None)
    number: Optional[str] = None
    star: bool = False


@dataclass
class Float(ASTNode):
    """Float environment."""
    float_type: str = ""
    children: list[ASTNode] = field(default_factory=list)
    caption: Optional[ASTNode] = None
    label: Optional[str] = None


@dataclass
class Caption(ASTNode):
    """Caption command."""
    content: ASTNode = field(default=None)
    short_caption: Optional[ASTNode] = None


@dataclass
class Label(ASTNode):
    """Label command."""
    name: str = ""


@dataclass
class NewCommand(ASTNode):
    """New command definition."""
    name: str = ""
    definition: ASTNode = field(default=None)
    num_args: int = 0
    default: Optional[ASTNode] = None


@dataclass
class NewEnvironment(ASTNode):
    """New environment definition."""
    name: str = ""
    before: ASTNode = field(default=None)
    after: ASTNode = field(default=None)
    num_args: int = 0
    default: Optional[ASTNode] = None


@dataclass
class Package(ASTNode):
    """Package loading."""
    name: str = ""
    options: list[str] = field(default_factory=list)


@dataclass
class DocumentClass(ASTNode):
    """Document class."""
    name: str = ""
    options: list[str] = field(default_factory=list)


@dataclass
class Paragraph(ASTNode):
    """Paragraph break."""
    pass


@dataclass
class LineBreak(ASTNode):
    """Line break."""
    pass


@dataclass
class Space(ASTNode):
    """Horizontal or vertical space."""
    space_type: str = ""
    length: Optional[Length] = None
