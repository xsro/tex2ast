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


# Built-in default commands (used if config file not found)
BUILTIN_DEFAULT_COMMANDS = [
    {'name': '\\cancel', 'has_new': False, 'has_old': True},
    {'name': '\\xcancel', 'has_new': False, 'has_old': True},
    {'name': '\\sG', 'has_new': False, 'has_old': True},
    {'name': '\\tG', 'has_new': True, 'has_old': False},
    {'name': '\\replaceG', 'has_new': True, 'has_old': True},
]


def get_default_config_path() -> Optional[Path]:
    """Get the path to the default config file.

    Looks for .config/remove-changes.txt in:
    1. Current working directory
    2. Project root (where pyproject.toml is)

    Returns:
        Path to config file, or None if not found
    """
    # Check current working directory
    cwd_config = Path('.config/remove-changes.txt').resolve()
    if cwd_config.exists():
        return cwd_config

    # Check project root (two levels up from this file)
    # src/tex2ast/remove_changes.py -> project root
    project_root = Path(__file__).resolve().parent.parent.parent
    project_config = project_root / '.config/remove-changes.txt'
    if project_config.exists():
        return project_config

    return None


def parse_changes_config(config_path: Path) -> list[dict]:
    """Parse a remove-changes config file.

    Format:
    # Comments start with #
    \\command{old}     - delete content
    \\command{new}     - keep content
    \\command{new}{old} - replace (keep new, delete old)

    Returns:
        List of command specs with 'name', 'has_new', 'has_old'
    """
    commands = []

    if config_path is None or not config_path.exists():
        return commands

    content = config_path.read_text(encoding='utf-8')

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

        commands.append({
            'name': cmd_name,
            'has_new': has_new,
            'has_old': has_old,
        })

    return commands


def get_changes_commands(config_path: str | None = None) -> list[dict]:
    """Get the list of custom change commands.

    Args:
        config_path: Path to config file, or None for default, or 'none' for no config

    Returns:
        List of command specs

    Raises:
        FileNotFoundError: if config_path is specified but file doesn't exist
    """
    if config_path is None:
        # Use default config
        default_path = get_default_config_path()
        if default_path:
            return parse_changes_config(default_path)
        else:
            # Fall back to built-in defaults
            return list(BUILTIN_DEFAULT_COMMANDS)
    elif config_path == 'none':
        return []
    else:
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        return parse_changes_config(path)

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


def process_changes(text: str, mode: str, custom_commands: list[dict] | None = None,
                   remove_empty: bool = False) -> str:
    """Process changes package commands in text.

    Only processes commands within \\begin{document}...\\end{document}
    and \\title{} in the preamble. Other preamble content is left unchanged.

    Args:
        text: LaTeX source text
        mode: 'new' for new version, 'old' for old version
        custom_commands: List of custom command specs from config
        remove_empty: If True, remove empty \\[...\\] and equation environments

    Returns:
        Processed text
    """
    # Process changes with scope restrictions (document body + \title{})
    result = _process_changes_scope(text, mode, custom_commands)

    # Remove empty math environments (also scope-restricted)
    if remove_empty:
        result = _remove_empty_math(result)

    return result


def _process_changes_scope(text: str, mode: str, custom_commands: list[dict] | None = None) -> str:
    """Process changes commands only within document body and \\title{} in preamble.

    Args:
        text: LaTeX source text
        mode: 'new' for new version, 'old' for old version
        custom_commands: List of custom command specs from config

    Returns:
        Processed text with changes only in scoped areas
    """
    # Find document environment boundaries
    doc_match = re.search(r'\\begin\{document\}', text)
    if not doc_match:
        # No document environment, only process \title{} in preamble
        return _process_title_only(text, mode, custom_commands)

    doc_start = doc_match.end()
    doc_end_match = re.search(r'\\end\{document\}', text[doc_start:])
    if not doc_end_match:
        # No \end{document} found, only process \title{} in preamble
        return _process_title_only(text, mode, custom_commands)

    doc_end = doc_start + doc_end_match.start()

    # Split into preamble, document body, and post-document
    preamble = text[:doc_start]
    doc_body = text[doc_start:doc_end]
    post_doc = text[doc_end:]

    # Process changes in document body
    doc_body = _process_changes_unconditional(doc_body, mode, custom_commands)

    # Process \title{} in preamble
    preamble = _process_title_only(preamble, mode, custom_commands)

    return preamble + doc_body + post_doc


