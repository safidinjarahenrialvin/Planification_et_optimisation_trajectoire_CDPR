"""Tests de création sûre des snapshots explicites."""
from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from shutil import copytree

import pytest

import services.snapshot_service as snapshot_module
from services.result_service import ResultService
from services.snapshot_service import SnapshotCreationError, SnapshotService


REFERENCE = Path(__file__).parent / "fixtures" / "reference_run"


def _artifact_inventory(run_dir: Path) -> list[str]:
    return sorted(
        path.relative_to(run_dir).as_posix()
        for path in run_dir.rglob("*")
        if path.is_file() and path.name != "run_manifest.json"
    )


def _prepare_run(
    tmp_path: Path,
    *,
    status: str = "COMPLETED",
) -> tuple[Path, Path, Path]:
    runs_root = tmp_path / "runs"
    run_dir = runs_root / "reference"
    runs_root.mkdir()
    copytree(REFERENCE, run_dir)
    config = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
    validation = json.loads(
        (run_dir / "validation_report.json").read_text(encoding="utf-8")
    )
    manifest = {
        "schema_version": 1,
        "status": status,
        "fingerprint": config["fingerprint"],
        "completed_steps": [
            "4_point_generator",
            "5_point_filter",
            "6_cost_calculator",
            "7_optimizer",
            "8_extractor",
            "9_profiler",
            "10_validator",
            "11_comparator",
        ],
        "available_artifacts": _artifact_inventory(run_dir),
        "validation_status": validation["overall_status"],
    }
    (run_dir / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return runs_root, run_dir, tmp_path / "snapshots"


def _read_manifest(run_dir: Path) -> dict:
    return json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))


def _write_manifest(run_dir: Path, manifest: dict) -> None:
    (run_dir / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def test_create_snapshot_copies_and_revalidates_complete_run(tmp_path: Path) -> None:
    runs_root, run_dir, snapshots_root = _prepare_run(tmp_path)

    snapshot = SnapshotService.create_snapshot(
        run_dir,
        "reference-accepted",
        runs_root=runs_root,
        snapshots_root=snapshots_root,
    )

    assert snapshot == snapshots_root / "reference-accepted"
    assert (snapshot / "run_manifest.json").is_file()
    assert (snapshot / "config.json").read_bytes() == (run_dir / "config.json").read_bytes()
    assert (snapshot / ".config_hash").read_bytes() == (run_dir / ".config_hash").read_bytes()
    assert _artifact_inventory(snapshot) == _artifact_inventory(run_dir)
    assert ResultService.load(snapshot).validation_status == "PASS"
    assert ResultService.discover_snapshots(snapshots_root) == [snapshot]
    assert _read_manifest(run_dir)["status"] == "COMPLETED"


@pytest.mark.parametrize("status", ["FAILED", "CANCELLED", "RUNNING"])
def test_create_snapshot_rejects_non_completed_run(
    tmp_path: Path,
    status: str,
) -> None:
    runs_root, run_dir, snapshots_root = _prepare_run(tmp_path, status=status)

    with pytest.raises(SnapshotCreationError, match=f"{status}"):
        SnapshotService.create_snapshot(
            run_dir,
            "should-not-exist",
            runs_root=runs_root,
            snapshots_root=snapshots_root,
        )

    assert not snapshots_root.exists()


def test_create_snapshot_requires_manifest(tmp_path: Path) -> None:
    runs_root, run_dir, snapshots_root = _prepare_run(tmp_path)
    (run_dir / "run_manifest.json").unlink()

    with pytest.raises(SnapshotCreationError, match=r"[Mm]anifeste"):
        SnapshotService.create_snapshot(
            run_dir,
            "missing-manifest",
            runs_root=runs_root,
            snapshots_root=snapshots_root,
        )


def test_create_snapshot_rejects_malformed_or_unsupported_manifest(
    tmp_path: Path,
) -> None:
    runs_root, run_dir, snapshots_root = _prepare_run(tmp_path)
    (run_dir / "run_manifest.json").write_text("[]", encoding="utf-8")

    with pytest.raises(SnapshotCreationError, match="objet JSON"):
        SnapshotService.create_snapshot(
            run_dir,
            "bad-manifest",
            runs_root=runs_root,
            snapshots_root=snapshots_root,
    )


def test_create_snapshot_rejects_unsupported_manifest_schema(tmp_path: Path) -> None:
    runs_root, run_dir, snapshots_root = _prepare_run(tmp_path)
    manifest = _read_manifest(run_dir)
    manifest["schema_version"] = 2
    _write_manifest(run_dir, manifest)

    with pytest.raises(SnapshotCreationError, match="schema_version"):
        SnapshotService.create_snapshot(
            run_dir,
            "unsupported-schema",
            runs_root=runs_root,
            snapshots_root=snapshots_root,
        )


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda manifest: manifest.update(fingerprint="0000000000000000"), "[Ff]ingerprint"),
        (lambda manifest: manifest.update(available_artifacts=[]), "artefacts déclarés"),
        (lambda manifest: manifest.update(completed_steps=[]), "étapes terminées"),
    ],
)
def test_create_snapshot_rejects_inconsistent_manifest(
    tmp_path: Path,
    mutate,
    message: str,
) -> None:
    runs_root, run_dir, snapshots_root = _prepare_run(tmp_path)
    manifest = _read_manifest(run_dir)
    mutate(manifest)
    _write_manifest(run_dir, manifest)

    with pytest.raises(SnapshotCreationError, match=message):
        SnapshotService.create_snapshot(
            run_dir,
            "inconsistent-manifest",
            runs_root=runs_root,
            snapshots_root=snapshots_root,
        )


