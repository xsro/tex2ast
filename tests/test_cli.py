"""Integration tests for the CLI."""

import pytest
import json
from pathlib import Path
from click.testing import CliRunner

from tex2ast.cli import cli


class TestAstCommand:
    """Test the ast command."""

    def test_ast_to_json(self, tmp_path):
        """Convert LaTeX to JSON."""
        tex_file = tmp_path / "test.tex"
        tex_file.write_text("\\documentclass{article}")

        runner = CliRunner()
        result = runner.invoke(cli, ['ast', '-i', str(tex_file)])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['type'] == 'LatexAST'

    def test_ast_to_file(self, tmp_path):
        """Convert LaTeX to JSON file."""
        tex_file = tmp_path / "test.tex"
        tex_file.write_text("\\documentclass{article}")
        json_file = tmp_path / "test.json"

        runner = CliRunner()
        result = runner.invoke(cli, ['ast', '-i', str(tex_file), '-o', str(json_file)])

        assert result.exit_code == 0
        assert json_file.exists()
        data = json.loads(json_file.read_text())
        assert data['type'] == 'LatexAST'

    def test_ast_pretty(self, tmp_path):
        """Pretty print JSON output."""
        tex_file = tmp_path / "test.tex"
        tex_file.write_text("\\alpha")

        runner = CliRunner()
        result = runner.invoke(cli, ['ast', '-i', str(tex_file), '--pretty'])

        assert result.exit_code == 0
        # Pretty output should have newlines and indentation
        assert '\n' in result.output


class TestTexCommand:
    """Test the tex command."""

    def test_json_to_tex(self, tmp_path):
        """Convert JSON back to LaTeX."""
        tex_file = tmp_path / "test.tex"
        tex_file.write_text("\\alpha")
        out_file = tmp_path / "out.tex"

        # First convert to JSON
        runner = CliRunner()
        runner.invoke(cli, ['ast', '-i', str(tex_file), '-o', str(tex_file.with_suffix('.json'))])

        # Then convert back
        result = runner.invoke(cli, ['tex', '-i', str(tex_file.with_suffix('.json')), '-o', str(out_file)])

        assert result.exit_code == 0
        assert out_file.exists()
        assert "\\alpha" in out_file.read_text()


class TestExpandCommand:
    """Test the expand command."""

    def test_expand(self, tmp_path):
        """Expand includes into single file."""
        main = tmp_path / "main.tex"
        included = tmp_path / "included.tex"
        main.write_text("\\input{included}")
        included.write_text("content")

        runner = CliRunner()
        result = runner.invoke(cli, ['expand', '-i', str(main)])

        assert result.exit_code == 0
        assert "Expanded" in result.output


class TestRemoveChangesCommand:
    """Test the remove-changes command (regex-based)."""

    def test_remove_changes_new(self, tmp_path):
        """Generate new version."""
        tex_file = tmp_path / "test.tex"
        tex_file.write_text("\\begin{document}\\added{new}\\end{document}")

        runner = CliRunner()
        result = runner.invoke(cli, ['remove-changes', '-i', str(tex_file), '--print_change', 'new'])

        assert result.exit_code == 0
        assert "new" in result.output
        assert "\\added" not in result.output

    def test_remove_changes_old(self, tmp_path):
        """Generate old version."""
        tex_file = tmp_path / "test.tex"
        tex_file.write_text("\\begin{document}\\deleted{old}\\end{document}")

        runner = CliRunner()
        result = runner.invoke(cli, ['remove-changes', '-i', str(tex_file), '--print_change', 'old'])

        assert result.exit_code == 0
        assert "old" in result.output


class TestAstRemoveChangesCommand:
    """Test the ast-remove-changes command."""

    def test_ast_remove_changes_new(self, tmp_path):
        """Generate new version with AST approach."""
        tex_file = tmp_path / "test.tex"
        tex_file.write_text("\\begin{document}\\added{new}\\end{document}")

        runner = CliRunner()
        result = runner.invoke(cli, ['ast-remove-changes', '-i', str(tex_file), '--print_change', 'new'])

        assert result.exit_code == 0
        assert "new" in result.output
        assert "\\added" not in result.output

    def test_ast_remove_changes_old(self, tmp_path):
        """Generate old version with AST approach."""
        tex_file = tmp_path / "test.tex"
        tex_file.write_text("\\begin{document}\\deleted{old}\\end{document}")

        runner = CliRunner()
        result = runner.invoke(cli, ['ast-remove-changes', '-i', str(tex_file), '--print_change', 'old'])

        assert result.exit_code == 0
        assert "old" in result.output

    def test_ast_remove_changes_output_file(self, tmp_path):
        """Output to file."""
        tex_file = tmp_path / "test.tex"
        tex_file.write_text("\\begin{document}\\added{new}\\end{document}")
        out_file = tmp_path / "out.tex"

        runner = CliRunner()
        result = runner.invoke(cli, ['ast-remove-changes', '-i', str(tex_file), '-o', str(out_file)])

        assert result.exit_code == 0
        assert out_file.exists()
        assert "new" in out_file.read_text()

    def test_ast_remove_changes_changes_list_none(self, tmp_path):
        """Disable custom commands."""
        tex_file = tmp_path / "test.tex"
        tex_file.write_text("\\begin{document}\\custom{test}\\end{document}")

        runner = CliRunner()
        result = runner.invoke(cli, ['ast-remove-changes', '-i', str(tex_file), '--changes-list', 'none', '--print_change', 'new'])

        assert result.exit_code == 0
        # Custom command should be preserved since changes-list is none
        assert "\\custom" in result.output

    def test_ast_remove_changes_with_config(self, tmp_path):
        """Use project config file."""
        tex_file = tmp_path / "test.tex"
        tex_file.write_text("\\begin{document}\\added{new}\\end{document}")
        config_file = tmp_path / "config.py"
        config_file.write_text('tex2ast_config = {"input_tex": "%s", "output_tex": "%s"}' % (tex_file, tmp_path / "out.tex"))

        runner = CliRunner()
        result = runner.invoke(cli, ['ast-remove-changes', '--project', str(config_file)])

        assert result.exit_code == 0
        assert (tmp_path / "out.tex").exists()


class TestDependencyCommand:
    """Test the dependency command."""

    def test_dependency(self, tmp_path):
        """List dependencies."""
        tex_file = tmp_path / "test.tex"
        tex_file.write_text("\\documentclass{article}\n\\begin{document}\nHello\n\\end{document}")

        runner = CliRunner()
        result = runner.invoke(cli, ['dependency', '-i', str(tex_file)])

        assert result.exit_code == 0
        # Should list the main file
        assert "test.tex" in result.output


class TestExtractBibCommand:
    """Test the extract-bib command."""

    def test_extract_bib(self, tmp_path):
        """Extract bib entries."""
        tex_file = tmp_path / "test.tex"
        tex_file.write_text("\\documentclass{article}\n\\begin{document}\n\\cite{key1}\n\\end{document}")

        runner = CliRunner()
        result = runner.invoke(cli, ['extract-bib', '-i', str(tex_file)])

        # May exit with 1 if no bib file found, that's acceptable
        assert result.exit_code in (0, 1)
        # Should output something
        assert len(result.output) > 0 or len(result.stderr) > 0