"""k300fx.__version__ degerini packaging/version_info.txt icine yazar (tek kaynak: __init__.py)."""
import re
from pathlib import Path

root = Path(__file__).resolve().parents[1]
ver = re.search(r'__version__ = "([^"]+)"', (root / "k300fx" / "__init__.py").read_text(encoding="utf-8")).group(1)
parts = (ver.split(".") + ["0", "0", "0"])[:4]
vi = root / "packaging" / "version_info.txt"
s = vi.read_text(encoding="utf-8")
s = re.sub(r"filevers=\([^)]*\)", "filevers=(%s)" % ", ".join(parts), s)
s = re.sub(r"prodvers=\([^)]*\)", "prodvers=(%s)" % ", ".join(parts), s)
s = re.sub(r"('FileVersion', ')[^']*(')", r"\g<1>%s\g<2>" % ".".join(parts), s)
s = re.sub(r"('ProductVersion', ')[^']*(')", r"\g<1>%s\g<2>" % ver, s)
vi.write_text(s, encoding="utf-8")
print("surum:", ver)
