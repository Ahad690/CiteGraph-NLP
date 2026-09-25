"""Draw what the flow-diagram reader sees onto one diagram, for the thesis.

    python scripts/render_flow_reader_example.py

Grey outlines are every box the detector found. Coloured outlines are the
boxes whose counts were used, tagged with the stage and value the reader
assigned. The example is PMC11809628 (F1000Research, CC BY 4.0), chosen because
its analysis boxes hold only "N = 85": the stage comes from the side banner,
which is the layout reasoning the text method cannot do.
"""

import os
import sys

import cv2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from citegraph.vision import flow_diagram as fd  # noqa: E402

SOURCE = os.path.join(ROOT, "data", "flow_diagrams",
                      "PMC11809628_f1000research-13-176027-g0000.jpg")
OUT = os.path.join(ROOT, "thesis", "figures", "flow_reader_example.png")
COLOURS = {"screened": (180, 119, 31), "randomised": (44, 160, 44),
           "allocated": (14, 127, 255), "analysed": (40, 39, 214)}


def main() -> int:
    image = cv2.imread(SOURCE)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    lines = fd._ocr(image)
    boxes = fd._detect_boxes(gray)
    regions = fd._regions(lines, boxes)
    counts = [c for r in regions for c in fd._counts(r)]
    fd._assign_from_layout(regions, counts, float(gray.shape[1]))

    canvas = cv2.resize(image, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    for x0, y0, x1, y1 in boxes:
        cv2.rectangle(canvas, (int(2 * x0), int(2 * y0)), (int(2 * x1), int(2 * y1)), (170, 170, 170), 1)
    for count in counts:
        stage = next((s for s in ("screened", "randomised", "analysed", "allocated") if s in count.stages), None)
        if stage is None:
            continue
        r, colour = count.region, COLOURS[stage]
        cv2.rectangle(canvas, (int(2 * r.x0), int(2 * r.y0)), (int(2 * r.x1), int(2 * r.y1)), colour, 3)
        tag = f"{stage} {count.value}"
        (w, h), _ = cv2.getTextSize(tag, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        x, y = int(2 * r.x1) + 6, int(2 * r.y0) + h + 4
        if x + w > canvas.shape[1]:
            x = int(2 * r.x0) - w - 10
        cv2.rectangle(canvas, (x - 3, y - h - 5), (x + w + 3, y + 5), (255, 255, 255), -1)
        cv2.putText(canvas, tag, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, colour, 2, cv2.LINE_AA)

    reading = fd._aggregate(counts)
    cv2.imwrite(OUT, canvas)
    print(f"  {len(boxes)} boxes, {len(lines)} text lines -> {reading.as_dict()}")
    print(f"  wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
