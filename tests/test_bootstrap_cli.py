from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

import boto3
import pytest
import yaml
from click.testing import CliRunner
from cloudfoundry_client.common_objects import JsonObject
from moto import mock_ssm
from schema import SchemaError

from commands.bootstrap_cli import get_paas_env_vars
from commands.bootstrap_cli import instructions
from commands.bootstrap_cli import load_and_validate_config
from commands.bootstrap_cli import make_config
from commands.bootstrap_cli import migrate_secrets
from commands.utils import set_ssm_param


class MockEntity(JsonObject):
    def spaces(self):
        space = MockEntity(entity={"name": "trade-space"})
        return [space]

    def apps(self):
        app = MockEntity(entity={"name": "test-service", "environment_json": {"TEST_VAR": "TEST_VAR"}})
        return [app]


@patch("commands.bootstrap_cli.CloudFoundryClient", return_value=MagicMock)
def test_get_pass_env_vars(client):
    """Test that, given a CloudFoundryClient instance and an app's path string,
    get_paas_env_vars returns a dict of environment variables."""

    org = MockEntity(entity={"name": "dit-staging"})
    client.v2.organizations = [org]
    paas = "dit-staging/trade-space/test-service"
    env_vars = get_paas_env_vars(client, paas)

    assert env_vars == {"TEST_VAR": "TEST_VAR"}


def test_get_paas_env_vars_exception():
    """Test that get_pass_env_vars raises expected Exception error message when
    no application is found."""

    client = MagicMock()
    paas = "dit-blah/trade-space/trade-app"

    with pytest.raises(Exception) as err:
        get_paas_env_vars(client, paas)

    assert err.value.args[0] == f"Application {paas} not found"


def test_load_and_validate_config_valid_file():
    """Test that, given the path to a valid yaml file, load_and_validate_config
    returns the loaded yaml unmodified."""

    path = Path(__file__).parent.resolve() / "test_config.yaml"
    validated = load_and_validate_config(path)

    with open(path, "r") as fd:
        conf = yaml.safe_load(fd)

    assert validated == conf


def test_load_and_validate_config_invalid_file():
    """Test that, given the path to an invalid yaml file,
    load_and_validate_config raises a SchemaError with specific field errors."""

    path = Path(__file__).parent.resolve() / "invalid_test_config.yaml"

    with pytest.raises(SchemaError) as err:
        load_and_validate_config(path)

    assert (
        err.value.args[0]
        == "Key 'environments' error:\n[{'test': None, 'certificate_arns': ['ACM-ARN-FOR-test.landan.cloudapps.digital']}, {'production': None, 'certificate_arns': ['ACM-ARN-FOR-test.landan.cloudapps.digital']}] should be instance of 'dict'"
    )


