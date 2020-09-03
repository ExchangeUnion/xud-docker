import pytest
from subprocess import check_output
import json
import os


@pytest.fixture(scope="module", autouse=True)
def build_utils():
    wd = os.getcwd()
    os.chdir("tests")
    yield
    os.chdir(wd)


def test_xud_entrypoint():
    cmd = "bash run_image_script.sh"
    output = check_output(cmd, shell=True)
    j = json.loads(output)
    print(j)
    assert "XUD_OPTS=--foo bar" in j["environment"]
