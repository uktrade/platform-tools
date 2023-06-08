import yaml
from pathlib import Path
from schema import SchemaError
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from cloudfoundry_client.common_objects import JsonObject

from commands.bootstrap_cli import get_paas_env_vars
from commands.bootstrap_cli import load_and_validate_config



class MockEntity(JsonObject):
    def spaces(self):
        space = MockEntity(entity={"name":"trade-space"})
        return [space]
    
    def apps(self):
        app = MockEntity(entity={"name":"trade-app", "environment_json": {"ENV_VAR": "TEST"}})
        return [app]


@patch("commands.bootstrap_cli.CloudFoundryClient", return_value=MagicMock)
def test_get_pass_env_vars(client):
    """Test that, given a CloudFoundryClient instance and an app's path string, get_pa"""
    
    org = MockEntity(entity={"name": "dit-blah"})
    client.v2.organizations = [org]
    paas = "dit-blah/trade-space/trade-app"
    env_vars = get_paas_env_vars(client, paas)
    
    assert env_vars == {"ENV_VAR": "TEST"}
    
    
def test_get_paas_env_vars_exception():
    """Test that get_pass_env_vars raises expected Exception error message when no application is found."""
    
    client = MagicMock()
    paas = "dit-blah/trade-space/trade-app"
    
    with pytest.raises(Exception) as err:
        get_paas_env_vars(client, paas)
    
    assert err.value.args[0] == f"Application {paas} not found"
    

def test_load_and_validate_config_valid_file():
    """Test that, given the path to a valid yaml file, load_and_validate_config returns the loaded yaml unmodified."""
    
    path = Path(__file__).parent.resolve() / "test_config.yaml"
    validated = load_and_validate_config(path)
    
    with open(path, "r") as fd:
        conf = yaml.safe_load(fd)
    
    assert validated == conf


def test_load_and_validate_config_invalid_file():
    path = Path(__file__).parent.resolve() / "invalid_test_config.yaml"
    
    with pytest.raises(SchemaError) as err:
        load_and_validate_config(path)
    
    assert err.value.args[0] == "Key 'environments' error:\n[{'test': None, 'certificate_arns': ['ACM-ARN-FOR-test.landan.cloudapps.digital']}, {'production': None, 'certificate_arns': ['ACM-ARN-FOR-test.landan.cloudapps.digital']}] should be instance of 'dict'"
    