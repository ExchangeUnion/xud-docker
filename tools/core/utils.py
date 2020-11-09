from subprocess import check_output, STDOUT
from urllib.request import urlopen
import json
from typing import Optional


def execute(cmd: str) -> str:
    output = check_output(cmd, shell=True, stderr=STDOUT)
    return output.decode()


def get_github_job_url(run_id: str, job_name: str) -> Optional[str]:
    url = "https://api.github.com/repos/ExchangeUnion/xud-docker/actions/runs/{}/jobs".format(run_id)
    resp = urlopen(url)
    j = json.load(resp)
    for job in j["jobs"]:
        if job["name"] == job_name:
            return "https://github.com/ExchangeUnion/xud-docker/runs/{}?check_suite_focus=true".format(job["id"])
    return None
