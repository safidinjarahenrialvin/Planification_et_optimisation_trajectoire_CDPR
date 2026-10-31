"""Création explicite et sûre de snapshots à partir de runs locaux terminés."""
from __future__ import annotations

import ctypes
import errno
import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

from services.result_service import ResultLoadError, ResultService


class SnapshotCreationError(RuntimeError):
    """Indique qu’un run ne peut pas être publié comme snapshot."""


class SnapshotService:
    """Valide, copie et publie un run complet sous ``data/snapshots``."""

    _NAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
    _FINGERPRINT_PATTERN = re.compile(r"[0-9a-f]{16}\Z")
    _MANIFEST_NAME = "run_manifest.json"
    _REQUIRED_STEPS = frozenset(
        {
            "4_point_generator",
            "5_point_filter",
            "6_cost_calculator",
            "7_optimizer",
            "8_extractor",
            "9_profiler",
            "10_validator",
            "11_comparator",
        }
    )

    @classmethod
    def is_local_run_path(
        cls,
        run_dir: Path,
        *,
        runs_root: Path = Path("data/runs"),
    ) -> bool:
        """Retourne vrai pour un run direct de ``runs_root``, sans lien symbolique."""
        run_path = Path(run_dir)
        root_path = Path(runs_root)
        if run_path.is_symlink() or root_path.is_symlink():
            return False
        try:
            resolved_run = run_path.resolve(strict=True)
            resolved_root = root_path.resolve(strict=True)
        except (OSError, RuntimeError):
            return False
        return resolved_run.is_dir() and resolved_run.parent == resolved_root

    @classmethod
    def suggested_name(cls, run_id: str) -> str:
        """Construit un nom de proposition valide et distinct pour l’interface."""
        from datetime import datetime, timezone

        stem = re.sub(r"[^A-Za-z0-9._-]+", "-", str(run_id)).strip(".-_")
        stem = (stem or "run")[:40].rstrip(".-_") or "run"
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        return f"{stem}-{timestamp}"

    @classmethod
    def create_snapshot(
        cls,
        run_dir: Path,
        snapshot_name: str,
        *,
        runs_root: Path = Path("data/runs"),
        snapshots_root: Path = Path("data/snapshots"),
    ) -> Path:
        """Crée un snapshot validé, sans jamais remplacer une destination existante.

        La source doit être un sous-répertoire direct de ``runs_root``. La copie
        est préparée sous ``snapshots_root``, contrôlée à nouveau, puis publiée
        par le renommage Linux ``renameat2(RENAME_NOREPLACE)``.
        """
        cls._validate_name(snapshot_name)
        if not cls.is_local_run_path(run_dir, runs_root=runs_root):
            raise SnapshotCreationError(
                "La source doit être un run local, sous-répertoire direct de data/runs."
            )
        source = Path(run_dir).resolve(strict=True)
        source_digest_before = cls._validate_run_directory(source)

        root = Path(snapshots_root)
        if root.is_symlink():
            raise SnapshotCreationError(
                "Le répertoire des snapshots ne peut pas être un lien symbolique."
            )
        try:
            root.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise SnapshotCreationError(
                f"Impossible de préparer le répertoire des snapshots : {exc}"
            ) from exc
        if root.is_symlink() or not root.is_dir():
            raise SnapshotCreationError(
                "La destination des snapshots doit être un répertoire réel."
            )
        root = root.resolve(strict=True)
        if source == root or source in root.parents:
            raise SnapshotCreationError(
                "Le répertoire des snapshots ne peut pas être créé dans le run source."
            )

        target = root / snapshot_name
        if cls._path_exists(target):
            raise SnapshotCreationError(
                f"Un snapshot nommé {snapshot_name!r} existe déjà. Aucun fichier n’a été remplacé."
            )

        staging: Path | None = None
        try:
            staging = Path(
                tempfile.mkdtemp(prefix=f".{snapshot_name}.staging-", dir=root)
            )
            cls._copy_tree_private(source, staging)
            staged_digest = cls._validate_run_directory(staging)
            source_digest_after = cls._validate_run_directory(source)
            if not (
                source_digest_before == staged_digest == source_digest_after
            ):
                raise SnapshotCreationError(
                    "Le contenu du run a changé pendant la copie; le snapshot a été annulé."
                )
            cls._rename_directory_no_replace(staging, target)
            staging = None
            return target
        except SnapshotCreationError:
            raise
        except FileExistsError as exc:
            raise SnapshotCreationError(
                f"Un snapshot nommé {snapshot_name!r} existe déjà. Aucun fichier n’a été remplacé."
            ) from exc
        except (OSError, shutil.Error) as exc:
            raise SnapshotCreationError(
                f"Échec de la copie ou de la publication du snapshot : {exc}"
            ) from exc
        finally:
            if staging is not None and staging.exists():
                shutil.rmtree(staging, ignore_errors=True)

    @classmethod
    def _validate_name(cls, snapshot_name: str) -> None:
        if (
            not isinstance(snapshot_name, str)
            or snapshot_name != snapshot_name.strip()
            or not cls._NAME_PATTERN.fullmatch(snapshot_name)
        ):
            raise SnapshotCreationError(
                "Nom de snapshot invalide : utilisez 1 à 64 caractères ASCII "
                "(lettres, chiffres, point, tiret ou tiret bas), sans espace ni séparateur."
            )

    @classmethod
    def _validate_run_directory(cls, run_dir: Path) -> dict[str, str]:
        if run_dir.is_symlink() or not run_dir.is_dir():
            raise SnapshotCreationError("Le répertoire du run est absent ou invalide.")

        digests = cls._tree_digests(run_dir)
        manifest_path = run_dir / cls._MANIFEST_NAME
        if not manifest_path.is_file():
            raise SnapshotCreationError(
                "Manifeste de run absent (run_manifest.json). Relancez avec le pipeline actuel."
            )
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SnapshotCreationError(
                f"Manifeste illisible : {exc}"
            ) from exc
        if not isinstance(manifest, dict):
            raise SnapshotCreationError("Le manifeste doit être un objet JSON.")
        if type(manifest.get("schema_version")) is not int or manifest["schema_version"] != 1:
            raise SnapshotCreationError(
                "Version de manifeste non prise en charge : schema_version attendu à 1."
            )
        status = manifest.get("status")
        if status != "COMPLETED":
            raise SnapshotCreationError(
                f"Snapshot refusé : le statut du run est {status!r}, attendu 'COMPLETED'."
            )

        completed_steps = manifest.get("completed_steps")
        if (
            not isinstance(completed_steps, list)
            or any(not isinstance(step, str) for step in completed_steps)
            or len(set(completed_steps)) != len(completed_steps)
            or not cls._REQUIRED_STEPS.issubset(completed_steps)
        ):
            raise SnapshotCreationError(
                "Le manifeste ne confirme pas toutes les étapes terminées du pipeline."
            )

        fingerprint = manifest.get("fingerprint")
        if (
            not isinstance(fingerprint, str)
            or not cls._FINGERPRINT_PATTERN.fullmatch(fingerprint)
        ):
            raise SnapshotCreationError(
                "fingerprint invalide dans run_manifest.json."
            )

        config_path = run_dir / "config.json"
        hash_path = run_dir / ".config_hash"
        if not config_path.is_file() or not hash_path.is_file():
            raise SnapshotCreationError(
                "Snapshot refusé : config.json et .config_hash sont obligatoires."
            )

        declared = manifest.get("available_artifacts")
        if not isinstance(declared, list) or any(
            not isinstance(item, str) for item in declared
        ):
            raise SnapshotCreationError(
                "Le manifeste doit contenir une liste available_artifacts."
            )
        cls._validate_relative_artifact_paths(declared)
        actual = sorted(
            path for path in digests if Path(path).name != cls._MANIFEST_NAME
        )
        if declared != actual:
            raise SnapshotCreationError(
                "Les artefacts déclarés dans le manifeste ne correspondent pas "
                "à l’inventaire réel du run."
            )

        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config_fingerprint = config.get("fingerprint") if isinstance(config, dict) else None
            stored_hash = hash_path.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SnapshotCreationError(
                f"Configuration ou empreinte illisible : {exc}"
            ) from exc
        if (
            config_fingerprint != fingerprint
            or stored_hash != fingerprint
        ):
            raise SnapshotCreationError(
                "Fingerprint divergent entre run_manifest.json, config.json et .config_hash."
            )

        try:
            ResultService.load(run_dir)
        except ResultLoadError as exc:
            raise SnapshotCreationError(
                f"Les artefacts du run ne passent pas la validation : {exc}"
            ) from exc
        return digests

    @classmethod
    def _tree_digests(cls, root: Path) -> dict[str, str]:
        digests: dict[str, str] = {}
        try:
            for path in sorted(root.rglob("*")):
                if path.is_symlink():
                    raise SnapshotCreationError(
                        f"Lien symbolique interdit dans le run : {path.relative_to(root)}."
                    )
                mode = path.lstat().st_mode
                if stat.S_ISDIR(mode):
                    continue
                if not stat.S_ISREG(mode):
                    raise SnapshotCreationError(
                        f"Fichier spécial interdit dans le run : {path.relative_to(root)}."
                    )
                relative = path.relative_to(root).as_posix()
                digest = hashlib.sha256()
                with path.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(chunk)
                digests[relative] = digest.hexdigest()
        except SnapshotCreationError:
            raise
        except OSError as exc:
            raise SnapshotCreationError(
                f"Impossible de lire complètement le run : {exc}"
            ) from exc
        return digests

    @staticmethod
    def _validate_relative_artifact_paths(paths: list[str]) -> None:
        if paths != sorted(set(paths)):
            raise SnapshotCreationError(
                "available_artifacts doit être trié et ne contenir aucun doublon."
            )
        for value in paths:
            parsed = PurePosixPath(value)
            if (
                not value
                or "\\" in value
                or "\x00" in value
                or parsed.is_absolute()
                or str(parsed) != value
                or any(part in {"", ".", ".."} for part in parsed.parts)
            ):
                raise SnapshotCreationError(
                    f"Chemin d’artefact invalide dans le manifeste : {value!r}."
                )

    @staticmethod
    def _copy_tree_private(source: Path, destination: Path) -> None:
        """Copie les fichiers ordinaires sans suivre de symlink ni bit spécial."""
        for path in sorted(source.rglob("*")):
            relative = path.relative_to(source)
            target = destination / relative
            if path.is_symlink():
                raise SnapshotCreationError(
                    f"Lien symbolique interdit dans le run : {relative}."
                )
            mode = path.lstat().st_mode
            if stat.S_ISDIR(mode):
                target.mkdir(mode=0o700, parents=True, exist_ok=True)
                continue
            if not stat.S_ISREG(mode):
                raise SnapshotCreationError(
                    f"Fichier spécial interdit dans le run : {relative}."
                )
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            with path.open("rb") as source_stream, target.open("xb") as target_stream:
                shutil.copyfileobj(source_stream, target_stream, length=1024 * 1024)

    @staticmethod
    def _path_exists(path: Path) -> bool:
        return path.exists() or path.is_symlink()

    @staticmethod
    def _rename_directory_no_replace(source: Path, target: Path) -> None:
        """Publie un répertoire de façon atomique, sans écraser une cible Linux."""
        if not sys_platform_linux():
            raise SnapshotCreationError(
                "La publication atomique sans écrasement nécessite Linux/renameat2."
            )
        libc = ctypes.CDLL(None, use_errno=True)
        renameat2: Any = getattr(libc, "renameat2", None)
        if renameat2 is None:
            raise SnapshotCreationError(
                "renameat2 n’est pas disponible; aucun snapshot n’a été publié."
            )
        renameat2.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        renameat2.restype = ctypes.c_int
        at_fdcwd = -100
        rename_noreplace = 1
        result = renameat2(
            at_fdcwd,
            os.fsencode(source),
            at_fdcwd,
            os.fsencode(target),
            rename_noreplace,
        )
        if result == 0:
            return
        error_number = ctypes.get_errno()
        if error_number == errno.EEXIST:
            raise FileExistsError(error_number, os.strerror(error_number), target)
        if error_number in {errno.ENOSYS, errno.EINVAL}:
            raise SnapshotCreationError(
                "Le système de fichiers ne prend pas en charge la publication sans écrasement."
            )
        raise OSError(error_number, os.strerror(error_number), str(target))


def sys_platform_linux() -> bool:
    """Retourne vrai uniquement lorsque l’API atomique Linux est disponible."""
    import sys

    return sys.platform.startswith("linux")