def _process_title_only(text: str, mode: str, custom_commands: list[dict] | None = None) -> str:
    """Process changes commands only within \\title{} in the given text."""
    def _replace_title(match: re.Match) -> str:
        title_content = match.group(1)
        processed = _process_changes_unconditional(title_content, mode, custom_commands)
        return '\\title{' + processed + '}'

    return re.sub(r'\\title\{([^}]*)\}', _replace_title, text)


def _process_changes_unconditional(text: str, mode: str, custom_commands: list[dict] | None = None) -> str:
    """Process changes commands in text without scope restrictions."""
    result = []
    i = 0

    # Standard changes commands
    standard_commands = ['\\added', '\\deleted', '\\replaced', '\\comment', '\\highlight']

    # Build list of all commands to check
    custom_names = [cmd['name'] for cmd in (custom_commands or [])]

    while i < len(text):
        # Check for any command
        cmd_match = None
        for cmd in standard_commands + custom_names:
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
                    # Recursively process inner commands
                    result.append(_process_changes_unconditional(content, mode, custom_commands))
                # For 'old' mode, skip entirely (don't append anything)
                i = end_pos

            elif cmd_match == '\\deleted':
                content, end_pos = _extract_brace_content(text, pos)
                if mode == 'old':
                    # Recursively process inner commands
                    result.append(_process_changes_unconditional(content, mode, custom_commands))
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
                        # Recursively process inner commands
                        result.append(_process_changes_unconditional(new_content, mode, custom_commands))
                    else:
                        result.append(_process_changes_unconditional(old_content, mode, custom_commands))
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
                # Recursively process inner commands
                result.append(_process_changes_unconditional(content, mode, custom_commands))
                i = end_pos

            else:
                # Custom command
                cmd_spec = next(c for c in custom_commands if c['name'] == cmd_match)

                if cmd_spec['has_new'] and cmd_spec['has_old']:
                    # Replace: {new}{old}
                    new_content, end_pos = _extract_brace_content(text, pos)
                    temp_pos = end_pos
                    while temp_pos < len(text) and text[temp_pos] in ' \t\n':
                        temp_pos += 1
                    if temp_pos < len(text) and text[temp_pos] == '{':
                        old_content, end_pos = _extract_brace_content(text, temp_pos)
                        if mode == 'new':
                            # Recursively process inner commands
                            result.append(_process_changes_unconditional(new_content, mode, custom_commands))
                        else:
                            result.append(_process_changes_unconditional(old_content, mode, custom_commands))
                        i = end_pos
                    else:
                        result.append(text[i])
                        i += 1
                elif cmd_spec['has_new']:
                    # Keep: {new}
                    content, end_pos = _extract_brace_content(text, pos)
                    # Recursively process inner commands
                    result.append(_process_changes_unconditional(content, mode, custom_commands))
                    i = end_pos
                elif cmd_spec['has_old']:
                    # Delete: {old}
                    _, end_pos = _extract_brace_content(text, pos)
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


def _remove_empty_math_simple(text: str) -> str:
    """Remove empty \\[...\\] and equation environments (unconditional)."""
    # Remove empty \[...\]
    text = re.sub(r'\\\[\s*\\\]', '', text)
    # Remove empty \begin{equation}...\end{equation}
    text = re.sub(r'\\begin\{equation\}\s*\\end\{equation\}', '', text)
    # Remove empty \begin{equation*}...\end{equation*}
    text = re.sub(r'\\begin\{equation\*\}\s*\\end\{equation\*\}', '', text)
    return text


def _remove_empty_math(text: str) -> str:
    """Remove empty \\[...\\] and equation environments.

    Only processes content inside \\begin{document}...\\end{document}
    and empty \\title{} commands in the preamble.
    """
    # Find document environment boundaries
    doc_match = re.search(r'\\begin\{document\}', text)
    if not doc_match:
        # No document environment, don't process math environments
        # But still handle empty \title{}
        text = re.sub(r'\\title\{(\s*)\}', '', text)
        return text

    doc_start = doc_match.end()
    doc_end_match = re.search(r'\\end\{document\}', text[doc_start:])
    if not doc_end_match:
        # No \end{document} found, don't process
        text = re.sub(r'\\title\{(\s*)\}', '', text)
        return text

    doc_end = doc_start + doc_end_match.start()

    # Split into preamble, document body, and post-document
    preamble = text[:doc_start]
    doc_body = text[doc_start:doc_end]
    post_doc = text[doc_end:]

    # Process empty math only in document body
    doc_body = _remove_empty_math_simple(doc_body)

    # Remove empty \title{} in preamble
    preamble = re.sub(r'\\title\{(\s*)\}', '', preamble)

    return preamble + doc_body + post_doc


