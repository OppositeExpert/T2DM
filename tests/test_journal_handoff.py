"""Privacy, archive safety and exact-value checks for the final handoff."""
import stat
import zipfile

import pytest

from diabetes_pipeline.journal_revision.handoff import csv_bytes, read_rows, safe_member, reconstruct


@pytest.mark.parametrize("name", ["../outside.md", "/absolute.md", "outputs/model.json", "safe/model.joblib", "a\\b.md", "C:/x.md"])
def test_archive_rejects_unsafe_or_private_members(name):
    with pytest.raises(ValueError):
        safe_member(zipfile.ZipInfo(name))


def test_archive_rejects_symlinks():
    info = zipfile.ZipInfo("safe.md")
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    with pytest.raises(ValueError):
        safe_member(info)


def test_archive_accepts_safe_regular_report():
    info = zipfile.ZipInfo("analysis/journal_revision/report.md")
    info.external_attr = (stat.S_IFREG | 0o644) << 16
    safe_member(info)


def test_patient_identifiers_cannot_be_curated(tmp_path):
    path = tmp_path / "table.csv"
    path.write_text("dataset,row_id,auroc\npidd,secret,0.8\n")
    with pytest.raises(ValueError):
        read_rows(path)


def test_exact_csv_projection_preserves_small_p_values_and_decimal_strings(tmp_path):
    path = tmp_path / "table.csv"
    path.write_text("dataset,p,value\npidd,0.00000000000017,0.0019763328600674868\n")
    columns, rows = read_rows(path)
    assert csv_bytes(columns, rows).decode() == path.read_text()


def test_reconstruction_refuses_existing_evidence(tmp_path):
    (tmp_path / "keep.md").write_text("preserve")
    with pytest.raises(FileExistsError):
        reconstruct(tmp_path)
    assert (tmp_path / "keep.md").read_text() == "preserve"
