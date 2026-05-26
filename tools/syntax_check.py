import ast, sys
files = [
    "d:/project/cctv-centralization/backend/app/services/playback/hikvision_playback.py",
    "d:/project/cctv-centralization/backend/app/api/v1/routers/playback.py",
]
ok = True
for f in files:
    with open(f, encoding="utf-8") as fh:
        src = fh.read()
    try:
        ast.parse(src)
        print("OK:", f.split("/")[-1])
    except SyntaxError as e:
        print("SYNTAX ERROR in", f, ":", e)
        ok = False
sys.exit(0 if ok else 1)
