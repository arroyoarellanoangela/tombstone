# PyInstaller spec for Tombstone.exe.
#
# Console app on purpose: it prompts for the API key and streams docker's
# build output, both of which need a terminal. A windowed build would show
# a blank box and then vanish.
#
# Build from the repo root:
#   python -m PyInstaller launcher/tombstone.spec --noconfirm

a = Analysis(
    ["tombstone_launcher.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # The launcher only shells out to `docker` — none of the project's own
    # dependencies are imported, so nothing needs bundling and the binary
    # stays small.
    excludes=[
        "anthropic",
        "claude_agent_sdk",
        "fastapi",
        "httpx",
        "numpy",
        "pandas",
        "pydantic",
        "uvicorn",
        "yaml",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Tombstone",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
