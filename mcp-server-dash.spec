# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for mcp-server-dash
Builds a standalone executable for the MCP server
"""

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Additional hidden imports that might not be auto-detected
# We explicitly list what we need instead of collect_submodules to avoid CLI dependencies
hiddenimports = [
    'mcp',
    'mcp.server',
    'mcp.server.fastmcp',
    'mcp.server.stdio',
    'mcp.server.session',
    'mcp.types',
    'mcp.shared',
    'mcp.shared.context',
    'mcp.shared.memory',
    'mcp.shared.session',
    'dropbox',
    'dropbox.auth',
    'dropbox.files',
    'dropbox.sharing',
    'dropbox.team',
    'httpx',
    'httpx._transports',
    'httpx._transports.default',
    'pydantic',
    'pydantic_core',
    'pydantic.dataclasses',
    'pydantic.fields',
    'pydantic.main',
    'typing_extensions',
    'dotenv',
    'keyring',
    'keyring.backends',
    'keyring.backends.Windows',
    'json',
    'asyncio',
    'contextlib',
    'functools',
    'h11',
    'httpcore',
    'certifi',
    'charset_normalizer',
    'idna',
    'sniffio',
    'anyio',
]

# Collect data files for packages that need them
datas = []
datas += collect_data_files('mcp', include_py_files=True)
datas += collect_data_files('httpx')

a = Analysis(
    ['src\\mcp_server_dash.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='mcp-server-dash',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
