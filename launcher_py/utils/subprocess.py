from subprocess import check_output, STDOUT, CalledProcessError
import logging
from launcher.errors import ExecutionError


logger = logging.getLogger(__name__)


def run(cmd: str) -> str:
    try:
        output = check_output(cmd, shell=True, stderr=STDOUT)
        text = output.decode().rstrip()
        if "logs" in cmd:
            logger.debug("[Run] %s", cmd)
        else:
            logger.debug("[Run] %s\n%s", cmd, text)
        return text
    except CalledProcessError as e:
        text = e.output.decode().rstrip()
        if text.strip() == "":
            text = "<no output>"
        logger.error("[Run] %s (exit %s)\n%s", cmd, e.returncode, text)
        raise ExecutionError(str(e), e.returncode, text)
