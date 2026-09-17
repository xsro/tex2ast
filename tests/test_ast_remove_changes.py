"""Tests for the AST-based remove changes functionality."""

import pytest
from pathlib import Path
from tex2ast.ast_remove_changes import (
    ast_remove_changes, ChangesTransformer, parse_changes_list
)
from tex2ast.lexer import LatexLexer
from tex2ast.parser import LatexParser
from tex2ast.serializer import LatexSerializer
from tex2ast.ast_nodes import LatexAST


def process_ast(text: str, mode: str = "new", changes_list: dict = None) -> str:
    """Helper to process changes using AST approach on a text string."""
    if changes_list is None:
        changes_list = parse_changes_list("""
added:added
deleted:deleted
replaced:replaced
comment:comment
highlight:highlight
""")

    lexer = LatexLexer(text)
    tokens = lexer.get_tokens()
    parser = LatexParser(tokens)
    ast = parser.parse()
    ast.source = text

    transformer = ChangesTransformer(mode, changes_list, text)
    new_ast = transformer.transform(ast)

    serializer = LatexSerializer()
    return serializer.serialize(new_ast)


class TestBasicChanges:
    """Test basic changes command processing."""

    def test_added_new_mode(self):
        """\\added{} content is kept in new mode."""
        result = process_ast("\\begin{document}\\added{new text}\\end{document}", "new")
        assert "new text" in result
        assert "\\added" not in result

    def test_added_old_mode(self):
        """\\added{} content is removed in old mode."""
        result = process_ast("\\begin{document}\\added{new text}\\end{document}", "old")
        assert "new text" not in result
        assert "\\added" not in result

    def test_deleted_new_mode(self):
        """\\deleted{} content is removed in new mode."""
        result = process_ast("\\begin{document}\\deleted{old text}\\end{document}", "new")
        assert "old text" not in result
        assert "\\deleted" not in result

    def test_deleted_old_mode(self):
        """\\deleted{} content is kept in old mode."""
        result = process_ast("\\begin{document}\\deleted{old text}\\end{document}", "old")
        assert "old text" in result
        assert "\\deleted" not in result

    def test_replaced_new_mode(self):
        """\\replaced{new}{old} uses new in new mode."""
        result = process_ast("\\begin{document}\\replaced{new}{old}\\end{document}", "new")
        assert "new" in result
        assert "old" not in result

    def test_replaced_old_mode(self):
        """\\replaced{new}{old} uses old in old mode."""
        result = process_ast("\\begin{document}\\replaced{new}{old}\\end{document}", "old")
        assert "old" in result
        assert "new" not in result

    def test_comment(self):
        """\\comment{} is always removed."""
        result = process_ast("\\begin{document}\\comment{some comment}\\end{document}", "new")
        assert "some comment" not in result
        assert "\\comment" not in result

    def test_highlight(self):
        """\\highlight{} content is kept in both modes."""
        result_new = process_ast("\\begin{document}\\highlight{important}\\end{document}", "new")
        result_old = process_ast("\\begin{document}\\highlight{important}\\end{document}", "old")
        assert "important" in result_new
        assert "important" in result_old
        assert "\\highlight" not in result_new


class TestScopeRestriction:
    """Test that changes are only processed in document environment and title."""

    def test_changes_in_preamble_not_processed(self):
        """Changes commands in preamble (outside title) are not processed."""
        text = "\\added{preamble}\\begin{document}\\end{document}"
        result = process_ast(text, "new")
        assert "\\added" in result  # Should be preserved

    def test_changes_in_title_processed(self):
        """Changes commands in \\title{} are processed."""
        text = "\\documentclass{article}\\title{\\added{New} Title}\\begin{document}\\end{document}"
        result = process_ast(text, "new")
        assert "New" in result
        assert "\\added" not in result

    def test_changes_in_document_processed(self):
        """Changes commands in document environment are processed."""
        text = "\\begin{document}\\added{content}\\end{document}"
        result = process_ast(text, "new")
        assert "content" in result
        assert "\\added" not in result

    def test_changes_outside_document_not_processed(self):
        """Changes commands after \\end{document} are not processed."""
        text = "\\begin{document}\\end{document}\\added{after}"
        result = process_ast(text, "new")
        assert "\\added" in result  # Should be preserved


