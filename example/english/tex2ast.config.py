# Project configuration for tex2ast
# This file defines settings used by the tex2ast CLI commands.

tex2ast_config = {
    # Main input file (relative to this config file's directory)
    'input_tex': 'main.tex',

    # Output file for remove-changes commands
    'output_tex': 'main_cleaned.tex',

    # Inline changes commands configuration
    # Format: command_name:type (one per line)
    'changes_list': '''
# Custom changes commands
review:added
note:comment
obsolete:deleted
cancel:deleted
''',

    # Remove empty math environments
    'remove_empty_math': True,
}