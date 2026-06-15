# tex2ast

LaTeX to AST converter with XeLaTeX support.

## Features

- Parse LaTeX files into Abstract Syntax Tree (AST)
- Support for XeLaTeX syntax including:
  - Commands and environments
  - Math formulas (inline and display)
  - Tables and figures
  - Lists (itemize, enumerate, description)
  - Cross-references and citations
  - Hyperlinks and graphics
  - Chinese typesetting (CJK/ctex)
  - Special characters and escaping
- Command-line interface
- JSON output format

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd tex2ast

# Create virtual environment and install
uv venv
uv pip install -e .
```

## Usage

### Basic usage

```bash
# Convert LaTeX file to JSON
ast --input document.tex --output document.json

# Short form
ast -i document.tex -o document.json

# Pretty print JSON
ast -i document.tex -o document.json --pretty

# Specify encoding
ast -i document.tex -o document.json --encoding gbk
```

### Using stdin/stdout

```bash
# Read from stdin, write to stdout
cat document.tex | ast

# Read from stdin, write to file
cat document.tex | ast -o document.json

# Read from file, write to stdout
ast -i document.tex
```

### Examples

```bash
# Parse the example file
ast -i example.tex -o example.json --pretty

# View the output
cat example.json
```

## AST Node Types

The parser generates the following AST node types:

- **Document**: Root node containing all children
- **Text**: Plain text content
- **Command**: LaTeX commands with arguments
- **Environment**: LaTeX environments
- **MathEnvironment**: Math environments (equation, align, etc.)
- **InlineMath**: Inline math ($...$)
- **DisplayMath**: Display math ($$...$$ or \[...\])
- **Group**: Groups ({...})
- **OptionalGroup**: Optional groups ([...])
- **Section**: Section commands
- **List**: List environments
- **ListItem**: List items
- **Table**: Table environments
- **TableRow**: Table rows
- **TableCell**: Table cells
- **Float**: Float environments (figure, table)
- **Graphics**: Includegraphics commands
- **Hyperlink**: Hyperref commands
- **Citation**: Citation commands
- **Reference**: Cross-reference commands
- **Footnote**: Footnote commands
- **Label**: Label commands
- **Caption**: Caption commands
- **Package**: Usepackage commands
- **DocumentClass**: Documentclass command
- **Comment**: Comments
- **SpecialChar**: Special characters
- And more...

## Supported LaTeX Features

### Document Structure
- \documentclass, \usepackage
- \title, \author, \date
- \maketitle
- \section, \subsection, \subsubsection
- \paragraph, \subparagraph

### Text Formatting
- \textbf, \textit, \texttt, \textsl, \textsc
- \textrm, \textsf, \underline, \emph
- Font size commands

### Math
- Inline math: $...$, \(...\)
- Display math: $$...$$, \[...\]
- Math environments: equation, align, gather, multline, etc.
- Matrices: matrix, pmatrix, bmatrix, vmatrix, etc.
- Subscripts and superscripts

### Environments
- itemize, enumerate, description
- tabular, tabularx, longtable
- figure, table
- quote, quotation, verse
- center, flushleft, flushright
- And many more...

### Cross-references
- \label, \ref, \pageref, \eqref
- \cite, \nocite
- \footnote

### Graphics and Links
- \includegraphics
- \href, \url

### Special Characters
- Escaped characters: \#, \$, \%, \&, \_, \{, \}, \~, \^
- Unicode support (XeLaTeX)

## Output Format

The output is a JSON object with the following structure:

```json
{
  "type": "LatexAST",
  "children": [
    {
      "type": "DocumentClass",
      "name": "article",
      "options": ["12pt", "a4paper"]
    },
    {
      "type": "Package",
      "name": "ctex",
      "options": ["UTF8"]
    },
    ...
  ],
  "metadata": {}
}
```

## Development

### Project Structure

```
tex2ast/
├── src/
│   └── tex2ast/
│       ├── __init__.py
│       ├── ast_nodes.py    # AST node definitions
│       ├── lexer.py        # LaTeX lexer
│       ├── parser.py       # LaTeX parser
│       └── cli.py          # Command-line interface
├── pyproject.toml
├── README.md
└── example.tex
```

### Running Tests

```bash
# Install development dependencies
uv pip install -e ".[dev]"

# Run tests
pytest
```

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
