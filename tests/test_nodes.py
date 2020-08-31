from subprocess import check_output
import json


def test_xud_options():
    cmd = "NETWORK=simnet bash run_utils_test.sh dump_node_container_spec --xud.options='--foo bar'"
    output = check_output(cmd, shell=True)
    j = json.loads(output)
    print(j)
