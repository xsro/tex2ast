"""Command-line interface for tex2ast."""

import json
import sys
import tempfile
from pathlib import Path
from typing import Optional

import click

from .lexer import LatexLexer
from .parser import LatexParser
from .serializer import LatexSerializer
from .ast_nodes import LatexAST, ASTNode, SourcePos, SourceRange
from .remove_changes import expand_and_remove_changes
from .ast_remove_changes import ast_remove_changes as ast_remove_changes_ast, parse_changes_list
from .dependency import collect_all_dependencies, find_unreferenced_files, format_dependencies
from .bib_parser import extract_cited_entries, format_bib_entries, _find_bib_files
from .build import run_build, pack_dependency_files, extract_zip_project, expand_steps, TOOL_COMMANDS, STEP_ALIASES
from .expand import expand_latex


# --- AST <-> dict conversion ---

def _pos_to_dict(pos) -> Optional[dict]:
    if pos is None:
        return None
    if isinstance(pos, SourceRange):
        return {
            'start': {'line': pos.start.line, 'column': pos.start.column, 'offset': pos.start.offset},
            'end': {'line': pos.end.line, 'column': pos.end.column, 'offset': pos.end.offset},
        }
    return None


def _dict_to_pos(d) -> Optional[SourceRange]:
    if d is None:
        return None
    if isinstance(d, dict) and 'start' in d and 'end' in d:
        s = d['start']
        e = d['end']
        return SourceRange(
            start=SourcePos(line=s.get('line', 0), column=s.get('column', 0), offset=s.get('offset', 0)),
            end=SourcePos(line=e.get('line', 0), column=e.get('column', 0), offset=e.get('offset', 0)),
        )
    return None


def ast_to_dict(node) -> dict:
    """Convert AST node to dictionary."""
    if node is None:
        return None

    if isinstance(node, (str, int, float, bool)):
        return node

    if isinstance(node, LatexAST):
        result = {
            'type': 'LatexAST',
            'children': [ast_to_dict(child) for child in node.children],
            'metadata': node.metadata,
        }
        if node.source:
            result['source'] = node.source
        return result

    result = {'type': node.__class__.__name__}

    if node.pos is not None:
        result['pos'] = _pos_to_dict(node.pos)

    for field_name, field_value in node.__dict__.items():
        if field_name.startswith('_') or field_name == 'pos':
            continue

        if isinstance(field_value, list):
            result[field_name] = [ast_to_dict(item) for item in field_value]
        elif isinstance(field_value, (str, int, float, bool)):
            result[field_name] = field_value
        elif field_value is None:
            result[field_name] = None
        elif isinstance(field_value, ASTNode):
            result[field_name] = ast_to_dict(field_value)
        else:
            result[field_name] = str(field_value)

    return result


def dict_to_ast(d) -> ASTNode:
    """Convert dictionary to AST node."""
    if d is None:
        return None

    if isinstance(d, (str, int, float, bool)):
        return d

    if not isinstance(d, dict):
        return d

    node_type = d.get('type', '')

    if node_type == 'LatexAST':
        ast = LatexAST(
            children=[dict_to_ast(c) for c in d.get('children', [])],
            metadata=d.get('metadata', {}),
            source=d.get('source', ''),
        )
        return ast

    # Import all node types
    from . import ast_nodes

    cls = getattr(ast_nodes, node_type, None)
    if cls is None or not isinstance(cls, type):
        return None

    pos = _dict_to_pos(d.get('pos'))

    kwargs = {}
    if pos is not None:
        kwargs['pos'] = pos

    for field_name in d:
        if field_name in ('type', 'pos'):
            continue

        field_value = d[field_name]

        if isinstance(field_value, list):
            kwargs[field_name] = [dict_to_ast(item) for item in field_value]
        elif isinstance(field_value, dict) and 'type' in field_value:
            kwargs[field_name] = dict_to_ast(field_value)
        else:
            kwargs[field_name] = field_value

    try:
        return cls(**kwargs)
    except TypeError:
        # Fallback: try with just the basic fields
        return cls(**{k: v for k, v in kwargs.items() if k != 'pos'})


