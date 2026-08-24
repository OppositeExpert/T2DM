"""Build the development conference manuscript, supplement, and figures.

This builder deliberately labels every artifact as development-only. It does not
read or authorize final profiles.
"""

from __future__ import annotations

import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "conference_package"
GENERATED = PACKAGE / "generated"
FIGURES = GENERATED / "figures"
STUDY = ROOT / "outputs/publication_pipeline/studies/pidd_development_072cd2104089"
SYLHET_STUDY = ROOT / "outputs/publication_pipeline/studies/sylhet_development_b52477910fe6"

BLUE = "2E74B5"
DARK_BLUE = "1F4D78"
INK = "0B2545"
MUTED = "667085"
LIGHT_GRAY = "F2F4F7"
CALLOUT = "F4F6F9"
WHITE = "FFFFFF"
BLACK = "000000"
TABLE_WIDTH_DXA = 9360
TABLE_INDENT_DXA = 120


def set_run_font(run, *, size=None, color=BLACK, bold=None, italic=None):
    run.font.name = "Calibri"
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), "Calibri")
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), "Calibri")
    if size is not None:
        run.font.size = Pt(size)
    run.font.color.rgb = RGBColor.from_string(color)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic


def set_cell_margins(cell, top=80, start=120, bottom=80, end=120):
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for edge, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{edge}"))
        if node is None:
            node = OxmlElement(f"w:{edge}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_repeat_table_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def prevent_row_split(row):
    tr_pr = row._tr.get_or_add_trPr()
    cant_split = OxmlElement("w:cantSplit")
    cant_split.set(qn("w:val"), "true")
    tr_pr.append(cant_split)


def apply_table_geometry(table, widths):
    if sum(widths) != TABLE_WIDTH_DXA:
        raise ValueError(f"Table widths must sum to {TABLE_WIDTH_DXA}: {widths}")
    table.autofit = False
    tbl_pr = table._tbl.tblPr
    tbl_w = tbl_pr.first_child_found_in("w:tblW")
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        tbl_pr.append(tbl_w)
    tbl_w.set(qn("w:w"), str(TABLE_WIDTH_DXA))
    tbl_w.set(qn("w:type"), "dxa")
    tbl_ind = tbl_pr.first_child_found_in("w:tblInd")
    if tbl_ind is None:
        tbl_ind = OxmlElement("w:tblInd")
        tbl_pr.append(tbl_ind)
    tbl_ind.set(qn("w:w"), str(TABLE_INDENT_DXA))
    tbl_ind.set(qn("w:type"), "dxa")
    layout = tbl_pr.first_child_found_in("w:tblLayout")
    if layout is None:
        layout = OxmlElement("w:tblLayout")
        tbl_pr.append(layout)
    layout.set(qn("w:type"), "fixed")

    grid = table._tbl.tblGrid
    for child in list(grid):
        grid.remove(child)
    for width in widths:
        col = OxmlElement("w:gridCol")
        col.set(qn("w:w"), str(width))
        grid.append(col)

    for row in table.rows:
        for cell, width in zip(row.cells, widths):
            tc_pr = cell._tc.get_or_add_tcPr()
            tc_w = tc_pr.first_child_found_in("w:tcW")
            if tc_w is None:
                tc_w = OxmlElement("w:tcW")
                tc_pr.append(tc_w)
            tc_w.set(qn("w:w"), str(width))
            tc_w.set(qn("w:type"), "dxa")
            set_cell_margins(cell)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def table_widths(rows):
    columns = len(rows[0])
    if columns == 7:
        return [1800, 1260, 1260, 1260, 1260, 1260, 1260]
    if columns == 4:
        return [1400, 2900, 2200, 2860]
    lengths = []
    for index in range(columns):
        max_len = max(len(str(row[index])) for row in rows)
        lengths.append(min(max(max_len, 8), 36))
    raw = np.asarray(lengths, dtype=float)
    widths = np.floor(raw / raw.sum() * TABLE_WIDTH_DXA).astype(int)
    widths[-1] += TABLE_WIDTH_DXA - int(widths.sum())
    return widths.tolist()


def add_numbering_definitions(doc):
    numbering = doc.part.numbering_part.element
    abstract_ids = [int(x.get(qn("w:abstractNumId"))) for x in numbering.findall(qn("w:abstractNum"))]
    num_ids = [int(x.get(qn("w:numId"))) for x in numbering.findall(qn("w:num"))]
    next_abstract = max(abstract_ids, default=0) + 1
    next_num = max(num_ids, default=0) + 1

    def add_definition(abstract_id, num_id, fmt, text):
        abstract = OxmlElement("w:abstractNum")
        abstract.set(qn("w:abstractNumId"), str(abstract_id))
        multi = OxmlElement("w:multiLevelType")
        multi.set(qn("w:val"), "singleLevel")
        abstract.append(multi)
        lvl = OxmlElement("w:lvl")
        lvl.set(qn("w:ilvl"), "0")
        start = OxmlElement("w:start")
        start.set(qn("w:val"), "1")
        lvl.append(start)
        num_fmt = OxmlElement("w:numFmt")
        num_fmt.set(qn("w:val"), fmt)
        lvl.append(num_fmt)
        lvl_text = OxmlElement("w:lvlText")
        lvl_text.set(qn("w:val"), text)
        lvl.append(lvl_text)
        jc = OxmlElement("w:lvlJc")
        jc.set(qn("w:val"), "left")
        lvl.append(jc)
        p_pr = OxmlElement("w:pPr")
        tabs = OxmlElement("w:tabs")
        tab = OxmlElement("w:tab")
        tab.set(qn("w:val"), "num")
        tab.set(qn("w:pos"), "720")
        tabs.append(tab)
        p_pr.append(tabs)
        ind = OxmlElement("w:ind")
        ind.set(qn("w:left"), "720")
        ind.set(qn("w:hanging"), "360")
        p_pr.append(ind)
        spacing = OxmlElement("w:spacing")
        spacing.set(qn("w:after"), "160")
        spacing.set(qn("w:line"), "280")
        spacing.set(qn("w:lineRule"), "auto")
        p_pr.append(spacing)
        lvl.append(p_pr)
        abstract.append(lvl)
        numbering.append(abstract)

        num = OxmlElement("w:num")
        num.set(qn("w:numId"), str(num_id))
        abstract_ref = OxmlElement("w:abstractNumId")
        abstract_ref.set(qn("w:val"), str(abstract_id))
        num.append(abstract_ref)
        numbering.append(num)

    add_definition(next_abstract, next_num, "bullet", "•")
    add_definition(next_abstract + 1, next_num + 1, "decimal", "%1.")
    return next_num, next_num + 1


def apply_num(paragraph, num_id):
    p_pr = paragraph._p.get_or_add_pPr()
    num_pr = p_pr.find(qn("w:numPr"))
    if num_pr is None:
        num_pr = OxmlElement("w:numPr")
        p_pr.append(num_pr)
    ilvl = OxmlElement("w:ilvl")
    ilvl.set(qn("w:val"), "0")
    num = OxmlElement("w:numId")
    num.set(qn("w:val"), str(num_id))
    num_pr.append(ilvl)
    num_pr.append(num)


def configure_document(doc, short_title):
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(1)
    section.right_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.header_distance = Inches(0.492)
    section.footer_distance = Inches(0.492)
    section.different_first_page_header_footer = True

    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Calibri"
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
    normal.font.size = Pt(11)
    normal.font.color.rgb = RGBColor.from_string(BLACK)
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.10

    heading_tokens = {
        "Heading 1": (16, BLUE, 16, 8),
        "Heading 2": (13, BLUE, 12, 6),
        "Heading 3": (12, DARK_BLUE, 8, 4),
    }
    for name, (size, color, before, after) in heading_tokens.items():
        style = styles[name]
        style.font.name = "Calibri"
        style._element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
        style._element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(color)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = False
        style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT

    for style_name, size, italic, color in (
        ("Caption", 9, False, MUTED),
        ("Subtitle", 12, False, MUTED),
    ):
        style = styles[style_name]
        style.font.name = "Calibri"
        style._element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
        style._element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
        style.font.size = Pt(size)
        style.font.italic = italic
        style.font.color.rgb = RGBColor.from_string(color)

    if "Table Text" not in styles:
        table_style = styles.add_style("Table Text", WD_STYLE_TYPE.PARAGRAPH)
    else:
        table_style = styles["Table Text"]
    table_style.font.name = "Calibri"
    table_style._element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
    table_style._element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
    table_style.font.size = Pt(8.5)
    table_style.paragraph_format.space_before = Pt(0)
    table_style.paragraph_format.space_after = Pt(0)
    table_style.paragraph_format.line_spacing = 1.0

    header = section.header
    header_p = header.paragraphs[0]
    header_p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    header_p.paragraph_format.space_after = Pt(0)
    run = header_p.add_run(short_title)
    set_run_font(run, size=9, color=MUTED)

    footer_p = section.footer.paragraphs[0]
    footer_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = footer_p.add_run("Development package  |  ")
    set_run_font(run, size=9, color=MUTED)
    page_run = footer_p.add_run()
    fld_char1 = OxmlElement("w:fldChar")
    fld_char1.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    fld_char2 = OxmlElement("w:fldChar")
    fld_char2.set(qn("w:fldCharType"), "end")
    page_run._r.extend((fld_char1, instr, fld_char2))
    set_run_font(page_run, size=9, color=MUTED)


def add_cover(doc, title, subtitle):
    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_after = Pt(48)
    kicker = doc.add_paragraph()
    kicker.alignment = WD_ALIGN_PARAGRAPH.CENTER
    kicker.paragraph_format.space_after = Pt(12)
    set_run_font(kicker.add_run("DEVELOPMENT CONFERENCE PACKAGE"), size=10, color=BLUE, bold=True)

    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_p.paragraph_format.space_after = Pt(12)
    title_p.paragraph_format.keep_with_next = True
    set_run_font(title_p.add_run(title), size=26, color=INK, bold=True)

    subtitle_p = doc.add_paragraph()
    subtitle_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle_p.paragraph_format.space_after = Pt(34)
    set_run_font(subtitle_p.add_run(subtitle), size=13, color=MUTED)

    status = doc.add_paragraph()
    status.alignment = WD_ALIGN_PARAGRAPH.CENTER
    status.paragraph_format.space_before = Pt(6)
    status.paragraph_format.space_after = Pt(8)
    status._p.get_or_add_pPr().append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="{CALLOUT}"/>'))
    set_run_font(status.add_run("NOT FINAL EVIDENCE  |  NOT AUTHORIZED FOR SUBMISSION"), size=10.5, color=DARK_BLUE, bold=True)

    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta.paragraph_format.space_after = Pt(10)
    set_run_font(meta.add_run("Evidence cutoff: 24 August 2026"), size=10, color=MUTED)
    doc.add_page_break()


def add_inline_runs(paragraph, text):
    text = text.replace("  ", " ").strip()
    tokens = re.split(r"(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)", text)
    for token in tokens:
        if not token:
            continue
        if token.startswith("**") and token.endswith("**"):
            run = paragraph.add_run(token[2:-2])
            set_run_font(run, bold=True)
        elif token.startswith("`") and token.endswith("`"):
            run = paragraph.add_run(token[1:-1])
            set_run_font(run, color=DARK_BLUE)
            run.font.name = "Aptos Mono"
        elif token.startswith("*") and token.endswith("*"):
            run = paragraph.add_run(token[1:-1])
            set_run_font(run, italic=True)
        else:
            run = paragraph.add_run(token)
            set_run_font(run)


def add_markdown_table(doc, rows):
    widths = table_widths(rows)
    table = doc.add_table(rows=len(rows), cols=len(rows[0]))
    table.style = "Table Grid"
    table.alignment = WD_ALIGN_PARAGRAPH.LEFT
    apply_table_geometry(table, widths)
    set_repeat_table_header(table.rows[0])
    for row in table.rows:
        prevent_row_split(row)
    for r_idx, row in enumerate(rows):
        for c_idx, value in enumerate(row):
            cell = table.cell(r_idx, c_idx)
            cell.text = ""
            p = cell.paragraphs[0]
            p.style = "Table Text"
            numeric = bool(re.fullmatch(r"[-+]?\d+(?:\.\d+)?%?", value.strip()))
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if numeric or r_idx == 0 else WD_ALIGN_PARAGRAPH.LEFT
            display_value = value.strip()
            if display_value.startswith("`") and display_value.endswith("`"):
                display_value = display_value[1:-1]
            run = p.add_run(display_value)
            set_run_font(run, size=8.5, bold=(r_idx == 0), color=(WHITE if r_idx == 0 else BLACK))
            if r_idx == 0:
                tc_pr = cell._tc.get_or_add_tcPr()
                tc_pr.append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="{DARK_BLUE}"/>'))
    after = doc.add_paragraph()
    after.alignment = WD_ALIGN_PARAGRAPH.LEFT
    after.paragraph_format.space_after = Pt(2)
    return table


def add_figure(doc, source, alt_text):
    path = (PACKAGE / source).resolve()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    run = p.add_run()
    run.add_picture(str(path), width=Inches(6.2))
    inline = doc.inline_shapes[-1]._inline
    inline.docPr.set("descr", alt_text)
    inline.docPr.set("title", path.stem.replace("_", " ").title())


def render_markdown(doc, source, bullet_num_id, decimal_num_id):
    lines = source.read_text(encoding="utf-8").splitlines()
    index = 0
    paragraph_buffer = []

    def flush_paragraph():
        if paragraph_buffer:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            add_inline_runs(p, " ".join(paragraph_buffer))
            paragraph_buffer.clear()

    while index < len(lines):
        line = lines[index].rstrip()
        stripped = line.strip()
        if index == 0 and stripped.startswith("# "):
            index += 1
            continue
        if stripped.startswith("**Document state:") or stripped.startswith("**State:") or stripped.startswith("**Evidence cutoff:") or stripped.startswith("**Target format:"):
            index += 1
            continue
        if not stripped:
            flush_paragraph()
            index += 1
            continue
        image = re.fullmatch(r"!\[(.+)]\((.+)\)", stripped)
        if image:
            flush_paragraph()
            add_figure(doc, image.group(2), image.group(1))
            index += 1
            continue
        if stripped.startswith("|") and index + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-+", lines[index + 1]):
            flush_paragraph()
            raw_rows = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                raw_rows.append([cell.strip() for cell in lines[index].strip().strip("|").split("|")])
                index += 1
            if len(raw_rows) >= 2:
                raw_rows.pop(1)
            add_markdown_table(doc, raw_rows)
            continue
        heading = re.match(r"^(#{2,4})\s+(.+)$", stripped)
        if heading:
            flush_paragraph()
            level = min(len(heading.group(1)) - 1, 3)
            p = doc.add_paragraph(style=f"Heading {level}")
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.keep_with_next = False
            add_inline_runs(p, heading.group(2))
            index += 1
            continue
        bullet = re.match(r"^-\s+(.+)$", stripped)
        numbered = re.match(r"^\d+\.\s+(.+)$", stripped)
        if bullet or numbered:
            flush_paragraph()
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.line_spacing = 1.10
            p.paragraph_format.left_indent = Inches(0.5)
            p.paragraph_format.first_line_indent = Inches(-0.25)
            apply_num(p, bullet_num_id if bullet else decimal_num_id)
            index += 1
            item_parts = [(bullet or numbered).group(1)]
            while index < len(lines):
                continuation = lines[index]
                if not continuation.strip() or not continuation[:1].isspace():
                    break
                item_parts.append(continuation.strip())
                index += 1
            add_inline_runs(p, " ".join(item_parts))
            continue
        paragraph_buffer.append(stripped)
        index += 1
    flush_paragraph()


def save_figure(fig, name):
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / name, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def build_figures():
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.titlesize": 10.5,
        "axes.labelsize": 9.5,
        "axes.spines.top": False,
        "axes.spines.right": False,
    })
    ci = pd.read_csv(STUDY / "participant_confidence_intervals.csv")
    ci = ci[(ci["probability_version"] == "calibrated") & (ci["threshold_policy"] == "fixed_0_5")]
    order = ["logistic_regression", "random_forest", "xgboost", "lightgbm", "catboost"]
    labels = ["Logistic\nRegression", "Random\nForest", "XGBoost", "LightGBM", "CatBoost"]
    fig, axes = plt.subplots(1, 2, figsize=(7.3, 3.05))
    for ax, metric, title, ylim in zip(axes, ["auroc", "brier_score"], ["Discrimination", "Probability loss"], [(0.78, 0.89), (0.125, 0.185)]):
        frame = ci[ci.metric == metric].set_index("model").loc[order]
        values = frame.estimate.to_numpy()
        errors = np.vstack((values - frame.ci_lower.to_numpy(), frame.ci_upper.to_numpy() - values))
        ax.errorbar(range(len(order)), values, yerr=errors, fmt="o", color="#1F4D78", ecolor="#7A9BB8", capsize=3, lw=1.2)
        ax.set_xticks(range(len(order)), labels)
        ax.set_ylim(*ylim)
        ax.set_title(title)
        ax.set_ylabel("AUROC" if metric == "auroc" else "Brier score (lower is better)")
        ax.grid(axis="y", color="#E5E7EB", lw=0.7)
    fig.suptitle("PIDD participant-level calibrated performance (development)", fontweight="bold", color="#0B2545")
    fig.tight_layout()
    save_figure(fig, "pidd_model_performance.png")

    risk = pd.read_csv(STUDY / "selective_prediction/risk_coverage_metrics.csv")
    risk = risk[(risk.system == "availability_router") & (risk.scenario == "full")].sort_values("actual_coverage")
    fig, ax1 = plt.subplots(figsize=(6.8, 3.25))
    ax2 = ax1.twinx()
    ax1.plot(risk.actual_coverage * 100, risk.brier_score, marker="o", color="#1F4D78", label="Brier score")
    ax2.plot(risk.actual_coverage * 100, risk.positive_event_coverage * 100, marker="s", color="#9B1C1C", label="Positive-event coverage")
    ax1.set_xlabel("Accepted participants (%)")
    ax1.set_ylabel("Brier score (lower is better)", color="#1F4D78")
    ax2.set_ylabel("Positive events retained (%)", color="#9B1C1C")
    ax1.set_xlim(68, 102)
    ax1.grid(axis="both", color="#E5E7EB", lw=0.7)
    lines = ax1.get_lines() + ax2.get_lines()
    ax1.legend(lines, [line.get_label() for line in lines], loc="upper left", frameon=False)
    ax1.set_title("Selective prediction improves retained-case loss but drops positive events", fontweight="bold", color="#0B2545")
    fig.tight_layout()
    save_figure(fig, "pidd_risk_coverage.png")

    stress = pd.read_csv(STUDY / "missingness_stress/summary_metrics.csv")
    fig, axes = plt.subplots(1, 2, figsize=(7.3, 3.1), sharex=True)
    styles = {
        ("random_forest", "mcar_independent"): ("#1F4D78", "o", "RF, MCAR-like"),
        ("random_forest", "structured_block"): ("#1F4D78", "s", "RF, block"),
        ("xgboost", "mcar_independent"): ("#9B1C1C", "o", "XGB, MCAR-like"),
        ("xgboost", "structured_block"): ("#9B1C1C", "s", "XGB, block"),
    }
    for key, (color, marker, label) in styles.items():
        frame = stress[(stress.model == key[0]) & (stress.mechanism == key[1])].sort_values("severity")
        axes[0].plot(frame.severity * 100, frame.brier_score_mean, color=color, marker=marker, label=label)
    coverage_styles = {
        "mcar_independent": ("#1F4D78", "o", "MCAR-like"),
        "structured_block": ("#9B1C1C", "s", "Structured block"),
    }
    for mechanism, (color, marker, label) in coverage_styles.items():
        frame = stress[stress.mechanism == mechanism].groupby("severity", as_index=False)["mean_supported_panel_coverage"].mean()
        axes[1].plot(frame.severity * 100, frame.mean_supported_panel_coverage * 100, color=color, marker=marker, label=label)
    axes[0].set_ylabel("Brier score")
    axes[0].set_title("Probability loss")
    axes[1].set_ylabel("Supported-panel coverage (%)")
    axes[1].set_title("Applicability")
    for ax in axes:
        ax.set_xlabel("Additional dropout severity (%)")
        ax.grid(axis="both", color="#E5E7EB", lw=0.7)
    axes[0].legend(frameon=False, fontsize=8)
    axes[1].legend(frameon=False, fontsize=8)
    fig.suptitle("PIDD missingness stress (development)", fontweight="bold", color="#0B2545")
    fig.tight_layout()
    save_figure(fig, "pidd_missingness_stress.png")

    sylhet_ci = pd.read_csv(SYLHET_STUDY / "participant_confidence_intervals.csv")
    sylhet_ci = sylhet_ci[(sylhet_ci["probability_version"] == "calibrated") & (sylhet_ci["threshold_policy"] == "fixed_0_5")]
    sylhet_routing = pd.read_csv(SYLHET_STUDY / "availability_routing/summary_metrics.csv")
    fig, axes = plt.subplots(1, 2, figsize=(7.3, 3.15))
    frame = sylhet_ci[sylhet_ci.metric == "auroc"].set_index("model").loc[order]
    values = frame.estimate.to_numpy()
    errors = np.vstack((values - frame.ci_lower.to_numpy(), frame.ci_upper.to_numpy() - values))
    axes[0].errorbar(range(len(order)), values, yerr=errors, fmt="o", color="#1F4D78", ecolor="#7A9BB8", capsize=3, lw=1.2)
    axes[0].set_xticks(range(len(order)), labels)
    axes[0].set_ylim(0.88, 1.005)
    axes[0].set_ylabel("AUROC")
    axes[0].set_title("Grouped model discrimination")
    axes[0].grid(axis="y", color="#E5E7EB", lw=0.7)
    scenario_order = ["minimal_polyuria_polydipsia", "classic_symptoms", "core_symptoms", "core_questionnaire", "full"]
    scenario_labels = ["2", "4", "6", "10", "16"]
    for system, color, marker, label in (
        ("availability_router", "#1F4D78", "o", "Availability router"),
        ("robust_single_model", "#9B1C1C", "s", "Robust fixed model"),
    ):
        panel = sylhet_routing[sylhet_routing.system == system].set_index("scenario").loc[scenario_order]
        axes[1].plot(range(len(scenario_order)), panel.brier_score, color=color, marker=marker, label=label)
    axes[1].set_xticks(range(len(scenario_order)), scenario_labels)
    axes[1].set_xlabel("Available features")
    axes[1].set_ylabel("Brier score (lower is better)")
    axes[1].set_title("Probability loss by panel")
    axes[1].grid(axis="y", color="#E5E7EB", lw=0.7)
    axes[1].legend(frameon=False, fontsize=8)
    fig.suptitle("Sylhet grouped development evidence", fontweight="bold", color="#0B2545")
    fig.tight_layout()
    save_figure(fig, "sylhet_performance_and_panels.png")


