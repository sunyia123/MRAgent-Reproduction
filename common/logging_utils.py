# logging_utils.py
import os
import json
import logging
import datetime
from contextlib import contextmanager
from pathlib import Path

from common import config  # local config


RUN_ID = os.getenv("RUN_ID") or datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def safe_config_dict(config_module=config):
    """Return non-secret runtime config for logs and manifests."""
    payload = {}
    for name in dir(config_module):
        if not name.isupper():
            continue
        if any(kw in name.lower() for kw in ["key", "secret", "password", "token"]):
            payload[name] = "[HIDDEN]"
            continue
        value = getattr(config_module, name)
        try:
            json.dumps(value)
            payload[name] = value
        except TypeError:
            payload[name] = str(value)
    return payload


def run_log_path(dataset=None, base_dir="log"):
    dataset = dataset or config.DATASET
    log_dir = Path(base_dir) / dataset / "runs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / f"{RUN_ID}{config.ADDITIONAL_RE}.log"


def add_run_file_handler(dataset=None, base_dir="log"):
    """Attach a per-run log file and keep it active for the whole process."""
    logger = logging.getLogger()
    path = run_log_path(dataset=dataset, base_dir=base_dir)
    existing = str(path)
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler) and getattr(handler, "baseFilename", None) == os.path.abspath(existing):
            return handler, path
    fh = logging.FileHandler(path, mode="a", encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    logger.addHandler(fh)
    logger.info("==== RUN LOG START run_id=%s path=%s ====", RUN_ID, path)
    logger.info("argv_config=%s", json.dumps(safe_config_dict(), ensure_ascii=False, sort_keys=True))
    return fh, path

@contextmanager
def per_sample_log(sample_id, dataset, base_dir="log"):
    """Write to log/<dataset>/<sample_id>.log only within the with-block."""
    os.makedirs(f"{base_dir}/{dataset}", exist_ok=True)
    logger = logging.getLogger()

    log_path = f"{base_dir}/{dataset}/{sample_id}{config.ADDITIONAL_RE}_{RUN_ID}.log"
    fh = logging.FileHandler(log_path, mode='a', encoding="utf-8", delay=True)  # append
    fh.setLevel(logging.INFO)
    fh.setFormatter(logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))

    logger.addHandler(fh)
    try:
        logger.info("---- SAMPLE RUN START run_id=%s sample=%s path=%s ----", RUN_ID, sample_id, log_path)
        yield
    finally:
        logger.info("---- SAMPLE RUN END run_id=%s sample=%s ----", RUN_ID, sample_id)
        logger.removeHandler(fh)
        fh.close()
