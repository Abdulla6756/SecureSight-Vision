# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
)

# Keep the EXE build focused on runtime modules only.
# Do NOT use collect_all('sklearn'/'scipy'/'onnxruntime') here: it pulls test suites,
# onnx.reference, onnxruntime.tools, test suites, and other unused modules that
# can crash PyInstaller during binary dependency scanning on Windows.
# Matplotlib is kept because InsightFace imports it indirectly, but only with Agg.

def safe_collect_datas(package_name, excludes=None):
    try:
        return collect_data_files(package_name, excludes=excludes or [])
    except Exception:
        return []


def safe_collect_bins(package_name):
    try:
        return collect_dynamic_libs(package_name)
    except Exception:
        return []


def safe_collect_submods(package_name, skip_fragments=None):
    skip_fragments = skip_fragments or []
    try:
        return collect_submodules(
            package_name,
            filter=lambda name: not any(fragment in name for fragment in skip_fragments),
        )
    except Exception:
        return []


datas = [
    ('frontend/public', 'frontend/public'),
    ('backend/data', 'backend/data'),
]

# Data files needed by runtime packages. Exclude tests/examples to keep the package small
# and avoid PyInstaller scanning unstable optional dependencies.
datas += safe_collect_datas('insightface', excludes=['**/tests/**', '**/test/**', '**/examples/**'])
datas += safe_collect_datas('onnxruntime', excludes=['**/tools/**', '**/transformers/**', '**/quantization/**', '**/datasets/**'])
datas += safe_collect_datas('matplotlib', excludes=['**/tests/**', '**/test/**', '**/examples/**', '**/sample_data/**'])

binaries = []
for package_name in ['onnxruntime', 'cv2', 'numpy', 'scipy', 'matplotlib']:
    binaries += safe_collect_bins(package_name)

hiddenimports = [
    'uvicorn.loops.auto',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.http.h11_impl',
    'uvicorn.protocols.websockets.auto',
    'multipart',
    'python_multipart',
    'cv2',
    'numpy',
    'scipy',
    'scipy.spatial',
    'scipy.spatial.transform',
    'matplotlib',
    'matplotlib.figure',
    'matplotlib.pyplot',
    'matplotlib.backends.backend_agg',
    'onnxruntime',
    'onnxruntime.capi',
    'onnxruntime.capi.onnxruntime_pybind11_state',
    'insightface',
    'insightface.app',
    'insightface.model_zoo',
]

# InsightFace uses dynamic module loading for parts of its model zoo. Collect only its
# runtime submodules, not third-party test trees.
hiddenimports += safe_collect_submods(
    'insightface',
    skip_fragments=['.tests', '.test_', '.examples'],
)

# Explicitly exclude optional/test-heavy packages that the app does not use at runtime.
excludes = [
    'torch',
    'tensorflow',
    'onnxruntime_gpu',
    'onnx.reference',
    'onnx.reference.ops',
    'onnx.reference.ops_optimized',
    'onnx.backend',
    'onnxruntime.backend',
    'onnxruntime.tools',
    'onnxruntime.transformers',
    'onnxruntime.quantization',
    'onnxruntime.datasets',
    'tkinter',
    '_tkinter',
    'sklearn.tests',
    'sklearn.utils.tests',
    'scipy.tests',
    'numpy.tests',
    'skimage.tests',
    'sympy',
    'mpmath',
    'Cython',
]


a = Analysis(
    ['desktop_launcher.py'],
    pathex=['backend'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={'matplotlib': {'backends': ['Agg']}},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SecureSightVision',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='SecureSightVision',
)
