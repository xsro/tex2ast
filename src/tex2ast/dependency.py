"""Analyze LaTeX file dependencies."""

import re
from pathlib import Path
from typing import Optional


# File extensions to consider for graphics
GRAPHIC_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.pdf', '.eps', '.svg', '.tikz'}

# Patterns for finding dependencies
INCLUDE_PATTERN = re.compile(r'\\(?:include|input)\s*\{([^}]+)\}')
GRAPHICS_PATTERN = re.compile(r'\\includegraphics\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}')
BIBLIOGRAPHY_PATTERN = re.compile(r'\\(?:bibliography|addbibresource)\s*\{([^}]+)\}')
INCLUDEONLY_PATTERN = re.compile(r'\\includeonly\s*\{([^}]+)\}')


def find_dependencies(content: str, base_dir: Path) -> dict[str, list[Path]]:
    """Find all file dependencies in LaTeX content.

    Returns dict with keys: 'tex', 'graphics', 'bib'
    """
    deps = {
        'tex': [],
        'graphics': [],
        'bib': [],
    }

    # Find \include and \input
    for match in INCLUDE_PATTERN.finditer(content):
        file_ref = match.group(1).strip()
        if not file_ref.endswith('.tex'):
            file_ref += '.tex'
        file_path = (base_dir / file_ref).resolve()
        deps['tex'].append(file_path)

    # Find \includegraphics
    for match in GRAPHICS_PATTERN.finditer(content):
        file_ref = match.group(1).strip()
        file_path = (base_dir / file_ref).resolve()

        # If no extension, try common graphic extensions
        if not file_path.suffix:
            for ext in GRAPHIC_EXTENSIONS:
                candidate = file_path.with_suffix(ext)
                if candidate.exists():
                    file_path = candidate
                    break

        deps['graphics'].append(file_path)

    # Find \bibliography or \addbibresource
    for match in BIBLIOGRAPHY_PATTERN.finditer(content):
        file_ref = match.group(1).strip()
        # Multiple bib files can be separated by commas
        for ref in file_ref.split(','):
            ref = ref.strip()
            if ref:
                bib_path = (base_dir / ref).resolve()
                if not bib_path.suffix:
                    bib_path = bib_path.with_suffix('.bib')
                deps['bib'].append(bib_path)

    # Find \includeonly (these are also tex files)
    for match in INCLUDEONLY_PATTERN.finditer(content):
        file_ref = match.group(1).strip()
        for ref in file_ref.split(','):
            ref = ref.strip()
            if ref:
                tex_path = (base_dir / ref).resolve()
                if not tex_path.suffix:
                    tex_path = tex_path.with_suffix('.tex')
                if tex_path not in deps['tex']:
                    deps['tex'].append(tex_path)

    return deps


def collect_all_dependencies(
    main_file: Path,
    visited: set[Path] | None = None,
    root_dir: Path | None = None,
) -> dict[str, set[Path]]:
    """Recursively collect all dependencies starting from main file.

    Args:
        main_file: The .tex file to process
        visited: Set of already visited files (for cycle detection)
        root_dir: Root directory (main file's dir). Relative paths always resolve from here.

    Returns dict with keys: 'tex', 'graphics', 'bib'
    """
    if visited is None:
        visited = set()
    if root_dir is None:
        root_dir = main_file.parent

    main_file = main_file.resolve()
    if main_file in visited:
        return {'tex': set(), 'graphics': set(), 'bib': set()}
    visited.add(main_file)

    all_deps = {'tex': set(), 'graphics': set(), 'bib': set()}

    try:
        content = main_file.read_text(encoding='utf-8')
    except Exception:
        return all_deps

    # Always use root_dir for resolving relative paths
    deps = find_dependencies(content, root_dir)

    # Process tex files recursively
    for tex_file in deps['tex']:
        all_deps['tex'].add(tex_file)
        sub_deps = collect_all_dependencies(tex_file, visited, root_dir)
        for key in all_deps:
            all_deps[key].update(sub_deps[key])

    # Add graphics and bib directly
    all_deps['graphics'].update(deps['graphics'])
    all_deps['bib'].update(deps['bib'])

    return all_deps


def find_unreferenced_files(
    directory: Path,
    referenced: set[Path],
) -> list[Path]:
    """Find files in directory that are not in the referenced set."""
    unreferenced = []

    for file_path in directory.rglob('*'):
        if not file_path.is_file():
            continue

        # Skip hidden files and common non-content files
        if file_path.name.startswith('.'):
            continue
        if file_path.suffix in ('.aux', '.log', '.toc', '.out', '.fls', '.fdb_latexmk', '.synctex.gz'):
            continue

        resolved = file_path.resolve()
        if resolved not in referenced:
            unreferenced.append(file_path)

    return sorted(unreferenced)


def format_dependencies(main_file: Path, deps: dict[str, set[Path]]) -> str:
    """Format dependencies for display."""
    lines = []
    lines.append(f"Dependencies for: {main_file}")
    lines.append("=" * 60)

    if deps['tex']:
        lines.append(f"\nTeX files ({len(deps['tex'])}):")
        for f in sorted(deps['tex']):
            exists = "  " if f.exists() else " ! "
            lines.append(f"  {exists}{f}")

    if deps['graphics']:
        lines.append(f"\nGraphics ({len(deps['graphics'])}):")
        for f in sorted(deps['graphics']):
            exists = "  " if f.exists() else " ! "
            lines.append(f"  {exists}{f}")

    if deps['bib']:
        lines.append(f"\nBibliography ({len(deps['bib'])}):")
        for f in sorted(deps['bib']):
            exists = "  " if f.exists() else " ! "
            lines.append(f"  {exists}{f}")

    total = sum(len(v) for v in deps.values())
    lines.append(f"\nTotal: {total} file(s)")

    return '\n'.join(lines)
