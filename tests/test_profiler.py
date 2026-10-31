"""
Tests unitaires — BLOC 9 (TrajectoryProfiler)
===============================================

Référence : contrat de profilage des trajectoires SP2 (BLOC 9).

Vérifie :
  - v = 0 aux extrémités de chaque segment (< 1e-9 m/s, critère §7)
  - |v| ≤ v_max + tolérance partout
  - a_instantanée ≤ a_max + tolérance (hors discontinuités de LSPB)
  - Continuité en position aux jonctions
  - Cohérence des positions d'extrémités avec les waypoints d'entrée
  - Monotonie stricte du temps global
  - Format CSV conforme au contrat §6 étendu
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.config import Config
from src.profiler import TrajectoryProfiler


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------
@pytest.fixture
def cfg() -> Config:
    return Config()


@pytest.fixture
def profiler(cfg: Config) -> TrajectoryProfiler:
    return TrajectoryProfiler(cfg, dt=0.05, min_samples_per_segment=5)


def _traj_synthetic(kind: str = "time_opt") -> pd.DataFrame:
    """
    Trajectoire synthétique : 4 waypoints en L, alignés sur des distances
    connues (0.25 m, 0.25 m, 0.35 m) pour tester les 2 régimes LSPB.
    """
    pts = [
        (0, 0.00, 0.00, 0.45),
        (1, 0.25, 0.00, 0.45),
        (2, 0.50, 0.00, 0.45),
        (3, 0.75, 0.25, 0.45),  # diagonale : dist = sqrt(0.25² + 0.25²) ≈ 0.3536
    ]
    rows = []
    for rank, (pid, x, y, z) in enumerate(pts):
        rows.append({
            "kind": kind, "rank": rank, "point_id": pid,
            "x": x, "y": y, "z": z,
            "cumulative_time_motion_s": 0.0,
            "cumulative_energy_J": 0.0,
        })
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------
# T1 — Format CSV conforme au contrat §6 (étendu)
# ----------------------------------------------------------------------
def test_csv_columns(profiler: TrajectoryProfiler) -> None:
    df = profiler.profile_trajectory("time_opt", _traj_synthetic())
    assert list(df.columns) == [
        "kind", "segment_id", "t", "x", "y", "z", "vx", "vy", "vz",
    ]


# ----------------------------------------------------------------------
# T2 — v = 0 aux extrémités de CHAQUE segment (§7)
# ----------------------------------------------------------------------

def test_v_zero_at_waypoints(profiler: TrajectoryProfiler) -> None:
    """
    v = 0 au DÉBUT du premier segment et à la FIN de chaque segment
    (= à chaque waypoint visité, puisque le robot s'arrête à chaque point).

    Note : avec la déduplication des jonctions, le premier sample d'un
    segment k>0 n'est plus présent dans le profil (il est le dernier
    sample du segment k−1). Il n'y a donc pas de v=0 à vérifier
    séparément pour ces premières lignes.
    """
    df = profiler.profile_trajectory("time_opt", _traj_synthetic())

    # Début du premier segment
    first = df.iloc[0]
    v_first = np.linalg.norm(first[["vx", "vy", "vz"]].to_numpy(float))
    assert v_first < 1e-9, f"v au départ = {v_first}"

    # Fin de chaque segment = waypoint visité
    for seg_id in sorted(df["segment_id"].unique()):
        seg = df[df["segment_id"] == seg_id].sort_values("t")
        v_last = np.linalg.norm(seg.iloc[-1][["vx", "vy", "vz"]].to_numpy(float))
        assert v_last < 1e-9, f"v en fin de segment {seg_id} = {v_last}"

# ----------------------------------------------------------------------
# T3 — |v| ≤ v_max partout
# ----------------------------------------------------------------------
def test_v_max_respected(profiler: TrajectoryProfiler) -> None:
    df = profiler.profile_trajectory("time_opt", _traj_synthetic())
    v_norm = np.sqrt(df["vx"] ** 2 + df["vy"] ** 2 + df["vz"] ** 2)
    # ±1 % de marge (critère §7)
    tol = 0.01 * profiler.config.v_max
    assert (v_norm <= profiler.config.v_max + tol).all(), (
        f"|v| max observé = {v_norm.max():.6f} > v_max = {profiler.config.v_max}"
    )


# ----------------------------------------------------------------------
# T4 — Accélération bornée par a_max (tolérance 5 % pour la discrétisation)
# ----------------------------------------------------------------------
def test_a_max_respected(profiler: TrajectoryProfiler) -> None:
    df = profiler.profile_trajectory("time_opt", _traj_synthetic())
    a_max = profiler.config.a_max
    for seg_id in df["segment_id"].unique():
        seg = df[df["segment_id"] == seg_id].sort_values("t").reset_index(drop=True)
        t = seg["t"].to_numpy(float)
        vx = seg["vx"].to_numpy(float)
        vy = seg["vy"].to_numpy(float)
        vz = seg["vz"].to_numpy(float)
        dt = np.diff(t)
        # Filtrer les dt nuls (extrémités dupliquées entre segments)
        mask = dt > 1e-12
        if not mask.any():
            continue
        ax = np.diff(vx)[mask] / dt[mask]
        ay = np.diff(vy)[mask] / dt[mask]
        az = np.diff(vz)[mask] / dt[mask]
        a_mag = np.sqrt(ax ** 2 + ay ** 2 + az ** 2)
        # Tolérance 5 % (les transitions a_max→0 induisent des spikes
        # d'accélération numériquement grandes — attendu, filtrées par
        # la tolérance large du test diagnostique)
        assert (a_mag <= a_max * 1.05 + 1e-6).all(), (
            f"Segment {seg_id} : |a| max = {a_mag.max():.6f} > "
            f"a_max = {a_max}"
        )


# ----------------------------------------------------------------------
# T5 — Continuité en position aux jonctions (waypoint partagé)
# ----------------------------------------------------------------------
def test_position_continuity_at_junctions(profiler: TrajectoryProfiler) -> None:
    """
    Le dernier sample de chaque segment doit coïncider exactement avec
    le waypoint d'arrivée du segment (source de vérité = trajectoire
    d'entrée, pas la ligne précédente du CSV — plus robuste).

    La continuité entre segments est ainsi garantie par construction :
    W_{k+1} est à la fois l'arrivée du segment k et le départ (conceptuel)
    du segment k+1, mais il n'est écrit qu'une seule fois dans le profil.
    """
    traj = _traj_synthetic()
    traj_sorted = traj.sort_values("rank").reset_index(drop=True)
    df = profiler.profile_trajectory("time_opt", traj)

    for seg_id in sorted(df["segment_id"].unique()):
        last = df[df["segment_id"] == seg_id].sort_values("t").iloc[-1]
        wp_arrival = traj_sorted.iloc[seg_id + 1]
        assert last["x"] == pytest.approx(wp_arrival["x"], abs=1e-9)
        assert last["y"] == pytest.approx(wp_arrival["y"], abs=1e-9)
        assert last["z"] == pytest.approx(wp_arrival["z"], abs=1e-9)



# ----------------------------------------------------------------------
# T6 — Positions d'extrémités = waypoints d'entrée
# ----------------------------------------------------------------------
def test_extremities_match_waypoints(profiler: TrajectoryProfiler) -> None:
    traj = _traj_synthetic()
    df = profiler.profile_trajectory("time_opt", traj)
    seg_ids = sorted(df["segment_id"].unique())
    # Premier point du premier segment = waypoint 0
    p_first = df[df["segment_id"] == seg_ids[0]].sort_values("t").iloc[0]
    traj_sorted = traj.sort_values("rank").reset_index(drop=True)
    wp0 = traj_sorted.iloc[0]
    assert p_first["x"] == pytest.approx(wp0["x"], abs=1e-9)
    assert p_first["y"] == pytest.approx(wp0["y"], abs=1e-9)
    assert p_first["z"] == pytest.approx(wp0["z"], abs=1e-9)
    # Dernier point du dernier segment = waypoint final
    p_last = df[df["segment_id"] == seg_ids[-1]].sort_values("t").iloc[-1]
    wpN = traj_sorted.iloc[-1]
    assert p_last["x"] == pytest.approx(wpN["x"], abs=1e-9)
    assert p_last["y"] == pytest.approx(wpN["y"], abs=1e-9)
    assert p_last["z"] == pytest.approx(wpN["z"], abs=1e-9)


# ----------------------------------------------------------------------
# T7 — Monotonie stricte du temps global
# ----------------------------------------------------------------------
def test_time_monotonic(profiler: TrajectoryProfiler) -> None:
    df = profiler.profile_trajectory("time_opt", _traj_synthetic())
    t = df["t"].to_numpy(float)
    # Strictement croissant (dt > 0 imposé par dt cible et min_samples)
    assert np.all(np.diff(t) > 0), "Le temps global doit être strictement croissant."


# ----------------------------------------------------------------------
# T8 — Régime triangulaire : distance très courte
# ----------------------------------------------------------------------
def test_triangular_regime() -> None:
    """
    Une distance très courte (< 2·d_acc ≈ 0.0675 m) doit produire un
    profil triangulaire : la vitesse de pointe est < v_max.
    """
    cfg = Config()
    prof = TrajectoryProfiler(cfg, dt=0.001, min_samples_per_segment=50)
    # Distance 0.01 m → triangulaire
    d_small = 0.01
    traj = pd.DataFrame([
        {"kind": "x", "rank": 0, "point_id": 0,
         "x": 0.0, "y": 0.0, "z": 0.45,
         "cumulative_time_motion_s": 0.0, "cumulative_energy_J": 0.0},
        {"kind": "x", "rank": 1, "point_id": 1,
         "x": d_small, "y": 0.0, "z": 0.45,
         "cumulative_time_motion_s": 0.0, "cumulative_energy_J": 0.0},
    ])
    df = prof.profile_trajectory("x", traj)
    v_norm = np.sqrt(df["vx"] ** 2 + df["vy"] ** 2 + df["vz"] ** 2)
    v_peak = v_norm.max()
    v_peak_expected = np.sqrt(d_small * cfg.a_max)  # ≈ 0.0173 m/s
    assert v_peak == pytest.approx(v_peak_expected, rel=1e-2)
    assert v_peak < cfg.v_max * 0.5


# ----------------------------------------------------------------------
# T9 — Cas dégénéré d = 0 (waypoints confondus)
# ----------------------------------------------------------------------
def test_zero_distance_segment(cfg: Config) -> None:
    """
    Deux waypoints identiques : segment de longueur nulle → 1 seul
    sample, à la position du waypoint, avec v = 0.
    """
    prof = TrajectoryProfiler(cfg, dt=0.05, min_samples_per_segment=5)
    traj = pd.DataFrame([
        {"kind": "x", "rank": 0, "point_id": 0,
         "x": 0.25, "y": 0.25, "z": 0.45,
         "cumulative_time_motion_s": 0.0, "cumulative_energy_J": 0.0},
        {"kind": "x", "rank": 1, "point_id": 1,
         "x": 0.25, "y": 0.25, "z": 0.45,
         "cumulative_time_motion_s": 0.0, "cumulative_energy_J": 0.0},
    ])
    df = prof.profile_trajectory("x", traj)
    assert len(df) == 1
    assert df.iloc[0]["x"] == pytest.approx(0.25)
    assert df.iloc[0]["y"] == pytest.approx(0.25)
    assert df.iloc[0]["z"] == pytest.approx(0.45)
    assert np.linalg.norm(df.iloc[0][["vx", "vy", "vz"]].to_numpy(float)) < 1e-12


# ----------------------------------------------------------------------
# T10 — run_and_save : 4 fichiers écrits (profiles + 3 par kind)
# ----------------------------------------------------------------------
def test_run_and_save(cfg: Config, tmp_path: Path) -> None:
    prof = TrajectoryProfiler(cfg, dt=0.2, min_samples_per_segment=5)
    traj = pd.concat([
        _traj_synthetic(kind="time_opt"),
        _traj_synthetic(kind="energy_opt").assign(rank=lambda d: d["rank"]),
        _traj_synthetic(kind="compromise"),
    ], ignore_index=True)
    paths = prof.run_and_save(traj, output_dir=tmp_path)
    assert "profiles" in paths
    assert paths["profiles"].exists()
    assert paths["profiles_time_opt"].exists()
    assert paths["profiles_energy_opt"].exists()
    assert paths["profiles_compromise"].exists()
    # Relecture du combiné
    combined = pd.read_csv(paths["profiles"])
    assert set(combined["kind"]) == {"time_opt", "energy_opt", "compromise"}
    assert list(combined.columns) == [
        "kind", "segment_id", "t", "x", "y", "z", "vx", "vy", "vz",
    ]


# ----------------------------------------------------------------------
# T11 — Erreurs d'entrée
# ----------------------------------------------------------------------
def test_invalid_dt_raises(cfg: Config) -> None:
    with pytest.raises(ValueError, match="dt"):
        TrajectoryProfiler(cfg, dt=0.0)


def test_invalid_min_samples_raises(cfg: Config) -> None:
    with pytest.raises(ValueError, match="min_samples"):
        TrajectoryProfiler(cfg, min_samples_per_segment=1)


def test_missing_rank_raises(profiler: TrajectoryProfiler) -> None:
    bad = pd.DataFrame({"kind": ["x"], "x": [0.0], "y": [0.0], "z": [0.45]})
    with pytest.raises(ValueError, match="rank"):
        profiler.profile_trajectory("x", bad)