def test_make_config(tmp_path):
    """Test that, given a config file path and an output path, make_config
    generates the expected directories and file contents."""

    config_file_path = Path(__file__).parent.resolve() / "test_config.yaml"
    runner = CliRunner()
    result = runner.invoke(make_config, [str(config_file_path), str(tmp_path)])

    assert (
        "GitHub documentation: https://github.com/uktrade/platform-documentation/blob/main/gov-pass-to-copiltot-migration"
        in result.output
    )
    assert (tmp_path / "copilot").exists()

    with open(str(tmp_path / "copilot/.workspace")) as workspace:
        assert workspace.read() == "application: test-app"

    with open(str(tmp_path / "copilot/environments/test/manifest.yml")) as test:
        assert (
            test.read()
            == '# The manifest for the "dev" environment.\n# Read the full specification for the "Environment" type at:\n#  https://aws.github.io/copilot-cli/docs/manifest/environment/\n\n# Your environment name will be used in naming your resources like VPC, cluster, etc.\nname: test\ntype: Environment\n\n# Import your own VPC and subnets or configure how they should be created.\n# network:\n#   vpc:\n#     id:\n\n# Configure the load balancers in your environment, once created.\n\nhttp:\n  public:\n    certificates:\n      - ACM-ARN-FOR-test.landan.cloudapps.digital\n#   private:\n\n\n# Configure observability for your environment resources.\nobservability:\n  container_insights: true'
        )

    with open(str(tmp_path / "copilot/environments/production/manifest.yml")) as production:
        assert (
            production.read()
            == '# The manifest for the "dev" environment.\n# Read the full specification for the "Environment" type at:\n#  https://aws.github.io/copilot-cli/docs/manifest/environment/\n\n# Your environment name will be used in naming your resources like VPC, cluster, etc.\nname: production\ntype: Environment\n\n# Import your own VPC and subnets or configure how they should be created.\n# network:\n#   vpc:\n#     id:\n\n# Configure the load balancers in your environment, once created.\n\nhttp:\n  public:\n    certificates:\n      - ACM-ARN-FOR-test.landan.cloudapps.digital\n#   private:\n\n\n# Configure observability for your environment resources.\nobservability:\n  container_insights: true'
        )

    with open(str(tmp_path / "copilot/test-service/manifest.yml")) as service:
        assert (
            service.read()
            == "# The manifest for the \"web\" service.\n# Read the full specification for the \"Load Balanced Web Service\" type at:\n#  https://aws.github.io/copilot-cli/docs/manifest/lb-web-service/\n\n# Your service name will be used in naming your resources like log groups, ECS services, etc.\nname: test-service\ntype: Load Balanced Web Service\n\n# Distribute traffic to your service.\nhttp:\n  # Requests to this path will be forwarded to your service.\n  # To match all requests you can use the \"/\" path.\n  path: '/'\n  # You can specify a custom health check path. The default is \"/\".\n  # healthcheck: '/'\n  target_container: nginx\n  healthcheck:\n    path: '/'\n    port: 8080\n    success_codes: '200,301,302'\n    healthy_threshold: 3\n    unhealthy_threshold: 2\n    interval: 35s\n    timeout: 30s\n    grace_period: 90s\n\nsidecars:\n  nginx:\n    port: 443\n    image: public.ecr.aws/uktrade/nginx-reverse-proxy:latest\n    variables:\n      SERVER: localhost:8000\n      \n\n\n\n  ipfilter:\n    port: 8000\n    image: public.ecr.aws/h0i0h2o7/uktrade/ip-filter:latest\n    variables:\n      PORT: 8000\n      EMAIL_NAME: 'The Department for International Trade WebOps team'\n      EMAIL: test@test.test\n      LOG_LEVEL: DEBUG\n      ORIGIN_HOSTNAME: localhost:8080\n      ORIGIN_PROTO: http\n      CONFIG_FILE: 's3://ipfilter-config/ROUTES.yaml'\n\n\n# Configuration for your containers and service.\nimage:\n\n  location: not-a-url\n    # Port exposed through your container to route traffic to it.\n  port: 8080\n\ncpu: 256       # Number of CPU units for the task.\nmemory: 512 # Amount of memory in MiB used by the task.\ncount: # See https://aws.github.io/copilot-cli/docs/manifest/lb-web-service/#count\n  range: 2-10\n  cooldown:\n    in: 120s\n    out: 60s\n  cpu_percentage: 50\nexec: true     # Enable running commands in your container.\nnetwork:\n  connect: true # Enable Service Connect for intra-environment traffic between services.\n\n# storage:\n  # readonly_fs: true       # Limit to read-only access to mounted root filesystems.\n\n# Optional fields for more advanced use-cases.\n#\nvariables:                    # Pass environment variables as key value pairs.\n  PORT: 8080\n  TEST_VAR:\n  \n\n\n\nsecrets:                      # Pass secrets from AWS Systems Manager (SSM) Parameter Store.\n  TEST_SECRET: /copilot/${COPILOT_APPLICATION_NAME}/${COPILOT_ENVIRONMENT_NAME}/secrets/TEST_SECRET\n  \n\n\n# You can override any of the values defined above by environment.\nenvironments:\n  production:\n    http:\n      alias: test-service.trad.gav.ikx\n  test:\n    http:\n      alias: test-service.landan.cloudapps.digitalx# TODO: enable/disable ip filter on a per env basis.  For example, an service may need an the ip filter in non prod envs, but not prod."
        )