def test_create_snapshot_requires_config_hash(tmp_path: Path) -> None:
    runs_root, run_dir, snapshots_root = _prepare_run(tmp_path)
    (run_dir / ".config_hash").unlink()

    with pytest.raises(SnapshotCreationError, match="obligatoires"):
        SnapshotService.create_snapshot(
            run_dir,
            "missing-config-hash",
            runs_root=runs_root,
            snapshots_root=snapshots_root,
        )


def test_create_snapshot_rejects_manifest_path_traversal(tmp_path: Path) -> None:
    runs_root, run_dir, snapshots_root = _prepare_run(tmp_path)
    manifest = _read_manifest(run_dir)
    manifest["available_artifacts"] = ["../outside.txt"]
    _write_manifest(run_dir, manifest)

    with pytest.raises(SnapshotCreationError, match="Chemin d’artefact invalide"):
        SnapshotService.create_snapshot(
            run_dir,
            "unsafe-manifest-path",
            runs_root=runs_root,
            snapshots_root=snapshots_root,
        )


@pytest.mark.parametrize(
    "snapshot_name",
    ["", " ", ".", "..", "../outside", "nested/name", "name with space", ".hidden"],
)
def test_create_snapshot_rejects_unsafe_names(
    tmp_path: Path,
    snapshot_name: str,
) -> None:
    runs_root, run_dir, snapshots_root = _prepare_run(tmp_path)

    with pytest.raises(SnapshotCreationError, match=r"[Nn]om"):
        SnapshotService.create_snapshot(
            run_dir,
            snapshot_name,
            runs_root=runs_root,
            snapshots_root=snapshots_root,
        )

    assert not snapshots_root.exists()


def test_create_snapshot_rejects_source_outside_runs_root(tmp_path: Path) -> None:
    _, run_dir, snapshots_root = _prepare_run(tmp_path)
    outside_root = tmp_path / "other-runs"

    with pytest.raises(SnapshotCreationError, match="sous-répertoire direct"):
        SnapshotService.create_snapshot(
            run_dir,
            "outside",
            runs_root=outside_root,
            snapshots_root=snapshots_root,
        )


def test_create_snapshot_rejects_symlink_artifact(tmp_path: Path) -> None:
    runs_root, run_dir, snapshots_root = _prepare_run(tmp_path)
    outside_file = tmp_path / "secret.txt"
    outside_file.write_text("not a run artifact", encoding="utf-8")
    (run_dir / "linked.txt").symlink_to(outside_file)
    manifest = _read_manifest(run_dir)
    manifest["available_artifacts"] = _artifact_inventory(run_dir)
    _write_manifest(run_dir, manifest)

    with pytest.raises(SnapshotCreationError, match=r"[Ll]ien symbolique"):
        SnapshotService.create_snapshot(
            run_dir,
            "symlink-run",
            runs_root=runs_root,
            snapshots_root=snapshots_root,
        )


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="fifos non disponibles")
def test_create_snapshot_rejects_special_file(tmp_path: Path) -> None:
    runs_root, run_dir, snapshots_root = _prepare_run(tmp_path)
    os.mkfifo(run_dir / "special-pipe")

    with pytest.raises(SnapshotCreationError, match="Fichier spécial interdit"):
        SnapshotService.create_snapshot(
            run_dir,
            "special-file-run",
            runs_root=runs_root,
            snapshots_root=snapshots_root,
        )


