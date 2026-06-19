"""Remove changes package markup from LaTeX files."""

import re
from pathlib import Path
from typing import Optional


# Changes package commands
# \added[options]{text} - text was added
# \deleted[options]{text} - text was deleted
# \replaced[options]{new}{old} - text was replaced
# \comment[options]{text} - comment
# \highlight[options]{text} - highlight

def _find_matching_brace(text: str, start: int) -> int:
    """Find the position of the matching closing brace.

    Args:
        text: The full text
        start: Position of the opening brace

    Returns:
        Position of the matching closing brace, or -1 if not found
    """
    if start >= len(text) or text[start] != '{':
        return -1

    depth = 0
    i = start
    while i < len(text):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return i
        elif text[i] == '\\':
            # Skip escaped character
            i += 1
        i += 1

    return -1


def _skip_optional_arg(text: str, pos: int) -> int:
    """Skip an optional argument [...].

    Returns position after the closing ].
    """
    if pos >= len(text) or text[pos] != '[':
        return pos

    depth = 0
    i = pos
    while i < len(text):
        if text[i] == '[':
            depth += 1
        elif text[i] == ']':
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1

    return pos


def _extract_brace_content(text: str, pos: int) -> tuple[str, int]:
    """Extract content inside braces starting at pos.

    Returns (content, end_position) where end_position is after the closing brace.
    """
    end = _find_matching_brace(text, pos)
    if end == -1:
        return '', pos
    return text[pos + 1:end], end + 1


def process_changes(text: str, mode: str) -> str:
    """Process changes package commands in text.

    Args:
        text: LaTeX source text
        mode: 'new' for new version, 'old' for old version

    Returns:
        Processed text
    """
    result = []
    i = 0

    while i < len(text):
        # Check for changes commands
        cmd_match = None
        for cmd in ['\\added', '\\deleted', '\\replaced', '\\comment', '\\highlight']:
            if text[i:i + len(cmd)] == cmd:
                # Make sure it's a complete command (next char is not alpha)
                next_pos = i + len(cmd)
                if next_pos < len(text) and text[next_pos].isalpha():
                    continue
                cmd_match = cmd
                break

        if cmd_match:
            pos = i + len(cmd_match)

            # Skip optional argument [...]
            pos = _skip_optional_arg(text, pos)

            # Skip whitespace
            while pos < len(text) and text[pos] in ' \t':
                pos += 1

            if pos >= len(text) or text[pos] != '{':
                # Not a proper command, keep the backslash and continue
                result.append(text[i])
                i += 1
                continue

            if cmd_match == '\\added':
                content, end_pos = _extract_brace_content(text, pos)
                if mode == 'new':
                    result.append(content)
                # For 'old' mode, skip entirely (don't append anything)
                i = end_pos

            elif cmd_match == '\\deleted':
                content, end_pos = _extract_brace_content(text, pos)
                if mode == 'old':
                    result.append(content)
                # For 'new' mode, skip entirely (don't append anything)
                i = end_pos

            elif cmd_match == '\\replaced':
                new_content, end_pos = _extract_brace_content(text, pos)
                # Skip whitespace between arguments
                temp_pos = end_pos
                while temp_pos < len(text) and text[temp_pos] in ' \t\n':
                    temp_pos += 1

                if temp_pos < len(text) and text[temp_pos] == '{':
                    old_content, end_pos = _extract_brace_content(text, temp_pos)
                    if mode == 'new':
                        result.append(new_content)
                    else:
                        result.append(old_content)
                    i = end_pos
                else:
                    # Malformed command, keep as-is
                    result.append(text[i])
                    i += 1

            elif cmd_match == '\\comment':
                _, end_pos = _extract_brace_content(text, pos)
                # Skip comments in both versions
                i = end_pos

            elif cmd_match == '\\highlight':
                content, end_pos = _extract_brace_content(text, pos)
                result.append(content)
                i = end_pos

            else:
                result.append(text[i])
                i += 1
        else:
            result.append(text[i])
            i += 1

    return ''.join(result)


