"""Cliente ESGF/CMIP6.

Parser dos scripts wget gerados pelo MetaGrid ESGF e helpers para download
paralelo com validação de checksum. Implementa a §7.1 do project.md sem o
container Airflow (ver ADR-0002 e ADR-0003).
"""

from __future__ import annotations

import asyncio
import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from climate_esg.logging import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Modelo de dados
# ---------------------------------------------------------------------------

# Convenção CMIP6 do nome do arquivo:
#   <variable>_<table>_<source>_<experiment>_<member>_<grid>_<period>.nc
# Ex.: rsdt_Amon_EC-Earth3_historical_r120i1p1f1_gr_198801-198812.nc
_FILENAME_RE = re.compile(
    r"^(?P<variable>[A-Za-z0-9]+)_"
    r"(?P<table>[A-Za-z]+)_"
    r"(?P<source>[A-Za-z0-9.\-]+)_"
    r"(?P<experiment>[A-Za-z0-9.\-]+)_"
    r"(?P<member>r\d+i\d+p\d+f\d+)_"
    r"(?P<grid>g[a-z0-9]+)_"
    r"(?P<period>\d{6}-\d{6})\.nc$"
)


@dataclass(frozen=True, slots=True)
class CMIP6Identifier:
    """Decomposição CF do nome de um arquivo CMIP6."""

    variable: str
    table: str
    source: str
    experiment: str
    member: str
    grid: str
    period: str

    @classmethod
    def from_filename(cls, filename: str) -> "CMIP6Identifier | None":
        """Extrai metadado CF do nome. Retorna None se o nome não bater."""
        m = _FILENAME_RE.match(Path(filename).name)
        if not m:
            return None
        return cls(**m.groupdict())


@dataclass(frozen=True, slots=True)
class ESGFFile:
    """Manifesto de um único arquivo ESGF a baixar."""

    filename: str
    url: str
    checksum: str
    checksum_type: str = "sha256"

    @property
    def cmip6(self) -> CMIP6Identifier | None:
        return CMIP6Identifier.from_filename(self.filename)


@dataclass
class ESGFManifest:
    """Coleção de arquivos extraídos de um wget script."""

    source_path: Path
    files: list[ESGFFile] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.files)

    def __iter__(self) -> Iterator[ESGFFile]:
        return iter(self.files)

    def by_variable(self, variable: str) -> list[ESGFFile]:
        return [f for f in self.files if (id_ := f.cmip6) and id_.variable == variable]

    def variables(self) -> set[str]:
        return {id_.variable for f in self.files if (id_ := f.cmip6)}

    def members(self) -> set[str]:
        return {id_.member for f in self.files if (id_ := f.cmip6)}

    def experiments(self) -> set[str]:
        return {id_.experiment for f in self.files if (id_ := f.cmip6)}


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

# Cada linha dentro do bloco download_files tem 4 campos quote-delimitados:
#   'filename' 'url' 'checksum_type' 'checksum'
_LINE_RE = re.compile(
    r"^\s*"
    r"'(?P<f>[^']+)'\s+"
    r"'(?P<u>[^']+)'\s+"
    r"'(?P<ct>[^']+)'\s+"
    r"'(?P<c>[^']+)'\s*$"
)


