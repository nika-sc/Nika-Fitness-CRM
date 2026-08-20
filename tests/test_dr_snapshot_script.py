"""DR snapshot for hub VPS must wrap archives in 7z AES with encrypted names."""
from pathlib import Path


def test_dr_snapshot_uses_7z_aes_header_encryption():
    src = (
        Path(__file__).resolve().parents[1] / "scripts" / "dr_snapshot_nika_crm_ru.sh"
    ).read_text(encoding="utf-8")
    assert "-mhe=on" in src
    assert "-t7z" in src
    assert "BACKUP_ARCHIVE_PASSWORD" in src
    assert ".7z" in src
    assert 'subtype="xz"' not in src
