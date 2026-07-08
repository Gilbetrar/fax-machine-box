"""Convenience entry point for the Ponoko export mode: regenerate every
part with Ponoko's provider settings and re-nest them onto Ponoko-sized
sheets, in one command.

    .venv/bin/python -m faxbox.ponoko

is equivalent to:

    FAXBOX_PROVIDER=ponoko .venv/bin/python -m faxbox.layout

(the provider abstraction itself lives in faxbox.config.PROVIDERS and
faxbox.layout.generate_ponoko_layout -- this module is purely a friendlier
name for the same call, since every OTHER stage of this project already has
its own dedicated module (shell_generator, generate_drawers, generate_lids,
layout), and generate_ponoko_layout already regenerates all of its own
ponoko-flavored source SVGs internally).

Output: output/ponoko/ (sheet_1.svg, sheet_2.svg, ..., final_layout.svg,
plus the intermediate outer_shell.svg / drawer.svg / lids.svg / hardware.svg
/ calibration_coupon.svg). The default NYC Resistor path (output/*.svg,
`python -m faxbox.layout` with no env var) is never touched by this module.
"""

from faxbox.layout import generate_ponoko_layout


def main() -> None:
    generate_ponoko_layout(provider="ponoko")


if __name__ == "__main__":
    main()
