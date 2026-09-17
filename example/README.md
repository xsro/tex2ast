# Example Projects

This folder contains example LaTeX projects for testing and demonstrating the `tex2ast` tool.

## Project Structure

```
example/
├── README.md
├── english/
│   ├── main.tex              # Main document with \input/\include
│   ├── intro.tex             # Included file (introduction)
│   ├── methodology.tex       # Included file (methodology)
│   ├── results.tex           # Included file (results)
│   ├── tex2ast.config.py     # Project configuration
│   └── .config/
│       └── remove-changes.txt # Custom changes commands config
└── chinese/
    ├── main.tex              # Main document with \input/\include
    ├── intro.tex             # Included file (introduction)
    ├── methodology.tex       # Included file (methodology)
    ├── results.tex           # Included file (results)
    ├── tex2ast.config.py     # Project configuration
    └── .config/
        └── remove-changes.txt # Custom changes commands config
```

## Features Demonstrated

### English Project (`english/`)
A complete LaTeX research paper demonstrating:
- Document structure (title, author, abstract, sections)
- Multi-file project with `\input` and `\include` commands
- The `changes` package for tracking revisions (`\added`, `\deleted`, `\replaced`, `\highlight`, `\cancel`)
- Math environments (equations, inline math)
- Figures and captions
- Bibliography references
- Itemized and enumerated lists
- Cross-references (`\ref`, `\label`)
- Custom revision commands via config file

### Chinese Project (`chinese/`)
A Chinese-language LaTeX research paper using the `ctex` package, demonstrating:
- Chinese text processing
- Multi-file project structure
- All the same features as the English project
- Mixed Chinese and English content

## Configuration Files

### `tex2ast.config.py`
Project-level configuration that defines:
- `input_tex`: Main input file
- `output_tex`: Output file path
- `changes_list`: Inline changes commands configuration
- `remove_empty_math`: Whether to remove empty math environments

### `.config/remove-changes.txt`
Custom changes commands configuration file with `command:type` format:
- `command`: The LaTeX command name
- `type`: One of `added`, `deleted`, `replaced`, `comment`, `highlight`

## Usage

```bash
# Parse to AST JSON
tex2ast ast -i example/english/main.tex

# Convert to processed LaTeX (remove changes)
tex2ast remove-changes -i example/english/main.tex --print_change new
tex2ast ast-remove-changes -i example/english/main.tex --print_change new

# Use project config (no -i needed)
tex2ast remove-changes --project example/english/tex2ast.config.py
tex2ast ast-remove-changes --project example/chinese/tex2ast.config.py

# Expand includes
tex2ast expand -i example/english/main.tex

# Check dependencies
tex2ast dependency -i example/english/main.tex

# Use custom changes list
tex2ast remove-changes -i example/english/main.tex --changes-list example/english/.config/remove-changes.txt
```