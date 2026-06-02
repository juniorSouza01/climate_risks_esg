"""Testes dos helpers puros de linhagem (sem banco)."""

from __future__ import annotations

from climate_esg.governance.lineage import current_git_commit, hash_data_version


def test_hash_data_version_determinista() -> None:
    a = hash_data_version(["b.nc", "a.nc"])
    b = hash_data_version(["a.nc", "b.nc"])  # ordem não importa
    assert a == b


def test_hash_data_version_muda_com_conteudo() -> None:
    assert hash_data_version(["a.nc"]) != hash_data_version(["a.nc", "b.nc"])


def test_hash_data_version_respeita_length() -> None:
    assert len(hash_data_version(["a.nc"], length=8)) == 8
    assert len(hash_data_version(["a.nc"], length=32)) == 32


def test_current_git_commit_retorna_sha_ou_none() -> None:
    commit = current_git_commit()
    # Em repo git: 40 hex chars. Fora de repo/sem git: None. Ambos válidos.
    assert commit is None or (len(commit) == 40 and all(c in "0123456789abcdef" for c in commit))
