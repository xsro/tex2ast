"""Parse BibTeX files and extract entries."""

import re
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class BibEntry:
    """A single BibTeX entry."""
    entry_type: str       # article, book, inproceedings, etc.
    key: str              # citation key
    fields: dict[str, str] = field(default_factory=dict)
    raw: str = ""         # original raw text


def _find_matching_brace(text: str, start: int) -> int:
    """Find position of matching closing brace."""
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
            i += 1  # skip escaped char
        i += 1

    return -1


def parse_bib_file(file_path: Path) -> list[BibEntry]:
    """Parse a .bib file and return list of entries."""
    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception:
        return []

    return parse_bib_content(content)


def parse_bib_content(content: str) -> list[BibEntry]:
    """Parse BibTeX content and return list of entries."""
    entries = []

    # Match @type{key, ...}
    # This regex finds the start of each entry
    entry_pattern = re.compile(r'@(\w+)\s*\{', re.IGNORECASE)

    pos = 0
    while pos < len(content):
        match = entry_pattern.search(content, pos)
        if not match:
            break

        entry_type = match.group(1).lower()
        brace_start = match.end() - 1  # position of {
        brace_end = _find_matching_brace(content, brace_start)

        if brace_end == -1:
            pos = match.end()
            continue

        entry_body = content[brace_start + 1:brace_end]
        raw = content[match.start():brace_end + 1]

        # Parse the entry
        entry = _parse_entry_body(entry_type, entry_body, raw)
        if entry:
            entries.append(entry)

        pos = brace_end + 1

    return entries


def _parse_entry_body(entry_type: str, body: str, raw: str) -> BibEntry | None:
    """Parse the body of a BibTeX entry."""
    # The key is the first part before the first comma
    # But we need to handle nested braces in the key area

    # Find the first comma at depth 0
    depth = 0
    comma_pos = -1
    for i, c in enumerate(body):
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
        elif c == ',' and depth == 0:
            comma_pos = i
            break

    if comma_pos == -1:
        # No comma found, might be a string/preamble entry
        return None

    key = body[:comma_pos].strip()
    fields_str = body[comma_pos + 1:]

    # Handle special entry types
    if entry_type in ('string', 'preamble', 'comment'):
        return None

    # Parse fields
    fields = _parse_fields(fields_str)

    return BibEntry(
        entry_type=entry_type,
        key=key,
        fields=fields,
        raw=raw,
    )


def _parse_fields(fields_str: str) -> dict[str, str]:
    """Parse BibTeX fields from entry body."""
    fields = {}

    # Match field = {value} or field = "value" or field = number
    field_pattern = re.compile(r'(\w+)\s*=\s*')

    pos = 0
    while pos < len(fields_str):
        # Skip whitespace and commas
        while pos < len(fields_str) and fields_str[pos] in ' \t\n\r,':
            pos += 1

        if pos >= len(fields_str):
            break

        # Try to match field name
        match = field_pattern.match(fields_str, pos)
        if not match:
            pos += 1
            continue

        field_name = match.group(1).lower()
        pos = match.end()

        # Skip whitespace
        while pos < len(fields_str) and fields_str[pos] in ' \t\n\r':
            pos += 1

        if pos >= len(fields_str):
            break

        # Parse value
        value, pos = _parse_value(fields_str, pos)
        if field_name and value is not None:
            fields[field_name] = value

    return fields


def _parse_value(text: str, pos: int) -> tuple[str, int]:
    """Parse a BibTeX value starting at pos."""
    if pos >= len(text):
        return '', pos

    char = text[pos]

    if char == '{':
        # Brace-enclosed value
        end = _find_matching_brace(text, pos)
        if end == -1:
            return '', pos + 1
        return text[pos + 1:end], end + 1

    elif char == '"':
        # Quote-enclosed value
        depth = 0
        i = pos + 1
        while i < len(text):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
            elif text[i] == '"' and depth == 0:
                return text[pos + 1:i], i + 1
            elif text[i] == '\\':
                i += 1
            i += 1
        return text[pos + 1:], len(text)

    else:
        # Unquoted value (number or string reference)
        end = pos
        while end < len(text) and text[end] not in ',}':
            end += 1
        return text[pos:end].strip(), end


