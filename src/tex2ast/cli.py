"""Command-line interface for tex2ast."""

import json
import sys
from pathlib import Path
from typing import Optional

import click

from .lexer import LatexLexer
from .parser import LatexParser
from .ast_nodes import LatexAST, ASTNode


def ast_to_dict(node) -> dict:
    """Convert AST node to dictionary."""
    if node is None:
        return None

    if isinstance(node, (str, int, float, bool)):
        return node

    if isinstance(node, LatexAST):
        return {
            'type': 'LatexAST',
            'children': [ast_to_dict(child) for child in node.children],
            'metadata': node.metadata,
        }

    # Get all fields from the dataclass
    result = {'type': node.__class__.__name__}

    for field_name, field_value in node.__dict__.items():
        if field_name.startswith('_'):
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


@click.command()
@click.option('--input', '-i', 'input_file',
              type=click.Path(exists=True),
              help='Input LaTeX file path')
@click.option('--output', '-o', 'output_file',
              type=click.Path(),
              help='Output JSON file path')
@click.option('--pretty', '-p',
              is_flag=True,
              default=False,
              help='Pretty print JSON output')
@click.option('--encoding', '-e',
              default='utf-8',
              help='Input file encoding')
def main(input_file: Optional[str], output_file: Optional[str],
         pretty: bool, encoding: str):
    """Convert LaTeX file to AST in JSON format.

    Examples:

        ast --input document.tex --output document.json

        ast -i document.tex -o document.json --pretty

        cat document.tex | ast -o document.json
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
        # Read from stdin
        if sys.stdin.isatty():
            click.echo("Error: No input file specified and no stdin input", err=True)
            click.echo("Use --input to specify a file or pipe input via stdin", err=True)
            sys.exit(1)
        latex_content = sys.stdin.read()

    # Parse LaTeX
    try:
        lexer = LatexLexer(latex_content)
        tokens = lexer.get_tokens()

        parser = LatexParser(tokens)
        ast = parser.parse()

        # Convert to dict
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
            click.echo(f"AST written to {output_file}")
        else:
            click.echo(json_output)

    except Exception as e:
        click.echo(f"Error writing output: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
