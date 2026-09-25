"""The flow-diagram reader's rules, and the endpoint that runs it on demand.

The rule tests feed text straight into the stage and layout logic, so they need
no image and no OCR engine. The full reader is measured instead by
scripts/evaluate_flow_diagrams.py against the committed answer keys.
"""

import pytest

from citegraph.vision import flow_diagram as fd


def region(*lines, x0=0.0, y0=0.0, x1=200.0, y1=40.0):
    step = (y1 - y0) / max(len(lines), 1)
    return fd.Region(x0, y0, x1, y1, [
        fd.Line(text, 1.0, x0 + 5, y0 + i * step, x1 - 5, y0 + (i + 1) * step)
        for i, text in enumerate(lines)
    ])


class TestStages:
    @pytest.mark.parametrize("label,expected", [
        ("Assessed for eligibility", {"screened"}),
        ("Randomized", {"randomised"}),
        ("Enrolled and randomized", {"enrolled", "randomised"}),
        ("Analysed", {"analysed"}),
        ("Allocated to intervention", {"allocated"}),
        ("Excluded from analysis", {"excluded"}),
        ("Not meeting inclusion criteria", {"excluded"}),
        ("Lost to follow-up", {"excluded"}),
    ])
    def test_consort_vocabulary(self, label, expected):
        assert fd._stages_for(label) == expected

    def test_included_in_the_analysis_is_not_enrolment(self):
        assert fd._stages_for("were included in the analyses") == {"analysed"}


class TestCounts:
    def test_n_equals_style_pairs_label_before_count(self):
        counts = fd._counts(region("Analysed (n=35)", "Excluded from analysis (n=3)"))
        assert [(c.value, c.stages) for c in counts] == [(35, {"analysed"}), (3, {"excluded"})]

    def test_leading_number_style_pairs_label_after_count(self):
        counts = fd._counts(region("96 Patients assessed for eligibility"))
        assert [(c.value, c.stages) for c in counts] == [(96, {"screened"})]

    def test_count_on_its_own_line_above_its_label(self):
        counts = fd._counts(region("336", "Women were assessed for eligibility"))
        assert [(c.value, c.stages) for c in counts] == [(336, {"screened"})]

    def test_reasons_inside_an_exclusion_box_are_exclusions(self):
        """'before randomization' must not read as a randomised count."""
        counts = fd._counts(region("Excluded (n=22)", "Emergency intubation before randomization (n=4)"))
        assert all(c.stages == {"excluded"} for c in counts)


class TestAggregation:
    def arm(self, label, value, x0, y0):
        r = region(f"{label} (n={value})", x0=x0, y0=y0, x1=x0 + 150, y1=y0 + 30)
        return fd._counts(r)

    def test_arms_in_a_row_are_summed(self):
        counts = (self.arm("Randomized", 60, 100, 0)
                  + self.arm("Allocated to A", 30, 0, 100) + self.arm("Allocated to B", 30, 200, 100)
                  + self.arm("Analysed", 28, 0, 200) + self.arm("Analysed", 27, 200, 200))
        reading = fd._aggregate(counts)
        assert (reading.randomised, reading.analysed) == (60, 55)

    def test_randomised_falls_back_to_the_allocation_row(self):
        counts = self.arm("Allocated to A", 40, 0, 100) + self.arm("Allocated to B", 41, 200, 100)
        assert fd._aggregate(counts).randomised == 81

    def test_a_box_stating_the_total_is_not_added_to_its_arms(self):
        row = self.arm("Analysed", 23, 0, 200) + self.arm("Analysis", 46, 160, 200) + self.arm("Analysed", 23, 320, 200)
        assert fd._row_total(row) == 46

    def test_side_panel_analysis_is_ignored(self):
        """An analysis off to one side does not descend from the allocated arms."""
        counts = (self.arm("Allocated to A", 22, 0, 100) + self.arm("Allocated to B", 23, 160, 100)
                  + self.arm("Analysed", 16, 0, 200) + self.arm("Analysed", 16, 160, 200)
                  + self.arm("Analysed", 8, 600, 400) + self.arm("Analysed", 12, 760, 400))
        assert fd._aggregate(counts).analysed == 32

    def test_nothing_is_reported_without_stage_words(self):
        counts = fd._counts(region("Day 1 (n=3)", "Blood sampling (n=5)"))
        assert not fd._aggregate(counts).is_flow
