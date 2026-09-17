# Example Projects

This folder contains example LaTeX projects for testing and demonstration purposes.

## English Project (`english/`)

A complete LaTeX research paper demonstrating:
- Document structure (title, author, abstract, sections)
- The `changes` package for tracking revisions (`\added`, `\deleted`, `\replaced`, `\highlight`, `\cancel`)
- Math environments (equations)
- Figures and captions
- Bibliography references
- Itemized and enumerated lists
- Cross-references (`\ref`, `\label`)
- Hyperlinks (`\href`)

## Chinese Project (`chinese/`)

A Chinese-language LaTeX research paper using the `ctex` package, demonstrating:
- Chinese text processing
- All the same features as the English project
- Mixed Chinese and English content

## Usage

```bash
# Parse to AST JSON
tex2ast ast -i example/english/main.tex

# Convert to processed LaTeX (remove changes)
tex2ast remove-changes -i example/english/main.tex -m new
tex2ast ast-remove-changes -i example/english/main.tex -m new

# Expand includes
tex2ast expand -i example/english/main.tex

# Check dependencies
tex2ast dependency -i example/english/main.tex
```