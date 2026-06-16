"""LaTeX build tool - run compilers sequentially with log-based file tracking."""

import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path


TOOL_COMMANDS = {
    "xelatex": "xelatex",
    "pdflatex": "pdflatex",
    "biber": "biber",
    "biblatex": "biber",
    "bibtex": "bibtex",
}

STEP_ALIASES = {
    "pdf": ["pdflatex"],
    "xe": ["xelatex"],
    "pdf2": ["pdflatex", "pdflatex"],
    "xe2": ["xelatex", "xelatex"],
    "pdf3": ["pdflatex", "pdflatex", "pdflatex"],
    "xe3": ["xelatex", "xelatex", "xelatex"],
    "br": ["biber"],
    "bt": ["bibtex"],
}

TEX_TOOLS = {"xelatex", "pdflatex"}
BIB_TOOLS = {"biber", "biblatex", "bibtex"}

TEX_FLAGS = ["-interaction=nonstopmode", "-halt-on-error"]


def expand_steps(steps: list[str]) -> list[str]:
    """Expand step aliases (e.g. 'xe2' -> ['xelatex', 'xelatex'])."""
    expanded = []
    for step in steps:
        key = step.lower()
        if key in STEP_ALIASES:
            expanded.extend(STEP_ALIASES[key])
        else:
            expanded.append(step)
    return expanded


def _timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _join_wrapped_lines(content: str) -> str:
    """Join LaTeX log lines broken by 80-char line wrapping.

    When a path like ./foo/bar.pdf is split across lines, the first line
    ends with a word boundary (letter/digit) and the next line starts with
    a continuation that looks like an extension or path segment.
    """
    lines = content.split('\n')
    joined = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if (i + 1 < len(lines)
                and re.search(r'[\w/\.\-][/\.\-]$', line)
                and re.match(r'[\w/\.\-]', lines[i + 1])):
            line = line + lines[i + 1]
            i += 1
        joined.append(line)
        i += 1
    return '\n'.join(joined)


# Known file extensions in LaTeX logs
_TEX_EXTENSIONS = (
    'tex', 'sty', 'cls', 'bib', 'def', 'fd', 'cfg', 'ltx', 'sto',
    'pfb', 'pdf', 'png', 'jpg', 'jpeg', 'eps', 'svg', 'tikz',
    'code.tex', 'mkii',
)


def _parse_tex_log_files(log_content: str, base_dir: Path) -> set[str]:
    """Parse LaTeX log to extract all opened files.

    LaTeX log entries: (./file.tex  or  (d:/path/file.sty
    Paths may contain spaces in directory names like 'dir (1)/file.tex'.
    """
    content = _join_wrapped_lines(log_content)
    files = set()

    # Find all path-like sequences starting with ./ ../ or X:/
    # Scan character by character, allowing spaces when followed by valid path chars
    for line in content.split('\n'):
        # Look for path starts: ( or < followed by ./ ../ or X:/
        for m in re.finditer(r'[<(](\.{1,2}[\\/]|[A-Za-z]:[\\/])', line):
            start = m.start() + 1  # position after ( or <
            # Scan forward to extract the full path
            j = start
            n = len(line)
            last_ext_end = -1  # track last valid extension position

            while j < n:
                c = line[j]
                if c in ')>\n':
                    break
                if c == ' ':
                    # Space: check if this looks like a path continues after it
                    # Valid: " (1)/", " (2)/", or just end of path
                    rest = line[j:]
                    if re.match(r' \(\d+\)[\\/]', rest):
                        j += len(re.match(r' \(\d+\)[\\/]', rest).group(0))
                        continue
                    # Check if we already found a valid extension - stop here
                    if last_ext_end > 0:
                        break
                    # Otherwise, this might be end of path in log content
                    break
                j += 1
                # Check if current position ends a known extension
                for ext in _TEX_EXTENSIONS:
                    if line[:j].endswith('.' + ext):
                        last_ext_end = j
                        break

            if last_ext_end > 0:
                path = line[start:last_ext_end].strip()
            else:
                path = line[start:j].strip()

            if path.startswith('\\') or len(path) < 3:
                continue
            try:
                p = Path(path)
                if not p.is_absolute():
                    p = (base_dir / p).resolve()
                files.add(str(p))
            except (ValueError, OSError):
                files.add(path)

    return files


def _parse_biber_log(log_path: Path) -> set[str]:
    """Parse biber log file to find read .bib files."""
    files = set()
    if not log_path.exists():
        return files
    try:
        content = log_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return files
    for m in re.finditer(r'Reading\s+(\S+\.bib)', content):
        bib = Path(m.group(1))
        if not bib.is_absolute():
            bib = log_path.parent / bib
        files.add(str(bib.resolve()))
    return files


def _parse_bibtex_log(log_path: Path, base_dir: Path) -> set[str]:
    """Parse bibtex .blg file to find read .bib files."""
    files = set()
    if not log_path.exists():
        return files
    try:
        content = log_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return files
    for m in re.finditer(r'Database file.*?:\s*(\S+)', content):
        bib = Path(m.group(1))
        if not bib.is_absolute():
            bib = base_dir / bib
        files.add(str(bib.resolve()))
    return files