# --- CLI ---

@click.group()
def cli():
    """tex2ast - LaTeX to AST converter with roundtrip support."""
    pass


@cli.command('ast')
@click.option('--input', '-i', 'input_file',
              type=click.Path(exists=True),
              help='Input LaTeX file path')
@click.option('--output', '-o', 'output_file',
              type=click.Path(),
              help='Output JSON file path')
@click.option('--pretty', '-p',
              is_flag=True, default=False,
              help='Pretty print JSON output')
@click.option('--encoding', '-e',
              default='utf-8',
              help='Input file encoding')
def tex_to_ast(input_file: Optional[str], output_file: Optional[str],
               pretty: bool, encoding: str):
    """Convert LaTeX to AST JSON.

    Examples:

        tex2ast ast --input document.tex --output document.json

        tex2ast ast -i document.tex -o document.json --pretty
    """
    # Read input
    if input_file:
        try:
            input_path = Path(input_file)
            latex_content = input_path.read_text(encoding=encoding)
        except Exception as e:
            click.echo(f"Error reading input file: {e}", err=True)
            sys.exit(1)
    else:
        if sys.stdin.isatty():
            click.echo("Error: No input file specified", err=True)
            sys.exit(1)
        latex_content = sys.stdin.read()

    # Parse LaTeX
    try:
        lexer = LatexLexer(latex_content)
        tokens = lexer.get_tokens()

        parser = LatexParser(tokens)
        ast = parser.parse()
        ast.source = latex_content  # Store original source for roundtrip

        result = ast_to_dict(ast)

    except Exception as e:
        click.echo(f"Error parsing LaTeX: {e}", err=True)
        sys.exit(1)

    # Output JSON
    try:
        indent = 2 if pretty else None
        json_output = json.dumps(result, indent=indent, ensure_ascii=False)

        if output_file:
            output_path = Path(output_file)
            output_path.write_text(json_output, encoding='utf-8')
        else:
            click.echo(json_output)

    except Exception as e:
        click.echo(f"Error writing output: {e}", err=True)
        sys.exit(1)


@cli.command('tex')
@click.option('--input', '-i', 'input_file',
              type=click.Path(exists=True),
              help='Input JSON file path')
@click.option('--output', '-o', 'output_file',
              type=click.Path(),
              help='Output LaTeX file path')
@click.option('--encoding', '-e',
              default='utf-8',
              help='Output file encoding')
def ast_to_tex(input_file: Optional[str], output_file: Optional[str],
               encoding: str):
    """Convert AST JSON back to LaTeX.

    If the JSON contains a 'source' field, the original source is output directly
    for perfect roundtrip fidelity. Otherwise, the AST is serialized.

    Examples:

        tex2ast tex --input document.json --output document.tex

        tex2ast tex -i document.json -o document.tex
    """
    # Read input
    if input_file:
        try:
            input_path = Path(input_file)
            json_content = input_path.read_text(encoding='utf-8')
        except Exception as e:
            click.echo(f"Error reading input file: {e}", err=True)
            sys.exit(1)
    else:
        if sys.stdin.isatty():
            click.echo("Error: No input file specified", err=True)
            sys.exit(1)
        json_content = sys.stdin.read()

    # Parse JSON
    try:
        data = json.loads(json_content)
    except json.JSONDecodeError as e:
        click.echo(f"Error parsing JSON: {e}", err=True)
        sys.exit(1)

    # If source is present, use it directly for perfect roundtrip
    source = data.get('source', '')
    if source:
        latex_output = source
    else:
        # Deserialize AST and serialize back to LaTeX
        try:
            ast = dict_to_ast(data)
            if not isinstance(ast, LatexAST):
                click.echo("Error: Root node must be LatexAST", err=True)
                sys.exit(1)

            serializer = LatexSerializer()
            latex_output = serializer.serialize(ast)

        except Exception as e:
            click.echo(f"Error serializing AST: {e}", err=True)
            sys.exit(1)

    # Output LaTeX (use newline='' to preserve exact line endings for roundtrip)
    try:
        if output_file:
            output_path = Path(output_file)
            output_path.write_text(latex_output, encoding=encoding, newline='')
        else:
            click.echo(latex_output, nl=False)

    except Exception as e:
        click.echo(f"Error writing output: {e}", err=True)
        sys.exit(1)


