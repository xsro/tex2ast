import copy
# Project configuration for tex2ast (Chinese project)
# This file defines settings used by the tex2ast CLI commands.

changes1 = {
    # Main input file (relative to this config file's directory)
    'input_tex': 'main.tex',

    # Output file for remove-changes commands
    'output_tex': 'main_cleaned.tex',

    # Inline changes commands configuration
    # Format: command_name:type (one per line)
    'changes_list': '''
# Custom changes commands
cancel:deleted
''',

    # Remove empty math environments
    'remove_empty_math': True,
}
changes2 = copy.copy(changes1)
changes2["output_tex"] = 'main_cleaned_grep.tex'

tex2ast_config = {
    "ast-remove-changes": changes1,
    "remove-changes": changes2,
}