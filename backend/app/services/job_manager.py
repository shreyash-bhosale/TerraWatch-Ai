import json
import logging
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import settings
from app.processing.validation import validate_compatibility
from app.providers.base import BaseProvider
from app.providers.registry import get_provider
from app.schemas.analysis import (
    JobError,
    JobResultsResponse,
    JobStatusResponse,
    LayerUrls,
    Stats,
)
from app.schemas.common import GeoJSONPolygonGeometry
from app.services.validator import validate_aoi_geometry

logger = logging.getLogger(__name__)


class JobNotFoundError(Exception):
    pass


class JobNotCompletedError(Exception):
    pass


class ResultNotFoundError(Exception):
    pass


class JobManager:
    """In-process Job Manager running background raster difference pipelines.
    
    Persists job state atomically to data/jobs/<job_id>.json.
    Stages: queued -> validating -> reading -> aligning -> differencing -> statistics -> exporting -> completed / failed.
    """

    def __init__(self, max_workers: int = 2):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix="sar_worker")
        self.jobs_dir = settings.jobs_data_path
        self.outputs_dir = settings.outputs_data_path

    def _ensure_dirs(self) -> None:
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)

    def _atomic_write_job(self, job_dict: dict[str, Any]) -> None:
        self._ensure_dirs()
        job_id = job_dict["job_id"]
        target = self.jobs_dir / f"{job_id}.json"
        temp = self.jobs_dir / f".{job_id}.json.tmp"
        with open(temp, "w", encoding="utf-8") as f:
            json.dump(job_dict, f, indent=2)
        os.replace(temp, target)

    def get_job(self, job_id: str) -> dict[str, Any]:
        target = self.jobs_dir / f"{job_id}.json"
        if not target.is_file():
            raise JobNotFoundError(f"Job '{job_id}' not found")
        try:
            return json.loads(target.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise RuntimeError(f"Failed to read job state for '{job_id}': {e}")

    def update_job(
        self,
        job_id: str,
        stage: str | None = None,
        status: str | None = None,
        error: dict[str, str] | None = None,
        started_at: str | None = None,
        finished_at: str | None = None,
    ) -> dict[str, Any]:
        job_data = self.get_job(job_id)
        if stage is not None:
            job_data["stage"] = stage
        if status is not None:
            job_data["status"] = status
        if error is not None:
            job_data["error"] = error
        if started_at is not None:
            job_data["started_at"] = started_at
        if finished_at is not None:
            job_data["finished_at"] = finished_at

        self._atomic_write_job(job_data)
        return job_data

    def create_job(
        self,
        before_id: str,
        after_id: str,
        aoi: GeoJSONPolygonGeometry,
        provider: BaseProvider | None = None,
    ) -> str:
        self._ensure_dirs()
        if provider is None:
            provider = get_provider()

        # Validate AOI
        validate_aoi_geometry(aoi)

        # Validate Observation Existence
        try:
            obs_before = provider.get(before_id)
        except KeyError:
            raise KeyError(f"Observation '{before_id}' not found")

        try:
            obs_after = provider.get(after_id)
        except KeyError:
            raise KeyError(f"Observation '{after_id}' not found")

        # Validate Compatibility
        val_res = validate_compatibility(
            obs_before, obs_after, aoi, provider=provider
        )
        if not val_res.compatible:
            failed_rules = [r.message for r in val_res.rules if not r.passed and r.severity == "error"]
            raise ValueError(f"Incompatible observations: {'; '.join(failed_rules)}")

        job_id = f"job_{uuid.uuid4().hex[:12]}"
        is_synthetic = bool(obs_before.synthetic or obs_after.synthetic)
        result_dir = str((self.outputs_dir / job_id).resolve())

        now_iso = datetime.now(UTC).isoformat()
        job_record = {
            "job_id": job_id,
            "status": "queued",
            "stage": "queued",
            "created_at": now_iso,
            "started_at": None,
            "finished_at": None,
            "before_id": val_res.order.before_id,
            "after_id": val_res.order.after_id,
            "aoi": aoi.model_dump(),
            "synthetic": is_synthetic,
            "error": None,
            "result_dir": result_dir,
        }

        self._atomic_write_job(job_record)
        self.executor.submit(self._run_job_worker, job_id, provider)
        return job_id

    def _run_job_worker(self, job_id: str, provider: BaseProvider) -> None:
        try:
            job_data = self.get_job(job_id)
            now_iso = datetime.now(UTC).isoformat()
            self.update_job(job_id, stage="validating", status="running", started_at=now_iso)

            # Resolve observation assets
            before_path = provider.open_asset(job_data["before_id"])
            after_path = provider.open_asset(job_data["after_id"])
            output_dir = Path(job_data["result_dir"])

            # Import pipeline
            from app.processing.pipeline import run_pipeline

            def on_stage_change(current_stage: str) -> None:
                if current_stage in ("completed", "failed"):
                    return
                self.update_job(job_id, stage=current_stage, status="running")

            # Execute processing stages
            run_pipeline(
                before_path=before_path,
                after_path=after_path,
                aoi_geojson=job_data["aoi"],
                output_dir=output_dir,
                stage_callback=on_stage_change,
            )

            # Success transition
            finished_iso = datetime.now(UTC).isoformat()
            self.update_job(
                job_id,
                stage="completed",
                status="completed",
                finished_at=finished_iso,
            )

        except Exception as e:
            logger.exception("Analysis job %s failed", job_id)
            finished_iso = datetime.now(UTC).isoformat()
            code = getattr(e, "code", "INTERNAL_ERROR")
            if "not found" in str(e).lower():
                code = "OBSERVATION_NOT_FOUND"
            elif "align" in str(e).lower():
                code = "ALIGNMENT_MISMATCH"

            error_payload = {
                "code": code,
                "message": str(e),
            }
            self.update_job(
                job_id,
                stage="failed",
                status="failed",
                error=error_payload,
                finished_at=finished_iso,
            )

    def get_status_response(self, job_id: str) -> JobStatusResponse:
        job = self.get_job(job_id)
        error_model = JobError(**job["error"]) if job.get("error") else None
        return JobStatusResponse(
            job_id=job["job_id"],
            status=job["status"],
            stage=job["stage"],
            created_at=job["created_at"],
            started_at=job.get("started_at"),
            finished_at=job.get("finished_at"),
            before_id=job["before_id"],
            after_id=job["after_id"],
            synthetic=job["synthetic"],
            error=error_model,
        )

    def get_results_response(self, job_id: str) -> JobResultsResponse:
        job = self.get_job(job_id)
        if job["status"] != "completed":
            raise JobNotCompletedError(
                f"Job '{job_id}' is in status '{job['status']}' (stage: '{job.get('stage')}'). Results are only available when status is 'completed'."
            )

        result_dir = Path(job["result_dir"])
        stats_file = result_dir / "statistics.json"
        meta_file = result_dir / "metadata.json"

        if not stats_file.is_file() or not meta_file.is_file():
            raise ResultNotFoundError(f"Result files for job '{job_id}' not found on disk")

        stats_data = json.loads(stats_file.read_text(encoding="utf-8"))
        meta_data = json.loads(meta_file.read_text(encoding="utf-8"))

        bounds = meta_data.get("bounds", [-180.0, -90.0, 180.0, 90.0])
        limitations = meta_data.get("limitations", [
            "Difference of calibrated SAR backscatter (dB) between two dates; it is not a classified event map.",
            "Changes may come from surface change, soil moisture, vegetation, wind, incidence angle, speckle, or processing differences.",
            "No threshold or classification has been applied.",
        ])
        if job["synthetic"] and not any("DEMO DATA" in item for item in limitations):
            limitations.append("DEMO DATA — SYNTHETIC, NOT REAL NISAR OBSERVATIONS. No real-world conclusion can be drawn.")

        return JobResultsResponse(
            statistics=Stats(
                valid_pixel_count=stats_data["valid_pixel_count"],
                invalid_pixel_count=stats_data["invalid_pixel_count"],
                total_pixel_count=stats_data["total_pixel_count"],
                mean=stats_data["mean"],
                median=stats_data["median"],
                min=stats_data["min"],
                max=stats_data["max"],
                std=stats_data["std"],
            ),
            bounds=bounds,
            layers=LayerUrls(
                difference_png=f"/files/outputs/{job_id}/difference.png",
                before_png=f"/files/outputs/{job_id}/before.png",
                after_png=f"/files/outputs/{job_id}/after.png",
            ),
            geotiff_url=f"/files/outputs/{job_id}/difference.tif",
            metadata=meta_data,
            limitations=limitations,
            synthetic=job["synthetic"],
        )


job_manager = JobManager()
