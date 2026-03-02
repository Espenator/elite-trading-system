"""Repo Mapping Script for AI Context.

Generates a visual directory tree of the repository,
skipping heavy/useless folders (node_modules, .git, __pycache__)
and media files to keep AI context windows clean.

Usage:
    python map_repo.py              # map current directory
    python map_repo.py /path/to/dir # map specific directory
"""
import os
import sys

# ---------------------------------------------------------
# CONFIGURATION: What to hide from the AI to save context
# ---------------------------------------------------------
IGNORE_DIRS = {
    '.git', 'node_modules', '__pycache__', 'venv', 'env',
    '.vscode', '.idea', 'dist', 'build', 'coverage', '.next'
}
IGNORE_EXTS = {
    '.pyc', '.pyo', '.png', '.jpg', '.jpeg', '.gif',
    '.svg', '.ico', '.pdf', '.zip', '.tar', '.gz', '.mp4'
}


def generate_tree(dir_path, prefix=""):
    """Recursively build a visual tree string for a directory."""
    tree_str = ""
    try:
        entries = os.listdir(dir_path)
        entries.sort(key=lambda x: (not os.path.isdir(os.path.join(dir_path, x)), x.lower()))
    except PermissionError:
        return ""

    # Filter out ignored directories and files
    filtered_entries = []
    for e in entries:
        full_path = os.path.join(dir_path, e)
        if os.path.isdir(full_path):
            if e not in IGNORE_DIRS:
                filtered_entries.append(e)
        else:
            _, ext = os.path.splitext(e)
            if ext.lower() not in IGNORE_EXTS and e != '.DS_Store':
                filtered_entries.append(e)

    # Build the visual tree
    for i, entry in enumerate(filtered_entries):
        full_path = os.path.join(dir_path, entry)
        is_last = (i == len(filtered_entries) - 1)

        connector = "L-- " if is_last else "|-- "
        tree_str += f"{prefix}{connector}{entry}\n"

        if os.path.isdir(full_path):
            extension = "    " if is_last else "|   "
            tree_str += generate_tree(full_path, prefix + extension)

    return tree_str


if __name__ == "__main__":
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    target_dir = os.path.abspath(target_dir)

    print("```text")
    print(f"Directory Tree for: {os.path.basename(target_dir)}")
    print("=" * 40)
    print(os.path.basename(target_dir) + "/")
    print(generate_tree(target_dir), end="")
    print("=" * 40)
    print("```")