def main():
    cli()


def _load_project_config(config_path: str) -> dict:
    """Load tex2ast.config.py file and return the tex2ast_config dict.

    Uses exec() with sys.dont_write_bytecode to avoid creating
    __pycache__ in the project directory.

    Args:
        config_path: Path to the config .py file

    Returns:
        The tex2ast_config dictionary

    Raises:
        FileNotFoundError: if config file doesn't exist
        ValueError: if config file doesn't define tex2ast_config
    """
    import sys

    config_path = Path(config_path).resolve()
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    # Read and exec the config file content directly
    # Use sys.dont_write_bytecode to prevent .pyc generation in target directory
    source = config_path.read_text(encoding='utf-8')
    namespace = {}
    old_dont_write = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        exec(source, namespace)
    finally:
        sys.dont_write_bytecode = old_dont_write

    if 'tex2ast_config' not in namespace:
        raise ValueError(f"Config file {config_path} does not define 'tex2ast_config'")

    return namespace['tex2ast_config']


def _get_command_config(config: dict, command_name: str) -> dict:
    """Extract command-specific config from tex2ast_config.

    Supports two formats:
    1. Flat format (old): config has keys like 'input_tex', 'output_tex' directly
    2. Nested format (new): config maps command names to their sub-configs
       e.g. {'remove-changes': {...}, 'ast-remove-changes': {...}}

    Args:
        config: The full tex2ast_config dictionary
        command_name: The CLI command name (e.g. 'remove-changes', 'ast-remove-changes')

    Returns:
        The command-specific config dictionary
    """
    # Check if config uses nested format (maps command names to sub-configs)
    if command_name in config and isinstance(config[command_name], dict):
        return config[command_name]
    # Fall back to flat format (backward compatible)
    return config


@cli.command('remove-changes')
@click.option('--input', '-i', 'input_file',
              type=click.Path(exists=True),
              required=False,
              help='Input LaTeX file path (required unless --project specifies input_tex)')
@click.option('--output', '-o', 'output_file',
              type=click.Path(),
              help='Output file path (default: <input>_new.tex or <input>_old.tex)')
@click.option('--old', 'mode_old',
              is_flag=True, default=False,
              help='Generate old version (reject all changes)')
@click.option('--print_change',
              type=click.Choice(['new', 'old', 'no']),
              default=None,
              help='Print result to stdout: new, old, or no')
@click.option('--encoding', '-e',
              default='utf-8',
              help='File encoding')
@click.option('--changes-list',
              default=None,
              help='Path to changes config file, or "none" to disable custom commands')
@click.option('--remove-empty-math',
              is_flag=True, default=False,
              help='Remove empty \\[...\\] and equation environments')
@click.option('--project', 'project_config',
              default=None,
              help='Path to tex2ast.config.py for project-level settings')
