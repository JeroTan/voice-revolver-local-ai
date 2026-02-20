"""
Patch fairseq and hydra dataclass bugs for Python 3.11 compatibility.
Fixes "mutable default" errors by converting to field(default_factory=...).
"""
import re
from pathlib import Path

def patch_file(file_path, dry_run=False):
    """Patch a single Python file to fix dataclass mutable defaults."""
    if not file_path.exists():
        print(f"⚠️  File not found: {file_path}")
        return False
    
    content = file_path.read_text(encoding='utf-8')
    original_content = content
    
    # Pattern 1: field_name: TypeName = TypeName()
    # Replace with: field_name: TypeName = field(default_factory=TypeName)
    pattern1 = r'(\s+)(\w+):\s*(\w+(?:\.\w+)*)\s*=\s*\3\(\)'
    replacement1 = r'\1\2: \3 = field(default_factory=\3)'
    content = re.sub(pattern1, replacement1, content)
    
    # Pattern 2: Ensure dataclasses.field is imported if we added default_factory
    if content != original_content and 'from dataclasses import' in content:
        # Check if 'field' is already imported
        if not re.search(r'from dataclasses import.*\bfield\b', content):
            # Add field to existing dataclasses import
            content = re.sub(
                r'(from dataclasses import)([^)\n]+)',
                lambda m: m.group(1) + m.group(2).rstrip() + ', field',
                content,
                count=1
            )
    
    if content != original_content:
        if dry_run:
            print(f"✓ Would patch: {file_path}")
            return True
        else:
            file_path.write_text(content, encoding='utf-8')
            print(f"✅ Patched: {file_path}")
            return True
    return False

def main():
    import sys
    venv_path = Path(sys.prefix)
    
    # Files known to have dataclass bugs
    files_to_patch = [
        venv_path / "Lib/site-packages/fairseq/dataclass/configs.py",
        venv_path / "Lib/site-packages/hydra/conf/__init__.py",
        venv_path / "Lib/site-packages/hydra/core/config_store.py",
    ]
    
    # Also search for any other files with the pattern
    fairseq_path = venv_path / "Lib/site-packages/fairseq"
    hydra_path = venv_path / "Lib/site-packages/hydra"
    
    print(f"Scanning packages in: {venv_path}")
    
    if fairseq_path.exists():
        files_to_patch.extend(fairseq_path.rglob("*.py"))
    if hydra_path.exists():
        files_to_patch.extend(hydra_path.rglob("*.py"))
    
    print(f"Scanning {len(files_to_patch)} files for dataclass bugs...")
    
    patched_count = 0
    for file_path in files_to_patch:
        if patch_file(file_path):
            patched_count += 1
    
    print(f"\n{'='*60}")
    print(f"✅ Patched {patched_count} files")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