def process_file(file_path: Path, mode: str, apply: bool,
                 visited: set[Path] | None = None,
                 base_dir: Path | None = None,
                 custom_commands: list[dict] | None = None,
                 remove_empty: bool = False) -> dict[str, str]:
    """Process a single LaTeX file.

    Args:
        file_path: Path to the LaTeX file
        mode: 'new' or 'old'
        apply: If True, modify files in place
        visited: Set of already processed files (for cycle detection)
        base_dir: Base directory for resolving includes
        custom_commands: List of custom command specs from config
        remove_empty: If True, remove empty \\[...\\] and equation environments

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
        inc_results = process_file(inc_file, mode, apply, visited, base_dir, custom_commands, remove_empty)
        results.update(inc_results)

    # Process current file
    processed = process_changes(content, mode, custom_commands, remove_empty)
    processed = _remove_usepackage_changes(processed)
    # Preserve line structure: replace lines that became empty with % comments
    processed = _preserve_deleted_lines(content, processed)

    results[str(file_path)] = processed

    # Apply changes if requested
    if apply:
        file_path.write_text(processed, encoding='utf-8')

    return results


def _preserve_deleted_lines(original: str, processed: str) -> str:
    """Replace lines that became empty after changes removal with % comments.

    This prevents LaTeX from merging paragraphs when an entire line
    is deleted by \\deleted{} or custom delete commands.

    Args:
        original: Original text before changes processing
        processed: Text after changes processing

    Returns:
        Processed text with empty lines replaced by % where appropriate
    """
    orig_lines = original.splitlines(keepends=True)
    proc_lines = processed.splitlines(keepends=True)

    result = []
    for i, proc_line in enumerate(proc_lines):
        # If processed line is empty/whitespace-only and original had content
        if not proc_line.strip() and i < len(orig_lines) and orig_lines[i].strip():
            # Preserve original line ending
            ending = '\n' if proc_line.endswith('\n') else ''
            result.append('%' + ending)
        else:
            result.append(proc_line)

    return ''.join(result)


def expand_and_remove_changes(
    main_file: Path,
    mode: str,
    visited: set[Path] | None = None,
    root_dir: Path | None = None,
    custom_commands: list[dict] | None = None,
    remove_empty: bool = False,
) -> str:
    """Recursively expand \\input/\\include and strip changes markup.

    Args:
        main_file: Path to the main .tex file.
        mode: 'new' or 'old'
        visited: Set of already-visited files (cycle detection).
        root_dir: Root directory for resolving relative paths.
        custom_commands: List of custom command specs from config.
        remove_empty: If True, remove empty \\[...\\] and equation environments.

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

    # First expand includes recursively (without processing changes)
    pattern = re.compile(r'(\\(?:include|input))\s*\{([^}]+)\}')

    def _replace(match: re.Match) -> str:
        cmd = match.group(1)
        file_ref = match.group(2).strip()
        if not file_ref.endswith('.tex'):
            file_ref += '.tex'
        ref_path = (root_dir / file_ref).resolve()
        expanded = _expand_includes_only(ref_path, visited, root_dir)
        if cmd == '\\include':
            return f"\\clearpage\n{expanded}\\clearpage\n"
        return expanded

    expanded = pattern.sub(_replace, content)
    # Now process changes on the fully expanded text
    processed = process_changes(expanded, mode, custom_commands, remove_empty)
    processed = _remove_usepackage_changes(processed)
    # Preserve line structure: replace lines that became empty with % comments
    processed = _preserve_deleted_lines(expanded, processed)
    return processed


def _expand_includes_only(
    file_path: Path,
    visited: set[Path],
    root_dir: Path,
) -> str:
    """Recursively expand \\input/\\include without processing changes."""
    file_path = file_path.resolve()

    if file_path in visited:
        return "% [circular include skipped]\n"
    visited.add(file_path)

    try:
        content = file_path.read_text(encoding='utf-8')
    except FileNotFoundError:
        return f"% [file not found: {file_path}]\n"

    pattern = re.compile(r'(\\(?:include|input))\s*\{([^}]+)\}')

    def _replace(match: re.Match) -> str:
        cmd = match.group(1)
        file_ref = match.group(2).strip()
        if not file_ref.endswith('.tex'):
            file_ref += '.tex'
        ref_path = (root_dir / file_ref).resolve()
        expanded = _expand_includes_only(ref_path, visited, root_dir)
        if cmd == '\\include':
            return f"\\clearpage\n{expanded}\\clearpage\n"
        return expanded

    return pattern.sub(_replace, content)


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
