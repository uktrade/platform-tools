from pathlib import Path

from subprocess import run

from commands import check_cloudformation
from commands.cloudformation_checks.CheckCloudformationFailure import CheckCloudformationFailure


# @check_cloudformation.command()
def lint():
    output = []
    BASE_DIR = Path(__file__).parent.parent.parent

    command = ["cfn-lint", f"{BASE_DIR}/tests/test-application/copilot/**/addons/*.yml"]

    output.append(f"""\nRunning {" ".join(command)}""")

    result = run(command, capture_output=True)

    output.append(result.stdout.decode())
    if result.returncode != 0:
        output.append(result.stderr.decode())

    print("\n".join(output))
