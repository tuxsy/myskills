# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for MySkills CLI tool (R-005).

Build command:
    pyinstaller myskills.spec

Output: dist/myskills (single-file executable)

Configuration:
- --onefile mode for single binary distribution
- Lazy imports optimization
- Excluded unused stdlib modules for size reduction
- Runtime tmpdir set to ~/.cache/myskills for persistent extraction caching
"""

import sys
from pathlib import Path

# Determine the project root (where this spec file lives)
spec_root = Path(SPECPATH)

# Application entry point
entry_point = spec_root / "src" / "myskills" / "__main__.py"

# Analysis: discover all dependencies
a = Analysis(
    [str(entry_point)],
    pathex=[str(spec_root / "src")],
    binaries=[],
    datas=[],
    hiddenimports=[
        # Explicitly include dependencies that might be missed
        "myskills",
        "myskills.cli",
        "myskills.models",
        "myskills.git_ops",
        "myskills.skill_ops",
        "myskills.manifest",
        "myskills.symlinks",
        "myskills.config",
        "myskills.agents",
        "myskills.project",
        "myskills.ui",
        "myskills.rollback",
        # Dulwich and dependencies
        "dulwich",
        "dulwich.porcelain",
        "dulwich.client",
        "dulwich.contrib.paramiko_vendor",
        # Other dependencies
        "click",
        "yaml",
        "simple_term_menu",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unused stdlib modules to reduce bundle size (R-005)
        "tkinter",
        "unittest",
        "email",
        "html",
        "http",
        "xml",
        "pydoc",
        "doctest",
        "test",
        "tests",
        "distutils",
        "setuptools",
        "pkg_resources",
        "PIL",
        "matplotlib",
        "numpy",
        "pandas",
        "scipy",
        "IPython",
        "notebook",
        "jupyter",
    ],
    noarchive=False,
)

# PYZ: Create a compressed archive of Python modules
pyz = PYZ(a.pure)

# EXE: Create the executable
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="myskills",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,  # Keep symbols for debugging
    upx=True,  # Compress with UPX if available
    upx_exclude=[],
    runtime_tmpdir="~/.cache/myskills",  # Persistent extraction cache (R-005)
    console=True,  # CLI tool requires console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
