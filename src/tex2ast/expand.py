"""Expand \\input and \\include into a single LaTeX file."""

import re
from pathlib import Path


# Patterns for \input and \include (capture the command name and the file argument)
_INCLUDE_INPUT_RE = re.compile(
    r'(\\(?:include|input))\s*\{([^}]+)\}'
)


def expand_latex(
    main_file: Path,
    visited: set[Path] | None = None,
    root_dir: Path | None = None,
) -> str:
    """Recursively expand \\input and \\include in a LaTeX file.

    Args:
        main_file: Path to the main .tex file.
        visited: Set of already-visited files (cycle detection).
        root_dir: Root directory for resolving relative paths.
                  Defaults to main_file's parent.

    Returns:
        The expanded LaTeX source with all \\input/\\include replaced
        by the actual file contents.
    """
    main_file = main_file.resolve()
    if visited is None:
        visited = set()
    if root_dir is None:
        root_dir = main_file.parent

    if main_file in visited:
        return f"% [circular include skipped: {main_file.name}]\n"
    visited.add(main_file)

    try:
        content = main_file.read_text(encoding='utf-8')
    except FileNotFoundError:
        return f"% [file not found: {main_file}]\n"

    def _replace(match: re.Match) -> str:
        cmd = match.group(1)      # \input or \include
        file_ref = match.group(2).strip()

        # Resolve the referenced file
        if not file_ref.endswith('.tex'):
            file_ref += '.tex'
        ref_path = (root_dir / file_ref).resolve()

        # Recursively expand the referenced file
        expanded = expand_latex(ref_path, visited, root_dir)

        if cmd == '\\include':
            # \include adds \clearpage before and after
            return f"\\clearpage\n{expanded}\\clearpage\n"
        else:
            # \input is a straight textual insertion
            return expanded

    result = _INCLUDE_INPUT_RE.sub(_replace, content)
    return result