def remove_changes(input_file: str, output_file: Optional[str],
                   mode_old: bool, print_change: Optional[str], encoding: str,
                   changes_list: Optional[str], remove_empty_math: bool,
                   project_config: Optional[str]):
    """Remove changes package markup from LaTeX files.

    Supports \\added, \\deleted, \\replaced, \\comment, \\highlight commands.
    Recursively expands \\include and \\input files into a single output.

    Custom revision commands can be configured via .config/remove-changes.txt.
    Use --changes-list=none to disable, or --changes-list=<path> for custom config.

    Without -o, defaults to <input>_new.tex or <input>_old.tex.

    Examples:

        tex2ast remove-changes -i document.tex

        tex2ast remove-changes -i document.tex --old

        tex2ast remove-changes -i document.tex -o clean.tex

        tex2ast remove-changes -i document.tex --print_change new

        tex2ast remove-changes -i document.tex --changes-list=none

        tex2ast remove-changes -i document.tex --changes-list=myconfig.txt

        tex2ast remove-changes -i document.tex --remove-empty-math

        tex2ast remove-changes --project tex2ast.config.py
    """
    from pathlib import Path
    from .remove_changes import get_changes_commands

    # Load project config if specified
    config_overrides = {}
    if project_config:
        config = _load_project_config(project_config)
        config_overrides = _get_command_config(config, 'remove-changes')

    # Apply config defaults (CLI options take precedence)
    config_dir = Path(project_config).resolve().parent if project_config else None
    if 'input_tex' in config_overrides and not input_file:
        input_file = config_overrides['input_tex']
        if config_dir and not Path(input_file).is_absolute():
            input_file = str(config_dir / input_file)
    if 'output_tex' in config_overrides and not output_file:
        output_file = config_overrides['output_tex']
        if config_dir and not Path(output_file).is_absolute():
            output_file = str(config_dir / output_file)
    if 'remove_empty_math' in config_overrides and not remove_empty_math:
        remove_empty_math = config_overrides['remove_empty_math']

    # Validate input file
    if not input_file:
        click.echo("Error: --input is required (or specify input_tex in project config)", err=True)
        sys.exit(1)

    # Handle changes_list from config (as inline text, not file path)
    if 'changes_list' in config_overrides and changes_list is None:
        # Write the changes_list text to a temp file and use it
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(config_overrides['changes_list'])
            changes_list = f.name

    mode = 'old' if mode_old else 'new'
    input_path = Path(input_file).resolve()

    # Get custom commands from config
    custom_commands = get_changes_commands(changes_list)

    # Default output: <stem>_new.tex or <stem>_old.tex
    if not output_file:
        suffix = '_old' if mode_old else '_new'
        output_file = str(input_path.parent / (input_path.stem + suffix + '.tex'))

    # Expand includes and strip changes
    result = expand_and_remove_changes(input_path, mode, custom_commands=custom_commands, remove_empty=remove_empty_math)
    output_path = Path(output_file)
    output_path.write_text(result, encoding=encoding)

    # Print result if requested
    if print_change == 'no':
        pass  # silent
    elif print_change is not None:
        # Print the requested version (reuse result if same mode)
        print_mode = print_change
        if print_mode == mode:
            click.echo(result, nl=False)
        else:
            click.echo(
                expand_and_remove_changes(
                    input_path, print_mode, custom_commands=custom_commands,
                    remove_empty=remove_empty_math
                ),
                nl=False
            )
    else:
        click.echo(f"Written to: {output_path}")


@cli.command('ast-remove-changes')
@click.option('--input', '-i', 'input_file',
              type=click.Path(exists=True),
              required=False,
              help='Input LaTeX file path (required unless --project specifies input_tex)')
@click.option('--output', '-o', 'output_file',
              type=click.Path(),
              help='Output file path (default: <input>_new.tex or <input>_old.tex)')
@click.option('--old', 'mode_old',
              is_flag=True, default=False,
              help='Generate old version (reject all changes)')
@click.option('--print_change',
              type=click.Choice(['new', 'old', 'no']),
              default=None,
              help='Print result to stdout: new, old, or no')
@click.option('--encoding', '-e',
              default='utf-8',
              help='File encoding')
@click.option('--changes-list',
              default=None,
              help='Path to changes config file, or "none" to disable custom commands')
@click.option('--remove-empty-math',
              is_flag=True, default=False,
              help='Remove empty \\[...\\] and equation environments')
@click.option('--project', 'project_config',
              default=None,
              help='Path to tex2ast.config.py for project-level settings')
