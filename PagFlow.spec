# -*- mode: python ; coding: utf-8 -*-

import os

# Ícone do executável — opcional, para o build não quebrar em outra máquina
ICONE = (r'C:\Users\gustavo.pinheiro\OneDrive - DISTRIBUIDORA DE MEDICAMENTOS '
         r'SANTA CRUZ LTDA\Documentos\PagFlow.ico')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        # Envio de e-mails via Outlook Desktop (pywin32, importado de forma
        # lazy em envios.py — precisa ser declarado para o PyInstaller embutir).
        'envios',
        'win32com',
        'win32com.client',
        'pythoncom',
        'win32timezone',
        # Exportação rápida (import lazy em funcoes.py, com fallback para
        # openpyxl quando o pacote não está presente).
        'xlsxwriter',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PagFlow',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[ICONE] if os.path.exists(ICONE) else [],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PagFlow',
)
