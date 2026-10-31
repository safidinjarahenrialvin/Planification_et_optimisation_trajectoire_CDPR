# tests/test_robot_3d_viewer.py (nouveau fichier)
"""
Test de fumée pour Robot3DViewer — vérifie que build_figure s'exécute
sans NameError (détecte les lignes manquantes ou blocs dupliqués).
"""
from src.config import Config
from src.robot_3d_viewer import Robot3DViewer


def test_build_figure_smoke() -> None:
    config = Config.with_n(9)
    viewer = Robot3DViewer(config)
    fig = viewer.build_figure()
    assert fig is not None
    assert len(fig.data) > 0