def ast_remove_changes(input_file: str, output_file: Optional[str],
                       mode_old: bool, print_change: Optional[str], encoding: str,
                       changes_list: Optional[str], remove_empty_math: bool,
                       project_config: Optional[str]):
    """Remove changes package markup from LaTeX files using AST-based approach.

    Uses AST transformation instead of regex for more robust processing.
    Supports \\added, \\deleted, \\replaced, \\comment, \\highlight commands.
    Recursively expands \\include and \\input files into a single output.

    Custom revision commands can be configured via .config/remove-changes.txt.
    Use --changes-list=none to disable, or --changes-list=<path> for custom config.

    Without -o, defaults to <input>_new.tex or <input>_old.tex.

    Examples:

        tex2ast ast-remove-changes -i document.tex

        tex2ast ast-remove-changes -i document.tex --old

        tex2ast ast-remove-changes -i document.tex -o clean.tex

        tex2ast ast-remove-changes -i document.tex --print_change new

        tex2ast ast-remove-changes -i document.tex --changes-list=none

        tex2ast ast-remove-changes -i document.tex --remove-empty-math

        tex2ast ast-remove-changes --project tex2ast.config.py
    """
    from pathlib import Path
    from .remove_changes import get_changes_commands

    # Load project config if specified
    config_overrides = {}
    if project_config:
        config = _load_project_config(project_config)
        config_overrides = _get_command_config(config, 'ast-remove-changes')

    # Apply config defaults (CLI options take precedence)
    config_dir = Path(project_config).resolve().parent if project_config else None
    if 'input_tex' in config_overrides and not input_file:
        input_file = config_overrides['input_tex']
        if config_dir and not Path(input_file).is_absolute():
            input_file = str(config_dir / input_file)
    if 'output_tex' in config_overrides and not output_file:
        output_file = config_overrides['output_tex']
        if config_dir and not Path(output_file).is_absolute():
            output_file = str(config_dir / output_file)
    if 'remove_empty_math' in config_overrides and not remove_empty_math:
        remove_empty_math = config_overrides['remove_empty_math']

    # Validate input file
    if not input_file:
        click.echo("Error: --input is required (or specify input_tex in project config)", err=True)
        sys.exit(1)

    # Handle changes_list from config (as inline text, not file path)
    if 'changes_list' in config_overrides and changes_list is None:
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(config_overrides['changes_list'])
            changes_list = f.name

    mode = 'old' if mode_old else 'new'
    input_path = Path(input_file).resolve()

    # Parse changes list for AST version
    if changes_list == 'none':
        changes_list_dict = {}
    elif changes_list:
        # Read custom changes list from file
        with open(changes_list, 'r') as f:
            changes_list_dict = parse_changes_list(f.read())
    else:
        # Default changes list (empty - standard commands are handled separately)
        changes_list_dict = {}

    # Default output: <stem>_new.tex or <stem>_old.tex
    if not output_file:
        suffix = '_old' if mode_old else '_new'
        output_file = str(input_path.parent / (input_path.stem + suffix + '.tex'))

    # Expand includes and strip changes using AST approach
    result = ast_remove_changes_ast(input_path, mode, changes_list=changes_list_dict, remove_empty=remove_empty_math)
    output_path = Path(output_file)
    output_path.write_text(result, encoding=encoding)

    # Print result if requested
    if print_change == 'no':
        pass  # silent
    elif print_change is not None:
        # Print the requested version (reuse result if same mode)
        print_mode = print_change
        if print_mode == mode:
            click.echo(result, nl=False)
        else:
            click.echo(
                ast_remove_changes_ast(
                    input_path, print_mode, changes_list=changes_list_dict,
                    remove_empty=remove_empty_math
                ),
                nl=False
            )
    else:
        click.echo(f"Written to: {output_path}")


@cli.command('dependency')
@click.option('--input', '-i', 'input_file',
              type=click.Path(exists=True),
              required=True,
              help='Input LaTeX main file')
@click.option('--clean_dir',
              type=click.Path(exists=True),
              help='Directory to check for unreferenced files')
@click.option('--run', 'apply',
              is_flag=True, default=False,
              help='Delete unreferenced files in clean_dir')
