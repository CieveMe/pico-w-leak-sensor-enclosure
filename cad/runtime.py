"""Project-scoped import workaround; no global package or system font edits."""
import glob
import os
from pathlib import Path
from fontTools.ttLib import TTFont, TTLibError

def _import_build123d():
    invalid = None
    if os.name == "nt":
        windows_root = os.environ.get("WINDIR") or os.environ.get("SystemRoot")
        candidate = Path(windows_root) / "Fonts" / "mstmc.ttf" if windows_root else None
        if candidate is not None and candidate.exists():
            try:
                font = TTFont(candidate)
                font.close()
            except TTLibError as error:
                if "bad sfntVersion" not in str(error):
                    raise
                invalid = os.path.normcase(os.path.abspath(candidate))
    original = glob.glob
    if invalid:
        def filtered(pattern, *args, **kwargs):
            return [p for p in original(pattern, *args, **kwargs)
                    if os.path.normcase(os.path.abspath(p)) != invalid]
        glob.glob = filtered
    try:
        import build123d
        return build123d
    finally:
        glob.glob = original

bd = _import_build123d()
