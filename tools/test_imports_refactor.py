import traceback

modules = [
    'app.auto_fishing.auto_features',
    'app.auto_fishing.interface',
    'controller',
    'autoclicker',
    'ui',
]

for m in modules:
    try:
        mod = __import__(m, fromlist=['*'])
        print(f"MODULE_OK: {m} -> {getattr(mod,'__file__', 'builtin')}")
        names = [n for n in dir(mod) if not n.startswith('_')]
        print('  sample:', names[:20])
    except Exception:
        print(f"MODULE_FAIL: {m}")
        traceback.print_exc()

print('DONE')