def _find_included_files(text: str, base_dir: Path) -> list[Path]:
    """Find all \\include and \\input files.

    Returns list of file paths.
    """
    files = []

    # Match \include{file} or \input{file}
    pattern = re.compile(r'\\(?:include|input)\{([^}]+)\}')

    for match in pattern.finditer(text):
        file_ref = match.group(1)

        # Add .tex extension if not present
        if not file_ref.endswith('.tex'):
            file_ref += '.tex'

        file_path = base_dir / file_ref
        if file_path.exists():
            files.append(file_path)

    return files


def _remove_usepackage_changes(text: str) -> str:
    """Remove \\usepackage{changes} from text."""
    # Remove \usepackage[options]{changes}
    text = re.sub(r'\\usepackage(?:\[[^\]]*\])?\{changes\}\s*\n?', '', text)
    return text


def process_file(file_path: Path, mode: str, apply: bool,
                 visited: set[Path] | None = None,
                 base_dir: Path | None = None) -> dict[str, str]:
    """Process a single LaTeX file.

    Args:
        file_path: Path to the LaTeX file
        mode: 'new' or 'old'
        apply: If True, modify files in place
        visited: Set of already processed files (for cycle detection)
        base_dir: Base directory for resolving includes

    Returns:
        Dict mapping file paths to their processed content
    """
    if visited is None:
        visited = set()
    if base_dir is None:
        base_dir = file_path.parent

    # Resolve to absolute path
    file_path = file_path.resolve()

    # Cycle detection
    if file_path in visited:
        return {}
    visited.add(file_path)

    # Read file
    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return {}

    # Find included files first (before processing)
    included_files = _find_included_files(content, base_dir)

    # Process included files recursively
    results = {}
    for inc_file in included_files:
        inc_results = process_file(inc_file, mode, apply, visited, base_dir)
        results.update(inc_results)

    # Process current file
    processed = process_changes(content, mode)
    processed = _remove_usepackage_changes(processed)

    results[str(file_path)] = processed

    # Apply changes if requested
    if apply:
        file_path.write_text(processed, encoding='utf-8')

    return results


def expand_and_remove_changes(
    main_file: Path,
    mode: str,
    visited: set[Path] | None = None,
    root_dir: Path | None = None,
) -> str:
    """Recursively expand \\input/\\include and strip changes markup.

    Args:
        main_file: Path to the main .tex file.
        mode: 'new' or 'old'
        visited: Set of already-visited files (cycle detection).
        root_dir: Root directory for resolving relative paths.

    Returns:
        The expanded LaTeX source with changes markup removed.
    """
    main_file = main_file.resolve()
    if visited is None:
        visited = set()
    if root_dir is None:
        root_dir = main_file.parent

    if main_file in visited:
        return "% [circular include skipped]\n"
    visited.add(main_file)

    try:
        content = main_file.read_text(encoding='utf-8')
    except FileNotFoundError:
        return f"% [file not found: {main_file}]\n"

    # First expand includes, then strip changes
    pattern = re.compile(r'(\\(?:include|input))\s*\{([^}]+)\}')

    def _replace(match: re.Match) -> str:
        cmd = match.group(1)
        file_ref = match.group(2).strip()
        if not file_ref.endswith('.tex'):
            file_ref += '.tex'
        ref_path = (root_dir / file_ref).resolve()
        expanded = expand_and_remove_changes(ref_path, mode, visited, root_dir)
        if cmd == '\\include':
            return f"\\clearpage\n{expanded}\\clearpage\n"
        return expanded

    expanded = pattern.sub(_replace, content)
    processed = process_changes(expanded, mode)
    processed = _remove_usepackage_changes(processed)
    return processed


def show_diff(original: str, processed: str, file_path: str) -> str:
    """Show a simple diff between original and processed content."""
    orig_lines = original.splitlines(keepends=True)
    proc_lines = processed.splitlines(keepends=True)

    diff_output = []
    diff_output.append(f"--- {file_path}")
    diff_output.append(f"+++ {file_path} (processed)")

    # Simple line-by-line comparison
    max_lines = max(len(orig_lines), len(proc_lines))
    i = 0
    while i < max_lines:
        orig = orig_lines[i] if i < len(orig_lines) else ''
        proc = proc_lines[i] if i < len(proc_lines) else ''

        if orig != proc:
            if orig:
                diff_output.append(f"- {orig.rstrip()}")
            if proc:
                diff_output.append(f"+ {proc.rstrip()}")

        i += 1

    return '\n'.join(diff_output)
