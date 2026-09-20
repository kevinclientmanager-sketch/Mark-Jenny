# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Mark Imti Backend

import os
import sys

block_cipher = None

# Backend directory
BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(SPEC)), '..', 'backend')

a = Analysis(
    [os.path.join(BACKEND_DIR, 'main.py')],
    pathex=[BACKEND_DIR],
    binaries=[],
    datas=[
        (os.path.join(BACKEND_DIR, 'app'), 'app'),
        (os.path.join(BACKEND_DIR, 'requirements.txt'), '.'),
    ],
    hiddenimports=[
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'fastapi',
        'sqlalchemy',
        'pydantic',
        'httpx',
        'app.main',
        'app.core.config',
        'app.core.security',
        'app.db.base',
        'app.models.user',
        'app.models.agent',
        'app.models.project',
        'app.models.task',
        'app.models.file',
        'app.models.skill',
        'app.models.memory',
        'app.models.knowledge',
        'app.models.schedule',
        'app.models.chat',
        'app.api.v1.api',
        'app.services.agent_brain',
        'app.services.model_router',
        'app.services.airllm_engine',
        'app.services.smart_scraper',
        'app.services.browser_engine',
        'app.services.self_builder',
    ],
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
    [],
    exclude_binaries=True,
    name='mark-jenny-server',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(os.path.dirname(os.path.abspath(SPEC)), '..', 'desktop', 'assets', 'icon.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='mark-jenny-server',
)
