from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Iterable

from ert.config import ParameterConfig, ResponseConfig, SummaryConfig
from ert.run_arg import RunArg

from .load_status import LoadResult, LoadStatus
from .storage.realization_storage_state import RealizationStorageState

logger = logging.getLogger(__name__)


def _read_parameters(
    run_arg: RunArg, parameter_configuration: Iterable[ParameterConfig]
) -> LoadResult:
    result = LoadResult(LoadStatus.LOAD_SUCCESSFUL, "")
    error_msg = ""
    for config in parameter_configuration:
        if not config.forward_init:
            continue
        try:
            start_time = time.perf_counter()
            logger.info(f"Starting to load parameter: {config.name}")
            ds = config.read_from_runpath(Path(run_arg.runpath), run_arg.iens)
            logger.info(
                f"Loaded {config.name}",
                extra={"Time": f"{(time.perf_counter() - start_time):.4f}s"},
            )
            start_time = time.perf_counter()
            run_arg.ensemble_storage.save_parameters(config.name, run_arg.iens, ds)
            logger.info(
                f"Saved {config.name} to storage",
                extra={"Time": f"{(time.perf_counter() - start_time):.4f}s"},
            )
        except ValueError as err:
            error_msg += str(err)
            result = LoadResult(LoadStatus.LOAD_FAILURE, error_msg)
    return result


def _write_responses_to_storage(
    run_arg: RunArg, response_configs: Iterable[ResponseConfig]
) -> LoadResult:
    errors = []
    for config in response_configs:
        if isinstance(config, SummaryConfig) and not config.keys:
            # Nothing to load, should not be handled here, should never be
            # added in the first place
            continue
        try:
            start_time = time.perf_counter()
            logger.info(f"Starting to load response: {config.name}")
            ds = config.read_from_file(run_arg.runpath, run_arg.iens)
            logger.info(
                f"Loaded {config.name}",
                extra={"Time": f"{(time.perf_counter() - start_time):.4f}s"},
            )
            start_time = time.perf_counter()
            run_arg.ensemble_storage.save_response(config.name, ds, run_arg.iens)
            logger.info(
                f"Saved {config.name} to storage",
                extra={"Time": f"{(time.perf_counter() - start_time):.4f}s"},
            )
        except ValueError as err:
            errors.append(str(err))
    if errors:
        return LoadResult(LoadStatus.LOAD_FAILURE, "\n".join(errors))
    return LoadResult(LoadStatus.LOAD_SUCCESSFUL, "")


def forward_model_ok(
    run_arg: RunArg,
) -> LoadResult:
    parameters_result = LoadResult(LoadStatus.LOAD_SUCCESSFUL, "")
    response_result = LoadResult(LoadStatus.LOAD_SUCCESSFUL, "")
    try:
        # We only read parameters after the prior, after that, ERT
        # handles parameters
        if run_arg.itr == 0:
            parameters_result = _read_parameters(
                run_arg,
                run_arg.ensemble_storage.experiment.parameter_configuration.values(),
            )

        if parameters_result.status == LoadStatus.LOAD_SUCCESSFUL:
            response_result = _write_responses_to_storage(
                run_arg,
                run_arg.ensemble_storage.experiment.response_configuration.values(),
            )

    except Exception as err:
        logging.exception(f"Failed to load results for realization {run_arg.iens}")
        parameters_result = LoadResult(
            LoadStatus.LOAD_FAILURE,
            "Failed to load results for realization "
            f"{run_arg.iens}, failed with: {err}",
        )

    final_result = parameters_result
    if response_result.status != LoadStatus.LOAD_SUCCESSFUL:
        final_result = response_result

    run_arg.ensemble_storage.state_map[run_arg.iens] = (
        RealizationStorageState.HAS_DATA
        if final_result.status == LoadStatus.LOAD_SUCCESSFUL
        else RealizationStorageState.LOAD_FAILURE
    )

    return final_result