@patch("commands.bootstrap_cli.CloudFoundryClient", return_value=MagicMock)
def test_migrate_secrets_env_not_in_config(client):
    """Test that, given a config file path and an environment not found in that
    file, migrate_secrets outputs the expected error message."""

    config_file_path = Path(__file__).parent.resolve() / "test_config.yaml"
    runner = CliRunner()
    result = runner.invoke(migrate_secrets, [str(config_file_path), "--env", "staging", "--svc", "test-service"])
    path = str(Path(__file__).parent.resolve() / "test_config.yaml")
    assert f"staging is not an environment in {path}" in result.output


@patch("commands.bootstrap_cli.CloudFoundryClient", return_value=MagicMock)
def test_migrate_secrets_service_not_in_config(client):
    """Test that, given a config file path and a secret not found in that file,
    migrate_secrets outputs the expected error message."""

    config_file_path = Path(__file__).parent.resolve() / "test_config.yaml"
    runner = CliRunner()
    result = runner.invoke(migrate_secrets, [str(config_file_path), "--env", "test", "--svc", "blah"])
    path = str(Path(__file__).parent.resolve() / "test_config.yaml")
    assert f"blah is not a service in {path}" in result.output


@pytest.mark.parametrize(
    "env_vars,param_value",
    [({}, "NOT FOUND"), ({"TEST_SECRET": None}, "EMPTY"), ({"TEST_SECRET": "TEST_SECRET"}, "TEST_SECRET")],
)
@mock_ssm
@patch("commands.bootstrap_cli.get_paas_env_vars")
@patch("commands.bootstrap_cli.CloudFoundryClient", return_value=MagicMock)
def test_migrate_secrets_param_doesnt_exist(client, get_paas_env_vars, env_vars, param_value):
    """Test that, where a secret doesn't already exist in aws ssm,
    migrate_secrets creates it."""

    get_paas_env_vars.return_value = env_vars
    config_file_path = Path(__file__).parent.resolve() / "test_config.yaml"
    runner = CliRunner()
    result = runner.invoke(migrate_secrets, [str(config_file_path), "--env", "test", "--svc", "test-service"])

    assert ">>> migrating secrets for service: test-service; environment: test" in result.output
    assert "Created" in result.output

    client = boto3.session.Session().client("ssm")
    response = client.get_parameter(Name="/copilot/test-app/test/secrets/TEST_SECRET")

    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert response["Parameter"]["Value"] == f"kms:alias/aws/ssm:{param_value}"


@mock_ssm
@patch("commands.bootstrap_cli.get_paas_env_vars", return_value={})
@patch("commands.bootstrap_cli.CloudFoundryClient", return_value=MagicMock)
def test_migrate_secrets_param_already_exists(client, get_paas_env_vars):
    """Test that, where a secret already exists in aws ssm and overwrite flag
    isn't set, migrate_secrets doesn't update it."""

    set_ssm_param("test-app", "test", "/copilot/test-app/test/secrets/TEST_SECRET", "NOT_FOUND", False, False)
    config_file_path = Path(__file__).parent.resolve() / "test_config.yaml"
    runner = CliRunner()
    result = runner.invoke(migrate_secrets, [str(config_file_path), "--env", "test", "--svc", "test-service"])

    assert "NOT overwritten" in result.output

    client = boto3.session.Session().client("ssm")
    response = client.get_parameter(Name="/copilot/test-app/test/secrets/TEST_SECRET")

    assert response["Parameter"]["Version"] == 1


@mock_ssm
@patch("commands.bootstrap_cli.get_paas_env_vars", return_value={})
@patch("commands.bootstrap_cli.CloudFoundryClient", return_value=MagicMock)
def test_migrate_secrets_overwrite(client, get_paas_env_vars):
    """Test that, where a secret already exists in aws ssm and overwrite flag is
    set, migrate_secrets updates it."""

    set_ssm_param("test-app", "test", "/copilot/test-app/test/secrets/TEST_SECRET", "NOT_FOUND", False, False)
    config_file_path = Path(__file__).parent.resolve() / "test_config.yaml"
    runner = CliRunner()
    result = runner.invoke(
        migrate_secrets,
        [str(config_file_path), "--env", "test", "--svc", "test-service", "--overwrite"],
    )

    assert "Overwritten" in result.output
    assert "NOT overwritten" not in result.output

    client = boto3.session.Session().client("ssm")
    response = client.get_parameter(Name="/copilot/test-app/test/secrets/TEST_SECRET")

    assert response["Parameter"]["Version"] == 2