def extract_cited_keys(content: str) -> set[str]:
    """Extract all cited keys from LaTeX content."""
    keys = set()

    # Match \cite{key1, key2, ...} and variants
    # Also handles \cite[options]{keys}, \citep, \citet, \autocite, etc.
    cite_pattern = re.compile(
        r'\\(?:cite|citep|citet|citeauthor|citeyear|autocite|nocite|parencite|textcite|fullcite|footcite)'
        r'(?:\[[^\]]*\])?'   # optional [...]
        r'(?:\[[^\]]*\])?'   # second optional [...]
        r'\{([^}]+)\}'
    )

    for match in cite_pattern.finditer(content):
        keys_str = match.group(1)
        for key in keys_str.split(','):
            key = key.strip()
            if key and key != '*':
                keys.add(key)

    return keys


def extract_cited_entries(
    main_file: Path,
    bib_files: list[Path] | None = None,
) -> list[BibEntry]:
    """Extract cited bib entries from LaTeX project.

    Args:
        main_file: Path to main .tex file
        bib_files: Optional list of .bib files. If None, auto-detect from \bibliography

    Returns:
        List of cited BibEntry objects
    """
    # Read main file
    try:
        content = main_file.read_text(encoding='utf-8')
    except Exception:
        return []

    # Collect cited keys (including from included files)
    all_keys = _collect_cited_keys(main_file, content)

    # Find bib files if not provided
    if bib_files is None:
        bib_files = _find_bib_files(content, main_file.parent)

    # Parse bib files and find matching entries
    cited_entries = []
    seen_keys = set()

    for bib_file in bib_files:
        entries = parse_bib_file(bib_file)
        for entry in entries:
            if entry.key in all_keys and entry.key not in seen_keys:
                cited_entries.append(entry)
                seen_keys.add(entry.key)

    return cited_entries


def _collect_cited_keys(main_file: Path, content: str) -> set[str]:
    """Collect all cited keys from main file and included files."""
    from .dependency import INCLUDE_PATTERN

    keys = extract_cited_keys(content)

    # Also process included files
    base_dir = main_file.parent
    for match in INCLUDE_PATTERN.finditer(content):
        file_ref = match.group(1).strip()
        if not file_ref.endswith('.tex'):
            file_ref += '.tex'
        inc_path = base_dir / file_ref
        if inc_path.exists():
            try:
                inc_content = inc_path.read_text(encoding='utf-8')
                keys.update(extract_cited_keys(inc_content))
                # Recursively process nested includes
                keys.update(_collect_cited_keys(inc_path, inc_content))
            except Exception:
                pass

    return keys


def _find_bib_files(content: str, base_dir: Path) -> list[Path]:
    """Find bib files from \\bibliography command."""
    bib_files = []

    # Match \bibliography{file1, file2}
    bib_pattern = re.compile(r'\\bibliography\{([^}]+)\}')
    for match in bib_pattern.finditer(content):
        refs = match.group(1)
        for ref in refs.split(','):
            ref = ref.strip()
            if ref:
                bib_path = base_dir / ref
                if not bib_path.suffix:
                    bib_path = bib_path.with_suffix('.bib')
                if bib_path.exists():
                    bib_files.append(bib_path)

    # Also check \addbibresource
    addbib_pattern = re.compile(r'\\addbibresource\{([^}]+)\}')
    for match in addbib_pattern.finditer(content):
        ref = match.group(1).strip()
        if ref:
            bib_path = base_dir / ref
            if not bib_path.suffix:
                bib_path = bib_path.with_suffix('.bib')
            if bib_path.exists():
                bib_files.append(bib_path)

    return bib_files


def format_bib_entry(entry: BibEntry) -> str:
    """Format a BibTeX entry as string."""
    parts = [f"@{entry.entry_type}{{{entry.key},"]

    for field_name, field_value in entry.fields.items():
        parts.append(f"  {field_name} = {{{field_value}}},")

    parts.append("}")

    return '\n'.join(parts)


def format_bib_entries(entries: list[BibEntry]) -> str:
    """Format multiple BibTeX entries."""
    return '\n\n'.join(format_bib_entry(e) for e in entries) + '\n'
