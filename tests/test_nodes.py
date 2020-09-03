import pytest
from subprocess import check_output
import json
import os


@pytest.fixture(scope="session", autouse=True)
def build_utils():
    os.system("tools/build utils")
    wd = os.getcwd()
    os.chdir("tests")
    yield
    os.chdir(wd)


def test_xud_options():
    cmd = "NETWORK=simnet bash run_utils_test.sh dump_node_container_spec --xud.options='--foo bar'"
    output = check_output(cmd, shell=True)
    j = json.loads(output)
    print(j)
    assert "XUD_OPTS=--foo bar" in j["environment"]
