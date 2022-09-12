import os

import pytest
from hypothesis import given

from ert._c_wrappers.enkf import ConfigKeys, SiteConfig

from .config_dict_generator import config_dicts, to_config_file


def touch(filename):
    with open(filename, "w") as fh:
        fh.write(" ")


@pytest.mark.skip(reason="https://github.com/equinor/ert/issues/3801")
@pytest.mark.usefixtures("use_tmpdir")
@given(config_dicts())
def test_site_config_dict_same_as_from_file(config_dict):
    cwd = os.getcwd()
    filename = config_dict[ConfigKeys.CONFIG_FILE_KEY]
    to_config_file(filename, config_dict)
    config_dict[ConfigKeys.CONFIG_DIRECTORY] = cwd
    assert SiteConfig(filename) == SiteConfig(config_dict=config_dict)


@pytest.mark.xfail(reason="https://github.com/equinor/ert/issues/2553")
def test_site_config_defaults_umask(tmpdir):
    touch(tmpdir + "/rpfile")
    touch(tmpdir + "/datafile")
    os.mkdir(tmpdir + "/license")
    SiteConfig(
        config_dict={
            "CONFIG_DIRECTORY": str(tmpdir),
            "DATA_FILE": "datafile",
            "LICENSE_PATH": "license",
            "RES_CONFIG_FILE": "test.ert",
            "RUNPATH_FILE": "rpfile",
        }
    )