def dependency(input_file: str, clean_dir: Optional[str], apply: bool):
    """Analyze LaTeX file dependencies.

    Lists all files included/input/used by the LaTeX document.
    With --clean_dir, finds unreferenced files in that directory.

    Examples:

        tex2ast dependency -i document.tex

        tex2ast dependency -i document.tex --clean_dir ./figures

        tex2ast dependency -i document.tex --clean_dir ./figures --run
    """
    from pathlib import Path

    input_path = Path(input_file).resolve()
    deps = collect_all_dependencies(input_path)

    # Print dependencies
    click.echo(format_dependencies(input_path, deps))

    # Clean directory mode
    if clean_dir:
        clean_path = Path(clean_dir).resolve()
        if not clean_path.is_dir():
            click.echo(f"\nError: {clean_dir} is not a directory", err=True)
            sys.exit(1)

        # Build set of all referenced files (including main file)
        all_referenced = set()
        all_referenced.add(input_path)
        for key in deps:
            all_referenced.update(deps[key])

        # Find unreferenced files
        unreferenced = find_unreferenced_files(clean_path, all_referenced)

        if not unreferenced:
            click.echo(f"\nNo unreferenced files in {clean_dir}")
        else:
            click.echo(f"\nUnreferenced files in {clean_dir} ({len(unreferenced)}):")
            for f in unreferenced:
                click.echo(f"  {f}")

            if apply:
                click.echo("\nDeleting unreferenced files...")
                deleted = 0
                for f in unreferenced:
                    try:
                        f.unlink()
                        click.echo(f"  Deleted: {f}")
                        deleted += 1
                    except Exception as e:
                        click.echo(f"  Error deleting {f}: {e}", err=True)
                click.echo(f"\nDeleted {deleted} file(s)")
            else:
                click.echo(f"\nUse --run to delete these files")


@cli.command('extract-bib')
@click.option('--input', '-i', 'input_file',
              type=click.Path(exists=True),
              required=True,
              help='Input LaTeX main file')
@click.option('--output', '-o', 'output_file',
              type=click.Path(),
              help='Output .bib file path')
@click.option('--bib',
              'bib_files',
              multiple=True,
              type=click.Path(exists=True),
              help='Bib files to search (auto-detect if not specified)')
def extract_bib(input_file: str, output_file: str | None, bib_files: tuple[str]):
    """Extract cited bib entries to a new file.

    Finds all \\cite commands in the LaTeX project and exports matching
    BibTeX entries to a new file.

    Examples:

        tex2ast extract-bib -i document.tex -o cited.bib

        tex2ast extract-bib -i document.tex -o cited.bib --bib refs.bib
    """
    from pathlib import Path

    input_path = Path(input_file).resolve()

    # Resolve bib files
    bib_paths = [Path(f).resolve() for f in bib_files] if bib_files else None

    # Extract cited entries
    entries = extract_cited_entries(input_path, bib_paths)

    if not entries:
        click.echo("No cited entries found.", err=True)
        sys.exit(1)

    # Format output
    bib_output = format_bib_entries(entries)

    if output_file:
        output_path = Path(output_file)
        output_path.write_text(bib_output, encoding='utf-8')
        click.echo(f"Exported {len(entries)} entry(ies) to {output_file}")
    else:
        click.echo(bib_output, nl=False)


@cli.command('expand')
@click.option('--input', '-i', 'input_file',
              type=click.Path(exists=True),
              required=True,
              help='Input LaTeX main file')
@click.option('--output', '-o', 'output_file',
              type=click.Path(),
              help='Output expanded file (default: <input>_expanded.tex)')
@click.option('--encoding', '-e',
              default='utf-8',
              help='File encoding')