def build_docx(source_name, output_name, title, subtitle, short_title):
    source = PACKAGE / source_name
    doc = Document()
    configure_document(doc, short_title)
    bullet_id, decimal_id = add_numbering_definitions(doc)
    add_cover(doc, title, subtitle)
    render_markdown(doc, source, bullet_id, decimal_id)
    core = doc.core_properties
    core.title = title
    core.subject = "Development-only conference package"
    core.keywords = "diabetes screening, availability routing, calibration, abstention"
    core.author = "Project authors"
    core.comments = "Development evidence; not authorized for submission"
    GENERATED.mkdir(parents=True, exist_ok=True)
    doc.save(GENERATED / output_name)


def main():
    build_figures()
    build_docx(
        "Conference_Manuscript_Development_Draft.md",
        "Conference_Manuscript_Development_Draft.docx",
        "Availability-Aware Diabetes Screening Under Incomplete Predictor Panels",
        "A multi-environment development study",
        "Availability-aware diabetes screening | Development manuscript",
    )
    build_docx(
        "Supplementary_Appendix_Development_Draft.md",
        "Supplementary_Appendix_Development_Draft.docx",
        "Supplementary Appendix",
        "Development methods, evidence, and reproducibility map",
        "Availability-aware diabetes screening | Supplementary appendix",
    )


if __name__ == "__main__":
    main()