def extract_zip_project(zip_path: Path, main_file: str) -> Path:
    """Extract a zip archive to a temp directory and return the main .tex path.

    Args:
        zip_path: Path to the .zip file
        main_file: Relative path to the main .tex file inside the zip

    Returns:
        Path to the extracted main .tex file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    extract_dir = Path(tempfile.gettempdir()) / "tex2ast" / timestamp
    extract_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(extract_dir)

    tex_file = extract_dir / main_file
    if not tex_file.exists():
        raise FileNotFoundError(f"Main file '{main_file}' not found in zip archive")

    return tex_file.resolve()


def _build_tool_args(tool: str, tex_file: Path) -> list[str]:
    """Build command-line arguments for a tool."""
    cmd = TOOL_COMMANDS[tool]
    if tool in BIB_TOOLS:
        return [cmd, tex_file.stem]
    else:
        return [cmd, *TEX_FLAGS, str(tex_file)]


# Extensions considered as LaTeX source (not packed)
_LATEX_SOURCE_EXTS = {
    '.tex', '.sty', '.cls', '.def', '.fd', '.cfg', '.ltx', '.clo',
    '.bst', '.bbx', '.cbx', '.lbx', '.dbx',
}

# Extensions of packable dependency files
_PACKABLE_EXTS = {
    '.bib', '.pdf', '.png', '.jpg', '.jpeg', '.gif', '.bmp',
    '.eps', '.svg', '.tikz', '.csv', '.dat', '.txt', '.json',
}


def pack_dependency_files(
    tex_file: Path,
    all_files: set[str],
    output: Path,
) -> int:
    """Pack project dependency files into a zip archive.

    Includes main .tex file, .bib, and non-LaTeX files under the project directory.
    Excludes TeX system files (texmf-dist).

    Args:
        tex_file: Path to main .tex file
        all_files: Set of absolute file paths from build
        output: Output zip file path

    Returns:
        Number of files packed
    """
    base_dir = tex_file.parent
    main_tex = tex_file.resolve()

    packable = []
    seen = set()

    # Always include the main .tex file
    if main_tex.exists():
        packable.append(main_tex)
        seen.add(str(main_tex))

    # Include other .tex files from the project (not texmf)
    for fpath_str in all_files:
        fpath = Path(fpath_str)

        if 'texmf' in str(fpath).lower():
            continue

        try:
            fpath.resolve().relative_to(base_dir.resolve())
        except ValueError:
            continue

        resolved = str(fpath.resolve())
        if resolved in seen:
            continue

        if fpath.suffix.lower() in _PACKABLE_EXTS or fpath.suffix.lower() in _LATEX_SOURCE_EXTS:
            packable.append(fpath)
            seen.add(resolved)

    if not packable:
        return 0

    packable.sort()
    output.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as zf:
        for fpath in packable:
            arcname = fpath.resolve().relative_to(base_dir.resolve())
            zf.write(fpath, arcname)

    return len(packable)


def run_build(
    tex_file: Path,
    steps: list[str],
    log_dir: Path,
) -> tuple[bool, set[str]]:
    """Run LaTeX build steps sequentially.

    Args:
        tex_file: Path to main .tex file
        steps: List of tool names
        log_dir: Directory for log files

    Returns:
        Tuple of (success, all_files) where all_files is the set of files read
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    build_log = log_dir / "build.log"
    io_log = log_dir / "build-io.log"

    build_log.write_text("", encoding="utf-8")
    io_log.write_text("", encoding="utf-8")

    base_dir = tex_file.parent
    all_success = True
    all_files: set[str] = set()

    for i, tool in enumerate(steps):
        tool_lower = tool.lower()
        if tool_lower not in TOOL_COMMANDS:
            with open(build_log, "a", encoding="utf-8") as f:
                f.write(f"[{_timestamp()}] ERROR: unknown tool '{tool}'\n")
            print(f"Error: unknown tool '{tool}'. Valid: {', '.join(TOOL_COMMANDS)}")
            return False, all_files

        args = _build_tool_args(tool_lower, tex_file)
        step_label = f"[{i+1}/{len(steps)}] {tool_lower}"

        with open(build_log, "a", encoding="utf-8") as f:
            f.write(f"[{_timestamp()}] START {step_label}: {' '.join(args)}\n")
            f.write(f"  cwd={base_dir}\n\n")

        print(f"{step_label} running: {' '.join(args)}")

        try:
            env = {**os.environ, "max_print_line": "10000"}
            proc = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=str(base_dir),
                env=env,
            )
            stdout, _ = proc.communicate()
        except FileNotFoundError:
            with open(build_log, "a", encoding="utf-8") as f:
                f.write(f"[{_timestamp()}] ERROR: '{args[0]}' not found on PATH\n\n")
            print(f"Error: '{args[0]}' not found. Is it installed?")
            return False, all_files

        output = stdout.decode("utf-8", errors="replace") if stdout else ""
        with open(build_log, "a", encoding="utf-8") as f:
            if output:
                f.write(output)
                if not output.endswith("\n"):
                    f.write("\n")
            f.write(f"\n[{_timestamp()}] END {step_label} (exit={proc.returncode})\n\n")

        # Parse tex log for opened files
        if tool_lower in TEX_TOOLS:
            tex_log = base_dir / (tex_file.stem + ".log")
            if tex_log.exists():
                try:
                    log_content = tex_log.read_text(encoding="utf-8", errors="replace")
                    all_files.update(_parse_tex_log_files(log_content, base_dir))
                except Exception:
                    pass

        # Parse biber log for .bib files
        if tool_lower in ("biber", "biblatex"):
            all_files.update(_parse_biber_log(base_dir / (tex_file.stem + ".blg")))

        # Parse bibtex log for .bib files
        if tool_lower == "bibtex":
            all_files.update(_parse_bibtex_log(base_dir / (tex_file.stem + ".blg"), base_dir))

        if proc.returncode != 0:
            print(f"{step_label} finished with exit code {proc.returncode}")
            all_success = False
        else:
            print(f"{step_label} done")

    # Write summary of all read files
    if all_success and all_files:
        with open(io_log, "a", encoding="utf-8") as f:
            f.write(f"[{_timestamp()}] === All files read during build ===\n")
            for fp in sorted(all_files):
                f.write(f"{fp}\n")
            f.flush()

    return all_success, all_files
