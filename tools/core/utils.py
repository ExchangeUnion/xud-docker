from subprocess import check_output, STDOUT


def execute(cmd: str) -> str:
    output = check_output(cmd, shell=True, stderr=STDOUT)
    return output.decode()
