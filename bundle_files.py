"""File Bundler for AI Context.

Extracts specific files from the repo and formats them
with syntax highlighting for pasting into AI chat sessions.

Usage:
    1. Edit FILES_TO_EXTRACT below with the paths you need
    2. Run: python bundle_files.py
    3. Copy the output and paste into your AI chat

Tip: Use map_repo.py first to see the tree, then ask the AI
which files it needs, then add those paths here.
"""
import os

# ---------------------------------------------------------
# CONFIGURATION: Add the exact file paths you want to extract
# ---------------------------------------------------------
# Paste the paths exactly as they appeared in the tree output
FILES_TO_EXTRACT = [
    "backend/app/main.py",
    "backend/app/core/config.py",
    "backend/app/services/kelly_position_sizer.py",
    "frontend-v2/src/App.jsx",
    # Add more file paths here...
]


def bundle_files(file_list):
    """Read each file and format it with syntax highlighting."""
    output = []

    for file_path in file_list:
        normalized_path = os.path.normpath(file_path)

        if not os.path.exists(normalized_path):
            output.append(f"WARNING: Could not find file -> {normalized_path}\n")
            continue

        if not os.path.isfile(normalized_path):
            output.append(f"WARNING: Path is a directory, not a file -> {normalized_path}\n")
            continue

        try:
            with open(normalized_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Determine syntax highlighting based on extension
            _, ext = os.path.splitext(normalized_path)
            lang = ext.replace('.', '')
            if lang in ['js', 'jsx']:
                lang = 'javascript'
            elif lang in ['ts', 'tsx']:
                lang = 'typescript'
            elif lang == 'py':
                lang = 'python'

            # Format the output block
            block = f"### File: {normalized_path}\n"
            block += f"```{lang}\n"
            block += content
            if not content.endswith('\n'):
                block += '\n'
            block += "```\n"
            output.append(block)

        except Exception as e:
            output.append(f"WARNING: Could not read {normalized_path} ({str(e)})\n")

    return "\n".join(output)


if __name__ == "__main__":
    print("Bundling files for AI context...\n")
    print("-" * 50)

    bundled_text = bundle_files(FILES_TO_EXTRACT)
    print(bundled_text)

    print("-" * 50)
    print("Done! Copy the text above the line and paste it into Claude.")
