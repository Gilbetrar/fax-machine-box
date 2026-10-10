"""Write site/data/parts.json: part outlines (zero kerf), placement
transforms, assembly steps and box dimensions for the site build.

    python scripts/export_site_data.py [out.json]

Deterministic: the same source produces the same bytes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from faxbox.assembly3d import site_data  # noqa: E402


def main(argv: list[str]) -> Path:
    out = Path(argv[1]) if len(argv) > 1 else ROOT / "site" / "data" / "parts.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(site_data(), separators=(",", ":"), sort_keys=False) + "\n")
    print(f"wrote {out} ({out.stat().st_size / 1024:.0f} KB)")
    return out


if __name__ == "__main__":
    main(sys.argv)
