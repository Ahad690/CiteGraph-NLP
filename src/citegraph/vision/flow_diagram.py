"""Read a trial's participant-flow (CONSORT) diagram: which count is which stage.

The text extractor reads abstracts and is weakest at telling apart the
populations a trial reports (Section 6.4.3: 6 of 10 semantic types right).
A CONSORT flow diagram states the same numbers, but each one sits in a box
whose position in the flow says what it counts. Reading the layout, not only
the words, is what this module adds.

Pipeline:

  1. OCR       RapidOCR (PP-OCR exported to ONNX) gives text lines and their
               positions. It is a fixed classifier, so it cannot invent a number
               that is not in the image, which a generative vision model can.
  2. Boxes     OpenCV finds the drawn boxes as the holes inside the connected
               ink of borders and arrows, so rounded, square and elliptical
               boxes are all found the same way.
  3. Regions   each text line joins the smallest box around it; lines outside
               every box are clustered by proximity, because some diagrams draw
               no boxes at all.
  4. Counts    each count is paired with the words that label it: "Analysed
               (n = 35)" style, or "96 Patients assessed" style.
  5. Stages    labels are classified with CONSORT 2010 vocabulary. Exclusion
               words win, so "Excluded from analysis (n = 3)" is not analysed.
  6. Layout    a count whose own label names no stage takes one from a banner
               in its row or a heading directly above it; arms in one row are
               summed; the analysis row must sit below the allocated arms.

The vocabulary and layout rules come from the CONSORT 2010 template and the
ten development diagrams. None was added for a specific test diagram.

OpenCV and RapidOCR are optional dependencies, imported only when a diagram is
actually read, so the rest of the system runs without them.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any, Optional

STAGES = ("screened", "enrolled", "randomised", "analysed")

# --- CONSORT 2010 vocabulary -------------------------------------------------

EXCLUSION = re.compile(
    r"\b(not|exclud\w*|declin\w*|refus\w*|lost|loss|discontinu\w*|withdr\w*|"
    r"drop\w*|fail\w*|died|death)\b", re.I)
SCREENED = re.compile(
    r"assess\w*\s+for\s+(pre-?)?eligib|\bscreen\w*|\beligib\w*|\bapplied\b", re.I)
ENROLLED = re.compile(
    r"\benrol\w*|\bincluded\b|\brecruit(ed|ment)\b|"
    r"\b(met|meet|meeting|fulfill?ing|fulfilled)\s+(the\s+)?(\w+\s+)?inclusion", re.I)
RANDOMISED = re.compile(r"\brandomi[sz]\w*|\brandomly\b", re.I)
ANALYSED = re.compile(r"\banaly\w*", re.I)
ALLOCATED = re.compile(r"\ballocat\w*|\bassigned\b|\bgroups?\b|\barms?\b", re.I)

# Banners and headings name a stage for the boxes they sit beside or above.
HEADING_STAGE = [
    (re.compile(r"\banaly\w*", re.I), "analysed"),
    (re.compile(r"\ballocat\w*|\brandomi[sz]\w*", re.I), "allocated"),
    (re.compile(r"\bincluded\b|\benrolled\b", re.I), "enrolled"),
    (re.compile(r"\bscreening\b", re.I), "screened"),
]

N_COUNT = re.compile(r"\b[nN]\s*[=:]\s*(\d[\d,]*)")
LEADING_COUNT = re.compile(r"^\W*(\d[\d,]*)\s+(?=[A-Za-z])")
BULLETS = re.compile(r"^[\s•◆♦▪►➢➤\-–*·]+")


@dataclass
class Line:
    text: str
    conf: float
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2

    @property
    def h(self) -> float:
        return self.y1 - self.y0


@dataclass
class Region:
    x0: float
    y0: float
    x1: float
    y1: float
    lines: list[Line] = field(default_factory=list)
    drawn: bool = True

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2

    @property
    def h(self) -> float:
        return self.y1 - self.y0

    def text_lines(self) -> list[str]:
        """Lines in reading order: rows top to bottom, left to right in a row."""
        rows: list[list[Line]] = []
        for line in sorted(self.lines, key=lambda l: l.cy):
            if rows and abs(rows[-1][0].cy - line.cy) < 0.5 * max(line.h, rows[-1][0].h):
                rows[-1].append(line)
            else:
                rows.append([line])
        return [" ".join(l.text for l in sorted(row, key=lambda l: l.x0)) for row in rows]


@dataclass
class Count:
    value: int
    label: str
    stages: set[str]
    region: Region

    @property
    def cy(self) -> float:
        return self.region.cy


@dataclass
class FlowReading:
    screened: Optional[int] = None
    enrolled: Optional[int] = None
    randomised: Optional[int] = None
    analysed: Optional[int] = None
    evidence: dict[str, str] = field(default_factory=dict)
    ocr_lines: int = 0
    drawn_boxes: int = 0
    seconds: float = 0.0

    @property
    def is_flow(self) -> bool:
        return any(getattr(self, stage) is not None for stage in STAGES)

    def as_dict(self) -> dict[str, Any]:
        return {stage: getattr(self, stage) for stage in STAGES}


# --- 1. OCR -------------------------------------------------------------------

_engine = None


def _ocr_engine():
    global _engine
    if _engine is None:
        import logging
        from rapidocr import RapidOCR
        logging.getLogger("RapidOCR").setLevel(logging.WARNING)
        _engine = RapidOCR()
    return _engine


REREAD_BELOW = 0.85
REREAD_SCALE = 3
# Re-reading is only worth it where a count could be: a line with no digit
# cannot hold one. Without this, a text-heavy figure re-read dozens of lines
# and one development image took 13.7 s instead of about 3.
MAX_REREADS = 12
HAS_DIGIT = re.compile(r"\d")


def _ocr(image) -> list[Line]:
    # Passed explicitly because RapidOCR keeps these flags between calls: after
    # a recognition-only re-read, a plain call skipped text detection too and
    # returned no line positions at all.
    result = _ocr_engine()(image, use_det=True, use_cls=True, use_rec=True)
    lines = []
    rereads = 0
    for box, text, score in zip(result.boxes if result.boxes is not None else [],
                                result.txts or [], result.scores or []):
        text = str(text or "").strip()
        if not text or float(score) < 0.5:
            continue
        xs, ys = box[:, 0], box[:, 1]
        line = Line(text, float(score), float(xs.min()), float(ys.min()),
                    float(xs.max()), float(ys.max()))
        if line.conf < REREAD_BELOW and HAS_DIGIT.search(text) and rereads < MAX_REREADS:
            line = _reread(image, line)
            rereads += 1
        lines.append(line)
    return lines


def _reread(image, line: Line) -> Line:
    """Read one uncertain line again from an enlarged crop.

    PMC stores figures at web resolution, about 700 px wide, where a four-arm
    diagram's text is 10-12 px tall and the recogniser starts guessing: one
    development diagram came back as "Anaal s((a4)" for "Analysed (n=4)".
    Enlarging the whole image fixes that but quadruples the work; enlarging
    only the handful of lines the recogniser doubted costs almost nothing.
    """
    import cv2

    height, width = image.shape[:2]
    pad = 4
    x0, y0 = max(0, int(line.x0) - pad), max(0, int(line.y0) - pad)
    x1, y1 = min(width, int(line.x1) + pad), min(height, int(line.y1) + pad)
    if x1 <= x0 or y1 <= y0:
        return line
    crop = cv2.resize(image[y0:y1, x0:x1], None, fx=REREAD_SCALE, fy=REREAD_SCALE,
                      interpolation=cv2.INTER_CUBIC)
    # The crop is already one line, so text detection is skipped: recognition
    # alone read "Analysed (n=4)" at 0.97 in 57 ms, where the full pipeline on
    # the same crop found nothing and took 2.4 s.
    result = _ocr_engine()(crop, use_det=False, use_cls=False, use_rec=True)
    texts = [str(t).strip() for t in (result.txts or []) if str(t).strip()]
    scores = list(result.scores or [])
    if not texts:
        return line
    score = min(float(s) for s in scores) if scores else 0.0
    if score <= line.conf:
        return line
    return Line(" ".join(texts), score, line.x0, line.y0, line.x1, line.y1)


# --- 2. Boxes -----------------------------------------------------------------

def _detect_boxes(gray) -> list[tuple[float, float, float, float]]:
    """Drawn boxes, found as holes in the connected ink of borders and arrows.

    Connector arrows touch the boxes they join, so the borders of a whole flow
    chart are usually one connected shape; each box's interior is a hole in it.
    Taking holes rather than outer contours keeps boxes separate even when an
    arrow runs into them, and treats square, rounded and elliptical boxes alike.
    """
    import cv2
    import numpy as np

    height, width = gray.shape
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                   cv2.THRESH_BINARY_INV, 25, 12)
    # Close hairline gaps in thin borders so their interiors stay enclosed.
    binary = cv2.dilate(binary, np.ones((2, 2), np.uint8), iterations=1)
    contours, hierarchy = cv2.findContours(binary, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if hierarchy is None:
        return []
    boxes = []
    min_area = 0.002 * width * height
    for contour, info in zip(contours, hierarchy[0]):
        if info[3] == -1:  # an outer boundary, not a hole
            continue
        x, y, w, h = cv2.boundingRect(contour)
        if w < 30 or h < 14 or w * h < min_area:
            continue
        if w > 0.97 * width and h > 0.97 * height:
            continue
        boxes.append((float(x), float(y), float(x + w), float(y + h)))

    # One box can yield near-identical holes (double borders); keep one.
    boxes.sort(key=lambda b: (b[2] - b[0]) * (b[3] - b[1]))
    kept: list[tuple[float, float, float, float]] = []
    for box in boxes:
        if not any(_iou(box, other) > 0.8 for other in kept):
            kept.append(box)
    return kept


def _iou(a, b) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union else 0.0


# --- 3. Regions ---------------------------------------------------------------

def _regions(lines: list[Line], boxes) -> list[Region]:
    """Put each line in the smallest box around its centre; cluster the rest."""
    by_box: dict[int, Region] = {}
    free: list[Line] = []
    for line in lines:
        containing = [i for i, (x0, y0, x1, y1) in enumerate(boxes)
                      if x0 <= line.cx <= x1 and y0 <= line.cy <= y1]
        if not containing:
            free.append(line)
            continue
        smallest = min(containing, key=lambda i: (boxes[i][2] - boxes[i][0]) * (boxes[i][3] - boxes[i][1]))
        if smallest not in by_box:
            by_box[smallest] = Region(*boxes[smallest])
        by_box[smallest].lines.append(line)

    # Lines outside every box: join neighbours that sit on top of each other.
    parent = list(range(len(free)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, a in enumerate(free):
        for j in range(i + 1, len(free)):
            b = free[j]
            gap = max(a.y0, b.y0) - min(a.y1, b.y1)
            overlap = min(a.x1, b.x1) - max(a.x0, b.x0)
            if gap < 0.8 * max(a.h, b.h) and overlap > 0:
                parent[find(i)] = find(j)
    clusters: dict[int, list[Line]] = {}
    for i, line in enumerate(free):
        clusters.setdefault(find(i), []).append(line)
    regions = list(by_box.values())
    for members in clusters.values():
        regions.append(Region(min(l.x0 for l in members), min(l.y0 for l in members),
                              max(l.x1 for l in members), max(l.y1 for l in members),
                              members, drawn=False))
    return regions


# --- 4 and 5. Counts and stages -----------------------------------------------

def _stages_for(label: str) -> set[str]:
    if EXCLUSION.search(label):
        return {"excluded"}
    found = set()
    if SCREENED.search(label):
        found.add("screened")
    if ENROLLED.search(label):
        found.add("enrolled")
    if RANDOMISED.search(label):
        found.add("randomised")
    if ANALYSED.search(label):
        found.add("analysed")
    if ALLOCATED.search(label):
        found.add("allocated")
    return found


def _to_int(raw: str) -> Optional[int]:
    try:
        return int(raw.replace(",", ""))
    except ValueError:
        return None


def _counts(region: Region) -> list[Count]:
    """Pair every count in a region with the words that label it."""
    lines = [BULLETS.sub("", line) for line in region.text_lines()]
    text = " ".join(lines)
    counts: list[Count] = []
    matches = list(N_COUNT.finditer(text))
    if matches:
        # "Label (n = 35)": the label is the text since the previous count.
        start = 0
        for match in matches:
            value = _to_int(match.group(1))
            label = text[start:match.start()].strip(" ():;,.-")
            start = match.end()
            if value is not None:
                counts.append(Count(value, label, _stages_for(label), region))
        return counts

    # "96 Patients assessed for eligibility": the label follows the number, up
    # to the next line that starts with one.
    current: Optional[tuple[int, list[str]]] = None
    for line in lines:
        match = LEADING_COUNT.match(line)
        if match:
            if current:
                label = " ".join(current[1])
                counts.append(Count(current[0], label, _stages_for(label), region))
            value = _to_int(match.group(1))
            current = (value, [line[match.end():]]) if value is not None else None
        elif current:
            current[1].append(line)
    if current:
        label = " ".join(current[1])
        counts.append(Count(current[0], label, _stages_for(label), region))
    return counts


# --- 6. Layout ----------------------------------------------------------------

def _heading_stage(text: str) -> Optional[str]:
    for pattern, stage in HEADING_STAGE:
        if pattern.search(text):
            return stage
    return None


def _assign_from_layout(regions: list[Region], counts: list[Count], width: float) -> None:
    """Give a stage to counts whose own label names none (e.g. a box holding
    only "N = 85"), from a side banner in the same row or a heading just above."""
    headings = [r for r in regions if not _counts(r) and _heading_stage(" ".join(r.text_lines()))]
    side = [r for r in headings if (r.y1 - r.y0) > 1.5 * (r.x1 - r.x0) or r.x1 < 0.2 * width]
    for count in counts:
        if count.stages:
            continue
        region = count.region
        # A side banner labels a whole row, and a row's boxes are often taller
        # or offset from the banner, so take the nearest banner to the left
        # rather than requiring the box's centre to fall inside it.
        left = [b for b in side if b.x1 <= region.x0 + 5]
        banner = min(left, key=lambda b: abs((b.y0 + b.y1) / 2 - region.cy)) if left else None
        if banner is not None and abs((banner.y0 + banner.y1) / 2 - region.cy) > 1.5 * max(banner.y1 - banner.y0, region.h):
            banner = None
        if banner is None:
            above = [h for h in headings if h not in side and h.y1 <= region.y0 + 2
                     and region.y0 - h.y1 < 2.0 * max(region.h, 20)
                     and min(h.x1, region.x1) - max(h.x0, region.x0) > 0]
            banner = max(above, key=lambda h: h.y1) if above else None
        if banner is not None:
            stage = _heading_stage(" ".join(banner.text_lines()))
            if stage:
                count.stages = {stage}


def _rows(counts: list[Count]) -> list[list[Count]]:
    """Group counts whose regions sit side by side, top row first."""
    rows: list[list[Count]] = []
    for count in sorted(counts, key=lambda c: c.cy):
        if rows:
            anchor = rows[-1][0].region
            if abs(anchor.cy - count.cy) < 0.5 * max(anchor.h, count.region.h, 1):
                rows[-1].append(count)
                continue
        rows.append([count])
    return rows


def _first_per_region(counts: list[Count]) -> list[Count]:
    """One count per box: the first listed, e.g. ITT before per-protocol."""
    seen, out = set(), []
    for count in counts:
        if id(count.region) not in seen:
            seen.add(id(count.region))
            out.append(count)
    return out


def _row_total(row: list[Count]) -> int:
    """Sum the arms in a row, unless one box already states their total."""
    values = [c.value for c in row]
    if len(values) > 2:
        biggest = max(values)
        if biggest == sum(values) - biggest:
            return biggest
    return sum(values)


def _aggregate(counts: list[Count]) -> FlowReading:
    reading = FlowReading()

    def pick(stage: str, rows: list[list[Count]]) -> None:
        if rows:
            row = _first_per_region(rows[0])
            setattr(reading, stage, _row_total(row))
            reading.evidence[stage] = " | ".join(f"{c.label} ({c.value})" for c in row)

    for stage in ("screened", "enrolled", "randomised"):
        pick(stage, _rows([c for c in counts if stage in c.stages]))

    allocated = [c for c in counts if "allocated" in c.stages]
    if reading.randomised is None and allocated:
        # No randomised count stated: the arms of the first allocation row.
        pick("randomised", _rows(allocated))

    analysed = [c for c in counts if "analysed" in c.stages]
    if allocated:
        # The analysis must descend from the allocated arms, which excludes
        # secondary analyses drawn off to one side of the main flow. Only the
        # first allocation row defines the arms: a later box such as
        # "Sub-group (n = 20)" also matches the allocation vocabulary and would
        # otherwise stretch the span out to that side panel.
        arms = _rows(allocated)[0]
        span = (min(c.region.x0 for c in arms), max(c.region.x1 for c in arms))
        analysed = [c for c in analysed if min(span[1], c.region.x1) - max(span[0], c.region.x0) > 0]
    analysed_rows = _rows(analysed)
    if analysed_rows:
        row = _first_per_region(analysed_rows[-1])  # the final analysis row
        reading.analysed = _row_total(row)
        reading.evidence["analysed"] = " | ".join(f"{c.label} ({c.value})" for c in row)
    return reading


# --- Entry point --------------------------------------------------------------

def read_flow_diagram(image: bytes | str) -> FlowReading:
    """Read a flow-diagram image (bytes or path). Never raises on a bad image;
    an unreadable one returns a reading with every stage None."""
    import cv2
    import numpy as np

    start = time.perf_counter()
    if isinstance(image, (bytes, bytearray)):
        array = cv2.imdecode(np.frombuffer(image, np.uint8), cv2.IMREAD_COLOR)
    else:
        array = cv2.imread(str(image), cv2.IMREAD_COLOR)
    if array is None:
        return FlowReading(seconds=time.perf_counter() - start)

    gray = cv2.cvtColor(array, cv2.COLOR_BGR2GRAY)
    lines = _ocr(array)
    boxes = _detect_boxes(gray)
    regions = _regions(lines, boxes)
    counts = [count for region in regions for count in _counts(region)]
    _assign_from_layout(regions, counts, float(gray.shape[1]))

    reading = _aggregate(counts)
    reading.ocr_lines = len(lines)
    reading.drawn_boxes = len(boxes)
    reading.seconds = time.perf_counter() - start
    return reading
