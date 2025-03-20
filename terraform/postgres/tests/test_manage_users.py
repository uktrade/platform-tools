import json
import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

import boto3
from moto import mock_aws
from postgres.manage_users import create_or_update_db_user
from postgres.manage_users import create_or_update_user_secret
from postgres.manage_users import handler


class TestManageUsers(unittest.TestCase):
    def setUp(self):
        self.cursor = MagicMock()

    @classmethod
    def setUpClass(cls):
        cls.secret_name = "test-secret-name"
        cls.secret_string = '{"engine": "mocked", "port": 1234, "dbname": "mocked", "host": "mocked", "username": "mocked", "password": "password123"}'
        cls.event = {
            "SecretName": cls.secret_name,
            "SecretDescription": "used for testing",
            "Username": "test-user",
            "Permissions": ["SELECT"],
            "CopilotApplication": "test-app",
            "CopilotEnvironment": "test",
            "DbEngine": "mocked",
            "DbPort": 1234,
            "DbName": "mocked",
            "DbHost": "mocked",
            "dbInstanceIdentifier": "mocked",
        }
        cls.context = MagicMock()
        cls.conn = MagicMock()
        cls.cursor = MagicMock()

    def test_create_or_update_db_user(self):
        self.cursor.fetchone.return_value = None
        conn = MagicMock()
        username = "test_user"
        password = "test_password"
        permissions = ["SELECT", "INSERT"]

        create_or_update_db_user(conn, self.cursor, username, password, permissions)

        self.cursor.execute.assert_any_call(
            f"CREATE USER {username} WITH ENCRYPTED PASSWORD '{password}'"
        )
        self.cursor.execute.assert_any_call(f"GRANT {username} to postgres;")
        self.cursor.execute.assert_any_call(
            f"GRANT {', '.join(permissions)} ON ALL TABLES IN SCHEMA public TO {username};"
        )
        self.cursor.execute.assert_any_call(
            f"ALTER DEFAULT PRIVILEGES FOR USER application_user IN SCHEMA public GRANT {', '.join(permissions)} ON TABLES TO {username};"
        )

        conn.commit.assert_called_once()

    def test_create_or_update_db_user_when_user_exists(self):
        self.cursor.fetchone.return_value = ["test_user"]
        conn = MagicMock()
        username = "test_user"
        password = "test_password"
        permissions = ["SELECT", "INSERT"]

        create_or_update_db_user(conn, self.cursor, username, password, permissions)

        self.cursor.execute.assert_any_call(
            f"ALTER USER {username} WITH ENCRYPTED PASSWORD '{password}'"
        )

        conn.commit.assert_called_once()

    @mock_aws
    def test_create_or_update_user_secret(self):
        ssm = boto3.client("ssm")
        user_secret_name = "/test/secret"
        user_secret_string = {"username": "test_user", "password": "test_password"}

        response = create_or_update_user_secret(
            ssm, user_secret_name, user_secret_string, self.event
        )
        parameter = ssm.get_parameter(Name=user_secret_name, WithDecryption=True)["Parameter"]
        parameter_described = ssm.describe_parameters()["Parameters"][0]

        assert response["Version"] == 1
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
        assert parameter["Name"] == user_secret_name
        assert parameter["Value"] == json.dumps(user_secret_string)
        assert parameter_described["Description"] == "used for testing"

    @mock_aws
    def test_create_or_update_user_secret_overwrites(self):
        ssm = boto3.client("ssm")
        user_secret_name = "/test/secret"
        user_secret_string = {"username": "test_user", "password": "test_password"}
        ssm.put_parameter(Name=user_secret_name, Value="blah", Type="String")

        create_or_update_user_secret(ssm, user_secret_name, user_secret_string, self.event)

        parameter = ssm.get_parameter(Name=user_secret_name)["Parameter"]

        assert parameter["Version"] == 2
        assert parameter["Value"] == json.dumps(user_secret_string)

    @patch("postgres.manage_users.create_or_update_db_user")
    @patch("postgres.manage_users.psycopg2.connect")
    @mock_aws
    def test_handler(self, mock_connect, mock_create_or_update_db_user):
        secretsmanager = boto3.client("secretsmanager")
        secret_id = secretsmanager.create_secret(
            Name=self.secret_name, SecretString=self.secret_string
        )["ARN"]

        self.event["MasterUserSecretArn"] = secret_id

        mock_connect.return_value = self.conn
        self.conn.cursor = self.cursor

        handler(self.event, self.context)

        user_password = json.loads(
            boto3.client("ssm").get_parameter(Name=self.secret_name, WithDecryption=True)[
                "Parameter"
            ]["Value"]
        )["password"]

        mock_create_or_update_db_user.assert_called_once_with(
            self.conn, self.cursor(), "test-user", user_password, ["SELECT"]
        )