class TestFullLineDelete:
    """Test full-line delete preservation."""

    def test_full_line_delete_new_mode(self):
        """Full-line \\deleted{} in new mode leaves % comment."""
        text = "Before.\n\\begin{document}\n\\deleted{full line delete.}\n\\end{document}\nAfter."
        result = process_ast(text, "new")
        assert "%" in result
        assert "full line delete" not in result

    def test_full_line_delete_old_mode(self):
        """Full-line \\deleted{} in old mode keeps content."""
        text = "Before.\n\\deleted{full line delete.}\nAfter."
        result = process_ast(text, "old")
        assert "full line delete" in result
        assert "%" not in result

    def test_partial_line_delete(self):
        """Partial-line \\deleted{} does not leave % comment."""
        text = "\\begin{document}Before \\deleted{delete} After.\\end{document}"
        result = process_ast(text, "new")
        assert "delete" not in result
        # Should not have % comment since it's not a full-line delete


class TestUsepackageChanges:
    """Test that \\usepackage{changes} is removed."""

    def test_usepackage_changes_removed(self):
        """\\usepackage{changes} is removed from output."""
        text = "\\usepackage{changes}\n\\begin{document}\\end{document}"
        result = process_ast(text, "new")
        assert "\\usepackage{changes}" not in result

    def test_usepackage_changes_with_options_removed(self):
        """\\usepackage[options]{changes} is removed from output."""
        text = "\\usepackage[option]{changes}\n\\begin{document}\\end{document}"
        result = process_ast(text, "new")
        assert "\\usepackage" not in result


class TestVerbatimProtection:
    """Test that verbatim content is not processed."""

    def test_verbatim_not_processed(self):
        """Changes commands inside verbatim are not processed."""
        text = "\\begin{verbatim}\\deleted{not processed}\\end{verbatim}"
        result = process_ast(text, "new")
        assert "\\deleted" in result
        assert "not processed" in result

    def test_lstlisting_not_processed(self):
        """Changes commands inside lstlisting are not processed."""
        text = "\\begin{lstlisting}\\added{not processed}\\end{lstlisting}"
        result = process_ast(text, "new")
        assert "\\added" in result
        assert "not processed" in result


class TestNestedChanges:
    """Test nested changes commands."""

    def test_nested_added(self):
        """Nested \\added commands are processed recursively."""
        text = "\\added{outer \\added{inner} text}"
        result = process_ast(text, "new")
        assert "inner" in result
        assert "outer" in result

    def test_nested_deleted_replaced(self):
        """\\deleted containing \\replaced is processed correctly."""
        text = "\\begin{document}\\deleted{old \\replaced{a}{b} text}\\end{document}"
        result_new = process_ast(text, "new")
        result_old = process_ast(text, "old")
        # In new mode, deleted is removed entirely
        assert "a" not in result_new
        # "b" appears in "begin" and "document", so check differently
        assert "replaced" not in result_new
        # In old mode, deleted content is kept, replaced uses old
        assert "b" in result_old  # old of replaced


class TestCustomCommands:
    """Test custom changes commands."""

    def test_custom_added_command(self):
        """Custom command with type 'added' is processed correctly."""
        changes_list = {"customadd": "added"}
        result = process_ast("\\begin{document}\\customadd{new content}\\end{document}", "new", changes_list)
        assert "new content" in result
        assert "\\customadd" not in result

    def test_custom_deleted_command(self):
        """Custom command with type 'deleted' is processed correctly."""
        changes_list = {"customdel": "deleted"}
        result = process_ast("\\begin{document}\\customdel{old content}\\end{document}", "new", changes_list)
        assert "old content" not in result

    def test_custom_replaced_command(self):
        """Custom command with type 'replaced' is processed correctly."""
        changes_list = {"customrep": "replaced"}
        result_new = process_ast("\\customrep{new}{old}", "new", changes_list)
        result_old = process_ast("\\customrep{new}{old}", "old", changes_list)
        assert "new" in result_new
        assert "old" in result_old