def expand(input_file: str, output_file: Optional[str], encoding: str):
    """Expand \\input and \\include into a single LaTeX file.

    Recursively replaces \\input{...} and \\include{...} with the actual
    file contents, producing a single self-contained .tex file.

    Examples:

        tex2ast expand -i main.tex

        tex2ast expand -i main.tex -o merged.tex
    """
    input_path = Path(input_file).resolve()

    if not output_file:
        output_file = str(input_path.parent / (input_path.stem + '_expanded.tex'))

    result = expand_latex(input_path)

    output_path = Path(output_file)
    output_path.write_text(result, encoding=encoding)
    click.echo(f"Expanded to: {output_path}")


@cli.command('build')
@click.option('--input', '-i', 'input_file',
              required=True,
              help='Input .tex file or .zip archive')
@click.option('--main', 'main_file',
              default=None,
              help='Main .tex file inside zip (required when --input is a .zip)')
@click.option('--steps',
              required=True,
              help='Comma-separated build steps. Tools: xelatex, pdflatex, biber, bibtex. Aliases: pdf, xe, pdf2, xe2, pdf3, xe3, br, bt')
@click.option('--log-dir',
              type=click.Path(),
              default=str(Path(tempfile.gettempdir())/"tex2ast"/"logs"),
              help='Directory for log files (default: system temp directory)')
@click.option('--pack',
              type=click.Path(),
              default=None,
              help='Pack project dependency files into a zip archive')
def build(input_file: str, main_file: str | None, steps: str, log_dir: str, pack: str | None):
    """Run LaTeX build tools sequentially.

    Compiles the LaTeX project using the specified tools in order.
    Compilation output is saved to build.log, file I/O monitoring to build-io.log.

    Examples:

        tex2ast build -i main.tex --steps xelatex,biber,xelatex,xelatex

        tex2ast build -i main.tex --steps xe,biber,xe2

        tex2ast build -i main.tex --steps pdf2 --log-dir ./logs

        tex2ast build -i main.tex --steps xe,bt,xe2 --pack project.zip

        tex2ast build -i project.zip --main main.tex --steps pdf,bibtex,pdf2
    """
    from_zip = False
    input_path = Path(input_file).resolve()

    if input_path.suffix.lower() == '.zip':
        if not input_path.exists():
            click.echo(f"Error: zip file not found: {input_path}", err=True)
            sys.exit(1)
        if not main_file:
            click.echo("Error: --main is required when --input is a .zip file", err=True)
            sys.exit(1)
        try:
            input_path = extract_zip_project(input_path, main_file)
            from_zip = True
            click.echo(f"Extracted to {input_path.parent}")
        except FileNotFoundError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    else:
        if not input_path.exists():
            click.echo(f"Error: file not found: {input_path}", err=True)
            sys.exit(1)

    log_path = Path(log_dir).resolve()

    step_list = [s.strip() for s in steps.split(',') if s.strip()]
    if not step_list:
        click.echo("Error: no build steps provided", err=True)
        sys.exit(1)

    step_list = expand_steps(step_list)

    valid = ', '.join(TOOL_COMMANDS)
    aliases = ', '.join(STEP_ALIASES)
    for s in step_list:
        if s.lower() not in TOOL_COMMANDS:
            click.echo(f"Error: unknown tool '{s}'. Valid tools: {valid}", err=True)
            click.echo(f"Aliases: {aliases}", err=True)
            sys.exit(1)

    click.echo(f"Building {input_path.name} with {len(step_list)} step(s)")
    click.echo(f"Logs: {log_path / 'build.log'}, {log_path / 'build-io.log'}")
    click.echo()

    success, all_files = run_build(input_path, step_list, log_path)

    click.echo()
    if success:
        click.echo("Build completed successfully.")
    else:
        click.echo("Build finished with errors. Check build.log for details.")
        sys.exit(1)

    # Pack dependency files (skip if input was from zip)
    if pack and not from_zip:
        pack_path = Path(pack).resolve()
        count = pack_dependency_files(input_path, all_files, pack_path)
        if count > 0:
            click.echo(f"Packed {count} file(s) to {pack}")
        else:
            click.echo("No dependency files to pack.")
    elif pack and from_zip:
        click.echo("Skipping --pack (input is from zip archive)")


if __name__ == '__main__':
    main()
