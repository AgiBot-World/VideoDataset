from __future__ import annotations

import logging
import urllib.error
import urllib.request
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings
from typing_extensions import Self

logger = logging.getLogger(__name__)


class TestDatasetSettings(BaseSettings):
    """Settings class for datasets used in setting"""

    use_local_path: bool = True
    use_repo_id: bool = True
    # TODO: adjust path and repo id in public ci runner environment
    # Used for fetching from hugggingface hub
    lerobot_datasets_repo_ids: dict[str, str] = {
        "ucsd_kitchen_dataset": "lerobot/ucsd_kitchen_dataset"
    }

    # Used for loading from a file path
    lerobot_datasets_root_paths: dict[str, Path] = {
        "ucsd_kitchen_dataset": Path(
            "/mnt/public/huxingyu/lerobot/ucsd_kitchen_dataset"
        ),
        "aidea_world": Path(
            "/mnt/public/qiuying/aidea-world-h265-4/alpha/agibotworld/task_327"
        ),
        "0730_h265_toy": Path("/mnt/public/qiuying/LEROBOT/H265/0730_toy_h265"),
    }

    lerobot_datasets_input_dim: dict[str, int] = {
        "ucsd_kitchen_dataset": 921621,
        "aidea_world": 1572919,
        "0730_h265_toy": 589838,
    }

    lerobot_datasets_action_dim: dict[str, int] = {
        "ucsd_kitchen_dataset": 8,
        "0730_h265_toy": 14,
        "aidea_world": 14,
    }

    @model_validator(mode="after")
    def validate_path_or_repo(self) -> Self:
        # Perform sanity check on file path
        for dataset_name, path in (self.lerobot_datasets_root_paths).items():
            if not (path.exists() and path.is_dir()):
                msg = f"Validation failed for dataset: {dataset_name} and path: {path}"
                logger.warning(msg)
                self.use_local_path = False
                break

        try:
            # If local path does not work, fallback to fetching from huggingface
            if not self.use_local_path:
                for _, repo_id in (self.lerobot_datasets_repo_ids).items():
                    self.ping_huggingface_repo(repo_id)
                # If check failed for both local and remote paths, tests will not proceed
        except urllib.error.URLError:
            self.use_repo_id = False
            msg = "Validation failed for remote repo. Tests will be skipped."
            logger.warning(msg)

        return self

    def ping_huggingface_repo(self, repo_id: str, timeout: int = 5):
        url = f"https://huggingface.co/api/datasets/{repo_id}"
        request = urllib.request.Request(url)
        with urllib.request.urlopen(request, timeout=timeout) as response:
            logger.debug(response)


class TestTrainingSettings(BaseSettings):
    """Settings class for model settings"""

    batch_size: int = 16
    num_workers: int = 1
    train_iteration_limit: int = 20

    model_config = {
        "env_file": ".env.test",
        "env_prefix": "TEST_",
        "case_sensitive": False,
    }


dataset_settings = TestDatasetSettings()
training_settings = TestTrainingSettings()
