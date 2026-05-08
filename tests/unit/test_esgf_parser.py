"""Testes do parser de wget scripts ESGF.

Roda contra os 10 scripts reais arquivados em data/manifests/cmip6_wget/.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from climate_esg.ingestion.esgf_client import (
    CMIP6Identifier,
    ESGFManifest,
    parse_wget_directory,
    parse_wget_script,
)


def test_filename_decomposition() -> None:
    fid = CMIP6Identifier.from_filename(
        "rsdt_Amon_EC-Earth3_historical_r120i1p1f1_gr_198801-198812.nc"
    )
    assert fid is not None
    assert fid.variable == "rsdt"
    assert fid.table == "Amon"
    assert fid.source == "EC-Earth3"
    assert fid.experiment == "historical"
    assert fid.member == "r120i1p1f1"
    assert fid.grid == "gr"
    assert fid.period == "198801-198812"


def test_filename_decomposition_invalid_returns_none() -> None:
    assert CMIP6Identifier.from_filename("not_a_cmip6_file.nc") is None
    assert CMIP6Identifier.from_filename("foo/bar.nc") is None


def test_parse_real_wget_script_returns_nonempty(cmip6_manifest_dir: Path) -> None:
    scripts = sorted(cmip6_manifest_dir.glob("wget_script_*.sh"))
    assert len(scripts) >= 1, "esperava ao menos um wget script arquivado"

    manifest = parse_wget_script(scripts[0])

    assert isinstance(manifest, ESGFManifest)
    assert len(manifest) > 0
    # Todo arquivo deve ter os 4 campos preenchidos
    for f in manifest:
        assert f.filename.endswith(".nc")
        assert f.url.startswith("http")
        assert len(f.checksum) == 64  # SHA256 hex
        assert f.checksum_type == "sha256"


def test_parse_all_real_wget_scripts(cmip6_manifest_dir: Path) -> None:
    manifests = parse_wget_directory(cmip6_manifest_dir)

    assert len(manifests) == 10, "esperava 10 wget scripts arquivados"

    total_files = sum(len(m) for m in manifests)
    assert total_files > 100, f"esperava muitos arquivos no total, achei {total_files}"

    # Deve cobrir EC-Earth3 historical com membros r120/r121/r132
    all_members: set[str] = set()
    all_experiments: set[str] = set()
    all_variables: set[str] = set()
    for m in manifests:
        all_members |= m.members()
        all_experiments |= m.experiments()
        all_variables |= m.variables()

    assert all_experiments == {"historical"}
    assert {"r120i1p1f1", "r121i1p1f1", "r132i1p1f1"} & all_members, (
        f"esperava algum dos membros r120/r121/r132, achei {all_members}"
    )
    # Variáveis esperadas conforme docs/source/project.md §6.3
    assert all_variables & {"rsdt", "tasmin", "hurs", "huss", "prsn", "uo", "sivol"}


def test_parse_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        parse_wget_script(tmp_path / "nope.sh")


def test_parse_no_block_raises(tmp_path: Path) -> None:
    bogus = tmp_path / "bogus.sh"
    bogus.write_text("#!/bin/bash\necho 'hello'\n")
    with pytest.raises(ValueError, match="bloco download_files"):
        parse_wget_script(bogus)


def test_manifest_helpers(cmip6_manifest_dir: Path) -> None:
    scripts = sorted(cmip6_manifest_dir.glob("wget_script_*.sh"))
    manifest = parse_wget_script(scripts[0])

    variables = manifest.variables()
    assert variables, "manifest deve expor variáveis"

    chosen = next(iter(variables))
    subset = manifest.by_variable(chosen)
    assert all((id_ := f.cmip6) and id_.variable == chosen for f in subset)
