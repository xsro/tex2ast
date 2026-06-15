# tex2ast

LaTeX to AST converter with XeLaTeX support, roundtrip conversion, and utility commands.

## Features

- **LaTeX to AST**: Parse LaTeX files into Abstract Syntax Tree with position info
- **Roundtrip conversion**: tex -> json -> tex produces identical output
- **changes package**: Strip `\added`, `\deleted`, `\replaced` markup to generate old/new versions
- **Dependency analysis**: Find all included/input/graphics files, clean unreferenced files
- **BibTeX extraction**: Export cited bib entries to a new file
- Full XeLaTeX syntax support (CJK, math, tables, figures, etc.)

## Installation

```bash
git clone <repository-url>
cd tex2ast

uv venv
uv pip install -e .
```

## Commands

### `tex2ast ast` - Convert LaTeX to AST JSON

```bash
tex2ast ast -i document.tex -o document.json
tex2ast ast -i document.tex -o document.json --pretty
```

### `tex2ast tex` - Convert AST JSON back to LaTeX

```bash
tex2ast tex -i document.json -o document.tex
```

### Roundtrip

```bash
tex2ast ast -i document.tex -o document.json
tex2ast tex -i document.json -o document.tex
diff document.tex document.tex  # identical!
```

### `tex2ast remove-changes` - Strip changes package markup

Supports `\added`, `\deleted`, `\replaced`, `\comment`, `\highlight` commands.
Recursively processes `\include` and `\input` files.

```bash
tex2ast remove-changes -i document.tex --new          # new version
tex2ast remove-changes -i document.tex --old           # old version
tex2ast remove-changes -i document.tex --new --run     # apply in place
```

| Command | `--new` | `--old` |
|---------|---------|---------|
| `\added{text}` | keep text | remove |
| `\deleted{text}` | remove | keep text |
| `\replaced{new}{old}` | use new | use old |
| `\comment{text}` | remove | remove |
| `\highlight{text}` | keep text | keep text |

### `tex2ast dependency` - Analyze file dependencies

```bash
tex2ast dependency -i document.tex                              # list dependencies
tex2ast dependency -i document.tex --clean_dir ./figures        # find unreferenced files
tex2ast dependency -i document.tex --clean_dir ./figures --run  # delete unreferenced
```

Output:
- `!` marks files that are referenced but missing
- `--clean_dir` lists files in the directory that are NOT referenced
- `--run` deletes unreferenced files

### `tex2ast extract-bib` - Extract cited bib entries

```bash
tex2ast extract-bib -i document.tex -o cited.bib
tex2ast extract-bib -i document.tex                         # output to stdout
tex2ast extract-bib -i document.tex -o cited.bib --bib refs.bib
```

- Auto-detects bib files from `\bibliography` and `\addbibresource`
- Parses `\cite`, `\citep`, `\citet`, `\autocite`, `\parencite`, `\textcite`, `\nocite`, etc.
- Recursively processes `\include`/`\input` for citations

## Path Resolution

Relative paths in LaTeX are always resolved relative to the **main .tex file's directory**, regardless of where the referencing file is located. All commands follow this rule.

## JSON Output Format

Each AST node includes position info:

```json
{
  "type": "LatexAST",
  "children": [
    {
      "type": "Command",
      "pos": {
        "start": {"line": 1, "column": 15, "offset": 0},
        "end": {"line": 1, "column": 38, "offset": 7}
      },
      "name": "documentclass",
      "arguments": [...]
    }
  ],
  "metadata": {},
  "source": "\\documentclass{article}..."
}
```

## Supported LaTeX Features

- Document structure: `\documentclass`, `\usepackage`, sections
- Text formatting: `\textbf`, `\textit`, `\emph`, etc.
- Math: inline `$...$`, display `$$...$$`, environments (equation, align, matrix, etc.)
- Environments: itemize, enumerate, tabular, figure, table, quote, etc.
- Cross-references: `\label`, `\ref`, `\cite`, `\footnote`
- Graphics: `\includegraphics`
- Links: `\href`, `\url`
- Special characters: `\#`, `\$`, `\%`, `\&`, `\_`, `\{`, `\}`, `\~`, `\^`
- Chinese typesetting (ctex)
- Verbatim environments (lstlisting, verbatim)

## Project Structure

```
tex2ast/
├── src/tex2ast/
│   ├── __init__.py
│   ├── ast_nodes.py      # AST node definitions with position info
│   ├── lexer.py          # LaTeX lexer
│   ├── parser.py         # LaTeX parser
│   ├── serializer.py     # AST to LaTeX serializer
│   ├── remove_changes.py # changes package remover
│   ├── dependency.py     # Dependency analyzer
│   ├── bib_parser.py     # BibTeX parser
│   └── cli.py            # Command-line interface
├── pyproject.toml
└── README.md
```

## License

MIT License
