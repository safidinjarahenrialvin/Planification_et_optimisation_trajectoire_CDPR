"""Génération d’un support de présentation à partir d’un run chargé."""
from __future__ import annotations

from services.result_service import RunResults
from visualization.labels import kind_label


def build_jury_script(run_id: str, results: RunResults) -> str:
    """Construit un script oral factuel, sans inventer de métriques."""
    points = results.point_statistics()
    trajectories = results.trajectory_statistics()
    diagnostic = results.comparison_diagnostic
    validation = results.validation
    gain_stats = results.gain_statistics()
    filter_summary = results.point_filter_report.get("summary", {})
    alerts = results.points_generated_report.get("alerts", [])
    status = results.validation_status
    coverage_rate = (
        points["count"] / len(results.points_generated)
        if len(results.points_generated)
        else 0.0
    )
    warning_sentence = (
        "Le statut WARN provient d’un front Pareto court ; aucun contrôle FAIL "
        "n’a été détecté."
        if status == "WARN"
        else f"Le statut des contrôles automatiques est {status}."
    )
    lines = [
        "# Script oral — présentation Tandem SP2",
        "",
        f"## 1. Introduction — run `{run_id}`",
        "",
        "Notre plateforme planifie les trajectoires d’un robot à câbles en "
        "évaluant simultanément le temps de mouvement et l’énergie consommée. "
        "Les gains temporels utilisent le temps de mouvement, tandis que le temps total "
        "ajoute la stabilisation aux waypoints. "
        "Cette démonstration repose sur les artefacts réels du run affiché.",
        "",
        "## 2. Couverture de la grille étudiée",
        "",
        f"La grille contient {len(results.points_generated)} points générés, dont "
        f"{points['count']} retenus après filtrage, soit "
        f"{coverage_rate:.1%} de couverture. "
        f"Le taux de rejet déclaré est {filter_summary.get('reject_rate', 0):.1%}.",
        "",
        "## 3. Résultat de l’optimisation",
        "",
        f"Nous comparons {trajectories['count']} stratégies. La meilleure stratégie "
        f"en temps de mouvement est **{kind_label(trajectories['best_time_motion_kind'])}** ; "
        f"en temps total, c’est **{kind_label(trajectories['best_time_total_kind'])}**, "
        f"tandis que la meilleure en énergie est "
        f"**{kind_label(trajectories['best_energy_kind'])}**.",
        f"Le gain minimal de temps de mouvement mesuré est de "
        f"{diagnostic.get('min_time_gain_pct', 0):.2f} % et le gain minimal "
        f"d’énergie de {diagnostic.get('min_energy_gain_pct', 0):.2f} %.",
        f"Ces minima sont déterminés respectivement par "
        f"{kind_label(gain_stats['min_time_gain_kind'])} et "
        f"{kind_label(gain_stats['min_energy_gain_kind'])}; ils représentent "
        "le gain le moins favorable parmi les stratégies comparées.",
        f"Les maxima sont de {gain_stats['max_time_gain_pct']:.2f} % en temps de mouvement "
        f"({kind_label(gain_stats['max_time_gain_kind'])}) et "
        f"{gain_stats['max_energy_gain_pct']:.2f} % en énergie "
        f"({kind_label(gain_stats['max_energy_gain_kind'])}). "
        f"Les gains portent sur {gain_stats['strategy_count']} stratégies optimisées, "
        f"comparées à {kind_label(gain_stats['baseline_kind'])}.",
        "",
        "## 4. Contrôles automatiques et limites",
        "",
        f"Le statut des contrôles automatiques est `{status}`. "
        f"Les contrôles indiquent "
        f"{validation.get('summary', {}).get('n_pass', 0)} PASS, "
        f"{validation.get('summary', {}).get('n_warn', 0)} WARN et "
        f"{validation.get('summary', {}).get('n_fail', 0)} FAIL. "
        f"{warning_sentence} Ces résultats ne constituent pas à eux seuls une "
        "validation scientifique humaine ou expérimentale.",
    ]
    if alerts:
        lines.extend([
            "",
            "Point de vigilance à annoncer : " + " ".join(alerts),
        ])
    lines.extend([
        "",
        "## 5. Conclusion",
        "",
        "La décision ne repose pas sur une seule métrique : le front de Pareto "
        "permet de discuter explicitement le compromis temps-énergie. Les figures "
        "et tableaux présentés sont reconstruits depuis les CSV et JSON du run, "
        "et l’animation 3D reste une illustration pédagogique.",
    ])
    return "\n".join(lines)