@pytest.mark.parametrize("target_kind", ["file", "directory", "symlink"])
def test_create_snapshot_does_not_overwrite_existing_target(
    tmp_path: Path,
    target_kind: str,
) -> None:
    runs_root, run_dir, snapshots_root = _prepare_run(tmp_path)
    target = snapshots_root / "keep-me"
    target.parent.mkdir(parents=True)
    if target_kind == "file":
        target.write_text("existing file", encoding="utf-8")
    elif target_kind == "directory":
        target.mkdir()
        (target / "important.txt").write_text("existing", encoding="utf-8")
    else:
        protected = tmp_path / "protected"
        protected.mkdir()
        (protected / "important.txt").write_text("existing", encoding="utf-8")
        target.symlink_to(protected, target_is_directory=True)

    with pytest.raises(SnapshotCreationError, match="existe déjà"):
        SnapshotService.create_snapshot(
            run_dir,
            "keep-me",
            runs_root=runs_root,
            snapshots_root=snapshots_root,
        )

    if target_kind == "file":
        assert target.read_text(encoding="utf-8") == "existing file"
    elif target_kind == "directory":
        assert (target / "important.txt").read_text(encoding="utf-8") == "existing"
    else:
        assert target.is_symlink()
        assert (target / "important.txt").read_text(encoding="utf-8") == "existing"


def test_snapshot_publication_does_not_overwrite_target_created_during_copy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runs_root, run_dir, snapshots_root = _prepare_run(tmp_path)
    original_publish = SnapshotService._rename_directory_no_replace
    target = snapshots_root / "raced"

    def create_target_then_publish(staging: Path, destination: Path) -> None:
        destination.mkdir()
        (destination / "important.txt").write_text("keep", encoding="utf-8")
        original_publish(staging, destination)

    monkeypatch.setattr(
        snapshot_module.SnapshotService,
        "_rename_directory_no_replace",
        staticmethod(create_target_then_publish),
    )

    with pytest.raises(SnapshotCreationError, match="existe déjà"):
        SnapshotService.create_snapshot(
            run_dir,
            "raced",
            runs_root=runs_root,
            snapshots_root=snapshots_root,
        )

    assert (target / "important.txt").read_text(encoding="utf-8") == "keep"
    assert not any(path.name.startswith(".raced.staging-") for path in snapshots_root.iterdir())


def test_concurrent_snapshot_publications_to_same_name_never_overwrite(
    tmp_path: Path,
) -> None:
    runs_root, run_dir, snapshots_root = _prepare_run(tmp_path)

    def create() -> Path | SnapshotCreationError:
        try:
            return SnapshotService.create_snapshot(
                run_dir,
                "concurrent",
                runs_root=runs_root,
                snapshots_root=snapshots_root,
            )
        except SnapshotCreationError as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: create(), range(2)))

    successes = [result for result in results if isinstance(result, Path)]
    failures = [result for result in results if isinstance(result, SnapshotCreationError)]
    snapshot = snapshots_root / "concurrent"
    assert successes == [snapshot]
    assert len(failures) == 1
    assert "existe déjà" in str(failures[0])
    assert ResultService.load(snapshot).validation_status == "PASS"
    assert not any(
        path.name.startswith(".concurrent.staging-")
        for path in snapshots_root.iterdir()
    )


def test_snapshot_aborts_if_source_changes_during_copy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runs_root, run_dir, snapshots_root = _prepare_run(tmp_path)
    original_copy = SnapshotService._copy_tree_private

    def copy_then_change(source: Path, destination: Path) -> None:
        original_copy(source, destination)
        with (source / "hypotheses_report.md").open("a", encoding="utf-8") as stream:
            stream.write("\nchanged while snapshotting")

    monkeypatch.setattr(
        snapshot_module.SnapshotService,
        "_copy_tree_private",
        staticmethod(copy_then_change),
    )

    with pytest.raises(SnapshotCreationError, match="changé pendant la copie"):
        SnapshotService.create_snapshot(
            run_dir,
            "changed-source",
            runs_root=runs_root,
            snapshots_root=snapshots_root,
        )

    assert not (snapshots_root / "changed-source").exists()
    assert not any(
        path.name.startswith(".changed-source.staging-")
        for path in snapshots_root.iterdir()
    )


def test_create_snapshot_cleans_temporary_directory_after_copy_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runs_root, run_dir, snapshots_root = _prepare_run(tmp_path)

    def fail_copy(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(snapshot_module.shutil, "copyfileobj", fail_copy)

    with pytest.raises(SnapshotCreationError, match="copie"):
        SnapshotService.create_snapshot(
            run_dir,
            "copy-failure",
            runs_root=runs_root,
            snapshots_root=snapshots_root,
        )

    assert list(snapshots_root.iterdir()) == []
