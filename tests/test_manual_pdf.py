import re

from resources.manual_pdf import build_lab_manual_pdf


def test_lab_manual_pdf_wraps_content_across_pages_without_truncation():
    long_theory = "Conservation and measurement principles in the experiment. " * 140

    pdf = build_lab_manual_pdf(
        title="Fluid Mechanics Experiment: Long Title for Layout Verification",
        subject_code="ME204",
        department="Department of Mechanical Engineering",
        experiment_number="03",
        objective="Verify the stated fluid mechanics principle using the provided apparatus.",
        apparatus="Venturimeter, manometer panel, stopwatch, and collection tank.",
        theory=long_theory,
        procedure="Step 1: Establish steady flow. Step 2: Record the measurements.",
        formulas="Q = A * v | C_d = Q_actual / Q_theoretical",
        viva_questions=["Explain the relation used in this experiment."],
    )

    assert pdf.startswith(b"%PDF-")
    page_tree = re.search(rb"/Count\s+(\d+)", pdf)
    assert page_tree is not None
    assert int(page_tree.group(1)) >= 2


def test_lab_manual_pdf_accepts_optional_observation_table():
    pdf = build_lab_manual_pdf(
        title="Optics Experiment",
        subject_code="PH202",
        department="Department of Physics",
        experiment_number="02",
        objective="Measure the stated value.",
        apparatus="Optical bench, lens, and screen.",
        theory="The source document supplies this principle.",
        procedure="Step 1: Align the apparatus.",
        formulas="f = 1 / v + 1 / u",
        viva_questions=[],
        observation_table={"columns": ["Trial", "Reading"], "rows": [["1", ""]]},
    )

    assert pdf.startswith(b"%PDF-")
