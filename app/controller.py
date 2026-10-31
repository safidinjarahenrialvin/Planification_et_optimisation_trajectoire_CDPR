"""Contrôleur applicatif entre Streamlit et les services scientifiques."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from threading import Event, Lock, Thread
from typing import Callable
from uuid import uuid4

from services.configuration_service import ConfigurationService
from services.pipeline_service import (
    PipelineCancelled,
    PipelineOptions,
    PipelineRequest,
    PipelineResult,
    PipelineService,
)
from src.config import Config


@dataclass(frozen=True)
class GuiRunParameters:
    """Valeurs saisies dans le formulaire GUI.

    Le contrat reprend les options de configuration du CLI. Les paramètres
    ``None`` signifient « laisser Config.with_n appliquer sa règle par défaut ».
    """

    n: int
    platform: str
    zero_loss: bool
    K: int
    pop_size: int
    n_gen: int
    seed: int
    z_absolu_r0_override: float | None = None
    platform_mass_kg: float | None = None
    xy_bound: float | None = None
    x_bound: float | None = None
    y_bound: float | None = None


class RunStatus(str, Enum):
    """États observables d'un worker GUI."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class RunSnapshot:
    """Instantané cohérent d'un run, lisible par Streamlit."""

    status: RunStatus
    progress: float
    step: str | None
    step_status: str | None
    run_id: str | None
    result: PipelineResult | None
    error: str | None


class RunHandle:
    """Contrat thread-safe entre Streamlit et un pipeline en arrière-plan."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._cancellation_event = Event()
        self._status = RunStatus.PENDING
        self._progress = 0.0
        self._step: str | None = None
        self._step_status: str | None = None
        self._run_id: str | None = None
        self._result: PipelineResult | None = None
        self._error: str | None = None
        self._thread: Thread | None = None

    def start(self, parameters: GuiRunParameters, root: Path) -> None:
        """Démarre exactement un worker pour ce handle."""
        with self._lock:
            if self._thread is not None:
                raise RuntimeError("Ce handle de run a déjà été démarré.")
            self._status = RunStatus.RUNNING
            self._thread = Thread(
                target=self._worker,
                args=(parameters, Path(root)),
                name="tandem-pipeline-worker",
                daemon=True,
            )
            self._thread.start()

    def cancel(self) -> bool:
        """Demande une annulation coopérative ; retourne si le run était actif."""
        with self._lock:
            if self._status not in {RunStatus.PENDING, RunStatus.RUNNING}:
                return False
            self._cancellation_event.set()
            return True

    def snapshot(self) -> RunSnapshot:
        """Retourne un instantané sans exposer l'état mutable interne."""
        with self._lock:
            return RunSnapshot(
                status=self._status,
                progress=self._progress,
                step=self._step,
                step_status=self._step_status,
                run_id=self._run_id,
                result=self._result,
                error=self._error,
            )

    def is_active(self) -> bool:
        """Indique si le worker peut encore modifier l'état du run."""
        with self._lock:
            return self._status in {RunStatus.PENDING, RunStatus.RUNNING}

    def wait(self, timeout: float | None = None) -> bool:
        """Attend la fin du worker et indique s'il est effectivement terminé."""
        with self._lock:
            thread = self._thread
        if thread is None:
            return not self.is_active()
        thread.join(timeout=timeout)
        return not thread.is_alive()

    def _update_progress(self, step: str, status: str, fraction: float) -> None:
        with self._lock:
            self._step = step
            self._step_status = status
            self._progress = max(0.0, min(1.0, fraction))

    def _worker(self, parameters: GuiRunParameters, root: Path) -> None:
        try:
            run_id, result = run_from_gui(
                parameters,
                root=root,
                progress_callback=self._update_progress,
                cancellation_event=self._cancellation_event,
            )
        except PipelineCancelled as exc:
            with self._lock:
                self._status = RunStatus.CANCELLED
                self._error = str(exc)
                self._step_status = "cancelled"
        except Exception as exc:  # GUI boundary: report through the snapshot.
            with self._lock:
                self._status = RunStatus.FAILED
                self._error = str(exc)
                self._step_status = "failed"
        else:
            with self._lock:
                self._run_id = run_id
                self._result = result
                self._progress = 1.0
                self._status = RunStatus.COMPLETED
                self._step_status = "done"


def build_config(parameters: GuiRunParameters) -> Config:
    """Construit une Config : les règles métier restent dans ``Config``."""
    return Config.with_n(
        parameters.n,
        platform=parameters.platform,
        zero_loss=parameters.zero_loss,
        platform_mass=parameters.platform_mass_kg,
        xy_bound=parameters.xy_bound,
        x_bound=parameters.x_bound,
        y_bound=parameters.y_bound,
        z_absolu_r0_override=parameters.z_absolu_r0_override,
    )


def create_run_directory(root: Path = Path("data/runs")) -> tuple[str, Path]:
    """Crée un identifiant et un répertoire dédiés à une seule exécution."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"run_{timestamp}_{uuid4().hex[:8]}"
    output_dir = root / run_id
    output_dir.mkdir(parents=True, exist_ok=False)
    return run_id, output_dir


def run_from_gui(
    parameters: GuiRunParameters,
    *,
    root: Path = Path("data/runs"),
    progress_callback: Callable[[str, str, float], None] | None = None,
    cancellation_event: Event | None = None,
) -> tuple[str, PipelineResult]:
    """Valide puis lance explicitement une exécution isolée."""
    config = build_config(parameters)
    effective = ConfigurationService.validate(
        config,
        K=parameters.K,
        pop_size=parameters.pop_size,
        n_gen=parameters.n_gen,
        seed=parameters.seed,
    )
    run_id, output_dir = create_run_directory(root)
    request = PipelineRequest(
        config=effective.config,
        output_dir=output_dir,
        options=PipelineOptions(
            K=effective.K,
            pop_size=effective.pop_size,
            n_gen=effective.n_gen,
            seed=effective.seed,
        ),
        progress_callback=progress_callback,
        cancellation_event=cancellation_event,
    )
    return run_id, PipelineService().run(request)
