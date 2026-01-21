"""Test generator to verify Boxes.py installation works correctly."""

from pathlib import Path

from boxes.generators.closedbox import ClosedBox

from faxbox.config import BURN, DEFAULT_BOX, MATERIAL_THICKNESS, OUTPUT_DIR


def generate_test_box() -> Path:
    """Generate a simple finger-joint box SVG to verify Boxes.py works.

    Returns:
        Path to the generated SVG file.
    """
    # Ensure output directory exists
    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(parents=True, exist_ok=True)

    output_file = output_path / "test_box.svg"

    # Create a ClosedBox generator instance
    box = ClosedBox()

    # Configure the box using argparse-style arguments
    box.parseArgs([
        "--output", str(output_file),
        "--thickness", str(MATERIAL_THICKNESS),
        "--burn", str(BURN),
        "--x", str(DEFAULT_BOX["width"]),
        "--y", str(DEFAULT_BOX["depth"]),
        "--h", str(DEFAULT_BOX["height"]),
        "--outside", "1",  # Dimensions are outside dimensions
    ])

    # Initialize canvas and edge objects, then render
    box.open()
    box.render()
    data = box.close()

    # Write SVG data to file
    with open(output_file, "wb") as f:
        f.write(data.getvalue())

    print(f"Generated test box SVG: {output_file.absolute()}")
    return output_file


if __name__ == "__main__":
    generate_test_box()