def parse_wget_script(path: str | Path) -> ESGFManifest:
    """Extrai a lista de arquivos de um wget script do MetaGrid ESGF.

    Procura o bloco delimitado por ``download_files="$(cat <<EOF--...`` e
    ``EOF--``. Cada linha não vazia dentro do bloco é uma entrada.

    Levanta:
        FileNotFoundError: se ``path`` não existir.
        ValueError: se nenhum bloco ``download_files`` for encontrado.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"wget script não encontrado: {p}")

    files: list[ESGFFile] = []
    in_block = False
    found_block = False

    with p.open("r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip("\n")

            if not in_block:
                if line.startswith("download_files="):
                    in_block = True
                    found_block = True
                continue

            # Estamos dentro do bloco. EOF-- (e variações) fecham.
            stripped = line.strip()
            if stripped.startswith("EOF--") or stripped == "EOF":
                break
            if not stripped:
                continue

            m = _LINE_RE.match(line)
            if not m:
                # Linha de comentário ou metadado solto, ignora.
                continue

            files.append(
                ESGFFile(
                    filename=m.group("f"),
                    url=m.group("u"),
                    checksum_type=m.group("ct").lower(),
                    checksum=m.group("c"),
                )
            )

    if not found_block:
        raise ValueError(f"bloco download_files não encontrado em {p}")

    log.info(
        "esgf.manifest.parsed",
        path=str(p),
        n_files=len(files),
    )
    return ESGFManifest(source_path=p, files=files)


def parse_wget_directory(directory: str | Path) -> list[ESGFManifest]:
    """Parseia todos os ``wget_script_*.sh`` de um diretório."""
    d = Path(directory)
    if not d.is_dir():
        raise NotADirectoryError(f"esperado diretório: {d}")
    scripts = sorted(d.glob("wget_script_*.sh"))
    return [parse_wget_script(s) for s in scripts]


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------


def _hash_file(path: Path, algo: str) -> str:
    """Computa o checksum de um arquivo em chunks. Não carrega em memória."""
    h = hashlib.new(algo)
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):  # 1 MiB
            h.update(chunk)
    return h.hexdigest()


def verify_checksum(path: Path, expected: str, algo: str = "sha256") -> bool:
    """True se o checksum do arquivo bate com o esperado (case-insensitive)."""
    actual = _hash_file(path, algo)
    return actual.lower() == expected.lower()


@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
)
async def _download_one(
    client: httpx.AsyncClient,
    file: ESGFFile,
    dest_dir: Path,
    *,
    chunk_size: int = 1 << 20,
) -> Path:
    """Baixa um único ESGFFile para ``dest_dir/file.filename``.

    Reusa download anterior se o arquivo já existe e o checksum bate
    (idempotência prevista no project.md §7.1).
    """
    dest = dest_dir / file.filename

    if dest.exists() and verify_checksum(dest, file.checksum, file.checksum_type):
        log.info("esgf.download.skip_existing", filename=file.filename)
        return dest

    tmp = dest.with_suffix(dest.suffix + ".part")
    log.info("esgf.download.start", filename=file.filename, url=file.url)
    async with client.stream("GET", file.url, follow_redirects=True) as resp:
        resp.raise_for_status()
        with tmp.open("wb") as out:
            async for chunk in resp.aiter_bytes(chunk_size):
                out.write(chunk)

    if not verify_checksum(tmp, file.checksum, file.checksum_type):
        tmp.unlink(missing_ok=True)
        raise ValueError(
            f"checksum inválido para {file.filename}; arquivo descartado"
        )

    tmp.rename(dest)
    log.info("esgf.download.ok", filename=file.filename, size=dest.stat().st_size)
    return dest


async def download_manifest_async(
    manifest: ESGFManifest,
    dest_dir: Path,
    *,
    concurrency: int = 4,
    timeout_s: float = 600.0,
) -> list[Path]:
    """Baixa todos os arquivos do manifest em paralelo (concorrência limitada)."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(concurrency)
    timeout = httpx.Timeout(timeout_s, connect=30.0)

    async with httpx.AsyncClient(timeout=timeout, http2=True) as client:

        async def _bounded(f: ESGFFile) -> Path:
            async with sem:
                return await _download_one(client, f, dest_dir)

        return list(await asyncio.gather(*(_bounded(f) for f in manifest.files)))


def download_manifest(
    manifest: ESGFManifest,
    dest_dir: Path,
    *,
    concurrency: int = 4,
    timeout_s: float = 600.0,
) -> list[Path]:
    """Variante síncrona, usável dentro de tasks Prefect que rodam em thread."""
    return asyncio.run(
        download_manifest_async(
            manifest, dest_dir, concurrency=concurrency, timeout_s=timeout_s
        )
    )
