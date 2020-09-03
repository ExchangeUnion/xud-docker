import pytest
from subprocess import check_output
import json
import os


@pytest.fixture(scope="module", autouse=True)
def build_utils():
    os.system("tools/build utils")
    wd = os.getcwd()
    os.chdir("tests")
    yield
    os.chdir(wd)


def test_simnet_services():
    cmd = "NETWORK=simnet bash run_utils_test.sh dump_config_nodes --xud.options='--foo bar'"
    output = check_output(cmd, shell=True)
    j = json.loads(output)
    assert set(j) == {"xud", "lndbtc", "lndltc", "connext", "arby", "webui"}


def test_testnet_services():
    cmd = "NETWORK=testnet bash run_utils_test.sh dump_config_nodes --xud.options='--foo bar'"
    output = check_output(cmd, shell=True)
    j = json.loads(output)
    assert set(j) == {"xud", "lndbtc", "lndltc", "connext", "bitcoind", "litecoind", "geth", "arby", "boltz", "webui"}


def test_mainnet_services():
    cmd = "NETWORK=mainnet bash run_utils_test.sh dump_config_nodes --xud.options='--foo bar'"
    output = check_output(cmd, shell=True)
    j = json.loads(output)
    assert set(j) == {"xud", "lndbtc", "lndltc", "connext", "bitcoind", "litecoind", "geth", "arby", "boltz", "webui"}


def test_xud_options():
    cmd = "NETWORK=simnet bash run_utils_test.sh dump_config_nodes --xud.options='--foo bar'"
    output = check_output(cmd, shell=True)
    j = json.loads(output)
    assert j["xud"]["options"] == "--foo bar"

