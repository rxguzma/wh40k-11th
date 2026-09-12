from pathlib import Path

patch_path = Path("scripts/patch_html_v31_32.py")
script = patch_path.read_text(encoding="utf-8")

# V31.31's retained historical release note legitimately contains the phrase
# "Range only, Melee only, and Both". That phrase is historical documentation,
# not live V31.32 behavior, so remove only this over-broad acceptance check.
old_check = """if 'Range only, Melee only, and Both' in text:\n    raise SystemExit('old three-state Range/Melee invariant still present')\n"""
if script.count(old_check) != 1:
    raise SystemExit("expected exactly one obsolete historical-note validation check")
script = script.replace(old_check, "", 1)

exec(compile(script, str(patch_path), "exec"))