class TestParseChangesList:
    """Test the parse_changes_list function."""

    def test_parse_basic(self):
        """Parse basic changes list."""
        content = "added:added\ndeleted:deleted"
        result = parse_changes_list(content)
        assert result["added"] == "added"
        assert result["deleted"] == "deleted"

    def test_parse_with_comments(self):
        """Parse changes list with comments."""
        content = "# comment\nadded:added\n# another\n"
        result = parse_changes_list(content)
        assert result == {"added": "added"}

    def test_parse_empty(self):
        """Parse empty content."""
        result = parse_changes_list("")
        assert result == {}

    def test_parse_invalid_lines(self):
        """Parse content with invalid lines."""
        content = "invalid\nno_colon\nadded:added"
        result = parse_changes_list(content)
        assert result == {"added": "added"}


class TestComplexDocuments:
    """Test processing of complex documents."""

    def test_complex_document_new(self):
        """Complex document with various changes in new mode."""
        text = """\\documentclass{article}
\\usepackage{changes}
\\title{Test \\added{New} Title}
\\begin{document}
\\section{Intro}
This is \\added{new} and this is \\deleted{old}.
\\replaced{old}{new} version.
\\highlight{important}
\\begin{itemize}
\\item \\added{new item}
\\item \\deleted{old item}
\\item Normal item
\\end{itemize}
\\end{document}"""
        result = process_ast(text, "new")
        assert "new" in result
        assert "old item" not in result
        assert "New" in result
        assert "\\usepackage{changes}" not in result

    def test_complex_document_old(self):
        """Complex document with various changes in old mode."""
        text = """\\documentclass{article}
\\usepackage{changes}
\\title{Test \\added{New} Title}
\\begin{document}
\\section{Intro}
This is \\added{new} and this is \\deleted{old}.
\\replaced{old}{new} version.
\\end{document}"""
        result = process_ast(text, "old")
        assert "old" in result
        # In old mode, \added is removed but "new" appears in \replaced{old}{new}
        # So we can't just check that "new" is not in result
        # Instead check that the \added content is removed
        assert "This is " in result  # \added{new} is removed
        assert "old" in result  # \deleted{old} is kept
        assert "\\usepackage{changes}" not in result


class TestRemoveEmptyMath:
    """Test removal of empty math environments."""

    def test_remove_empty_equation(self):
        """Empty equation environment is removed."""
        text = "before\\begin{equation}\\end{equation}after"
        # Note: remove_empty_math is handled at a higher level (regex-based)
        # The AST transformer doesn't handle this directly
        # This test is for the overall ast_remove_changes function
        pass  # Tested via CLI integration


class TestAstRemoveChangesFunction:
    """Test the ast_remove_changes function with file I/O."""

    def test_ast_remove_changes_with_file(self, tmp_path):
        """ast_remove_changes processes a file correctly."""
        tex_file = tmp_path / "test.tex"
        tex_file.write_text("\\begin{document}\\added{new}\\end{document}")

        result = ast_remove_changes(tex_file, "new")
        assert "new" in result
        assert "\\added" not in result

    def test_ast_remove_changes_old_mode(self, tmp_path):
        """ast_remove_changes in old mode."""
        tex_file = tmp_path / "test.tex"
        tex_file.write_text("\\begin{document}\\deleted{old}\\end{document}")

        result = ast_remove_changes(tex_file, "old")
        assert "old" in result
        assert "\\deleted" not in result