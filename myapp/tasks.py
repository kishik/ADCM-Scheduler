from celery import shared_task
from celery_progress.backend import ProgressRecorder
import time
import logging
from myapp.models import WorkVolume, URN, Job

logger = logging.getLogger(__name__)


def sync_project(project: Project):
    logger.info(f"Syncing project {project.name}")
    latest_job = project.jobs.filter(task_type="LOAD").order_by("-created_at").filter(task_id__isnull=False).first()
    models = project.bim_models.filter(deleted_at__isnull=True)
    if latest_job:
        logger.info(f"Loading models updated after {latest_job.created_at}")
        models = models.filter(updated_at__gt=latest_job.created_at)

    job = project.jobs.create(task_type="LOAD")
    logger.info(f"Created job {job.id}")

    pending = []
    for model in models:
        if model.model_type == "REVIT":
            for rule in model.model_group.extractor_rules.filter(deleted_at__isnull=True):
                pending.append(load_revit_model.si(job.id, model.id, rule.id))
        elif model.model_type == "IFC":
            pending.append(load_ifc_model.si(job.id, model.id))
    if pending:
        result = group(pending).apply_async()
        job.task_id = result.id
        job.save()
    else:
        logger.info("No models to load")
    return job


@shared_task
def load_ifc_model(job_id, model_id):
    print(f"Loading IFC {job_id} / {model_id}")
    model = BimModel.objects.get(id=model_id)
    job = Job.objects.get(id=job_id)
    if model.model_type != "IFC":
        raise ValueError("Model is not an IFC model")
    return list(load_ifc(model, job))


@shared_task
def load_revit_model(job_id, model_id, rule_id):
    print(f"Loading Revit {job_id} / {model_id} / {rule_id}")
    model = BimModel.objects.get(id=model_id)
    job = Job.objects.get(id=job_id)
    rule = model.model_group.extractor_rules.get(id=rule_id)
    return list(load_revit(model, job, rule))