@mock_ssm
@patch("commands.bootstrap_cli.get_paas_env_vars", return_value={})
@patch("commands.bootstrap_cli.CloudFoundryClient", return_value=MagicMock)
def test_migrate_secrets_dry_run(client, get_paas_env_vars):
    """Test that, when dry-run flag is passed, migrate_secrets does not create a
    secret."""

    config_file_path = Path(__file__).parent.resolve() / "test_config.yaml"
    runner = CliRunner()
    result = runner.invoke(
        migrate_secrets,
        [str(config_file_path), "--env", "test", "--svc", "test-service", "--dry-run"],
    )

    assert (
        "/copilot/test-app/test/secrets/TEST_SECRET not created because `--dry-run` flag was included."
        in result.output
    )

    client = boto3.session.Session().client("ssm")

    with pytest.raises(client.exceptions.ParameterNotFound):
        client.get_parameter(Name="/copilot/test-app/test/secrets/TEST_SECRET")


def test_instructions():
    """Test that, given the path to a config file, instructions generates output
    for specific services and environments."""

    config_file_path = Path(__file__).parent.resolve() / "test_config.yaml"
    runner = CliRunner()
    result = runner.invoke(instructions, [str(config_file_path)])

    assert (
        result.output
        == "DEPLOYMENT INSTRUCTIONS\n\nProject files have been written to the copilot/ directory.  Any changes to these files should be committed to github.\n\nRun the following commands to bootstrap the app:\n\nNOTES:\n1. you will need to export the AWS_PROFILE env var for the copilot cli tool to pick up:  export AWS_PROFILE=your-aws-profile\n2. Environments will need an ACM TLS certs setting up before they can be deployed.  Speak to SRE for assistance.\n\nYou do not need to follow all of the instructions in sequence. For instance, you may decide to just initialise and deploy one environment, and then deploy a single service into that environment.\n\n# 1. init the app\n\ncopilot app init\n\n# 2. init each service\n\ncopilot svc init --name test-service\n\n# 3. initialise each environment\n\nNOTE: ensure ACM certs have been created and the cert ARNs added to each env's `copilot/environments/{env}/manifest.yml' file first.\n\nWhen running \"copilot env init\" chose the following options:\n* Credential source: the correct account that the env should exist in. [NOTE: environments can live in separate accounts.]\n* Default environment configuration? Yes, use default.\n\n\ncopilot env init --name test\ncopilot env init --name production\n\n# 4. deploy each environment\n\ncopilot env deploy --name test\ncopilot env deploy --name production\n\n# 5. migrate the secrets from Gov Paas to AWS/Copilot\n\ncopilot-bootstrap.py migrate-secrets /Users/gabrielnaughton/development/copilot-tools/tests/test_config.yaml\n\nYou need to be authenticated via the CF CLI for this command to work.\nUse the --dry-run flag initially to check the output\n\n# 6. deploy each service into each environment\n\n# test-service:\ncopilot svc deploy --name test-service --env test\ncopilot svc deploy --name test-service --env production\n\n\n# 7. Point DNS entries to ALB urls\n\nSpeak to SRE.\n\n# 8. Generate the storage addons\n\nCreate a storage.yml and add the relevant configuration.  See SRE for assistance.\n\nGenerate environment level storage addons\n\ncopilot-bootstrap generate-storage storage.yaml\n\nAdd required secrets to each service's manifest.yml.\n\nRedeploy each environment to provision those secrets\n\n\ncopilot env deploy --name test\ncopilot env deploy --name production\n\n# 9. Switch the bootstrap container to the service container\n\nEdit each copilot/{service-name}/manifest.yaml file and replace the image_location with the service's ECR registry url and redeploy.\n\nIt's expected that you'll need to iterate over this step a number of times whilst making changes to the services manifest.yml until the service is stable.\n"
    )
