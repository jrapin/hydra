# Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved
import subprocess

# noinspection PyUnresolvedReferences
import sys
from pathlib import Path
from typing import Any

import nevergrad as ng  # type: ignore
import pytest
from omegaconf import OmegaConf

from hydra.core.plugins import Plugins
from hydra.plugins.sweeper import Sweeper
from hydra.test_utils.test_utils import (  # noqa: F401
    TSweepRunner,
    chdir_plugin_root,
    sweep_runner,
)
from hydra_plugins.hydra_nevergrad_sweeper import NevergradSweeper
from hydra_plugins.hydra_nevergrad_sweeper.core import make_parameter

chdir_plugin_root()


def test_discovery() -> None:
    assert NevergradSweeper.__name__ in [x.__name__ for x in Plugins.discover(Sweeper)]


@pytest.mark.parametrize(  # type: ignore
    "string,param_cls,value_cls",
    [
        ("blu,blublu", ng.p.Choice, str),
        ("0,1,2", ng.p.TransitionChoice, int),
        ("0.0,12.0,2.0", ng.p.Choice, float),
        ("1:12", ng.p.Scalar, int),
        ("1.0:12", ng.p.Scalar, float),
        ("blublu", str, str),
        (
            "Scalar(init=12.1).set_mutation(sigma=3).set_integer_casting()",
            ng.p.Scalar,
            int,
        ),
    ],
)
def test_make_parameter(string: str, param_cls: Any, value_cls: Any) -> None:
    param = make_parameter(string)
    assert isinstance(param, param_cls)
    if param_cls is not str:
        assert isinstance(param.value, value_cls)


# pylint: disable=redefined-outer-name
def test_launched_jobs(sweep_runner: TSweepRunner) -> None:  # noqa: F811 # type: ignore
    budget = 8
    sweep = sweep_runner(
        calling_file=None,
        calling_module="hydra.test_utils.a_module",
        config_path="configs",
        config_name="compose.yaml",
        task_function=None,
        overrides=[
            "hydra/sweeper=nevergrad",
            "hydra/launcher=basic",
            f"hydra.sweeper.params.budget={budget}",  # small budget to test fast
            "hydra.sweeper.params.num_workers=3",
            "foo=1,2",
            "bar=4.0:8.0",
        ],
        strict=True,
    )
    with sweep:
        assert sweep.returns is None


def test_nevergrad_example(tmpdir: Path) -> None:
    budget = 32
    cmd = [
        sys.executable,
        "example/dummy_training.py",
        "-m",
        "hydra.sweep.dir=" + str(tmpdir),
        f"hydra.sweeper.params.budget={budget}",  # small budget to test fast
        "hydra.sweeper.params.num_workers=8",
        "hydra.sweeper.params.seed=12",  # avoid random failures
        "db=mnist,cifar",
        "batch_size=4,8,12,16",
        "lr=Log(a_min=0.001,a_max=1.0)",
        "dropout=0.0:1.0",
    ]
    subprocess.check_call(cmd)
    returns = OmegaConf.load(f"{tmpdir}/optimization_results.yaml")
    assert returns.optimizer == "nevergrad"
    assert len(returns) == 2
    best_parameters = returns.nevergrad
    assert best_parameters.batch_size == 4  # this argument should be easy to find