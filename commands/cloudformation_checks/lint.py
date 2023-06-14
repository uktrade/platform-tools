from pathlib import Path

from subprocess import run


def lint():
    output = []
    BASE_DIR = Path(__file__).parent.parent.parent

    command = ["cfn-lint", f"{BASE_DIR}/tests/test-application/copilot/**/addons/*.yml"]

    output.append(f"""\nRunning {" ".join(command)}""")

    result = run(command, capture_output=True)

    output.append(result.stdout.decode())
    if result.returncode != 0:
        output.append(result.stderr.decode())

    return "\n".join(output)
