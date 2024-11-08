import os

import boto3
import psycopg2
import pytest

S3_CONFIG = {
    "endpoint_url": "http://s3-mock:9000",
    "aws_access_key_id": "minioadmin",
    "aws_secret_access_key": "minioadmin",
    "region_name": "eu-west-2",
}

ECS_CONFIG = {
    "endpoint_url": "http://app:5000",
    "aws_access_key_id": "test",
    "aws_secret_access_key": "test",
    "region_name": "eu-west-2",
}


@pytest.fixture(scope="module")
def s3_client():
    return boto3.client("s3", **S3_CONFIG)


@pytest.fixture(scope="module")
def ecs_client():
    return boto3.client("ecs", **ECS_CONFIG)


@pytest.fixture(scope="module")
def source_db():
    conn = psycopg2.connect(os.getenv("SOURCE_DB_CONNECTION_STRING"))
    yield conn
    conn.close()


@pytest.fixture(scope="module")
def destination_db():
    conn = psycopg2.connect(os.getenv("DESTINATION_DB_CONNECTION_STRING"))
    yield conn
    conn.close()


def test_can_speak_to_source_db(source_db):
    new_cursor = source_db.cursor()
    new_cursor.execute("SELECT * FROM pg_catalog.pg_user")

    assert new_cursor.fetchone()[0] == "test_user"


def test_can_speak_to_destination_db(destination_db):
    new_cursor = destination_db.cursor()
    new_cursor.execute("SELECT * FROM pg_catalog.pg_user")

    assert new_cursor.fetchone()[0] == "test_user"


def test_can_speak_to_ecs(ecs_client):
    pass


def test_can_speak_to_s3(s3_client):
    response = s3_client.list_objects_v2(Bucket="test-dump-bucket")
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200


def test_data_is_dumped_into_s3(s3_client):
    response = s3_client.list_objects_v2(Bucket="test-dump-bucket")
    object = s3_client.get_object(Bucket="test-dump-bucket", Key="data_dump.sql")
    print(f"FILE CONTENTS: {object["Body"].read().decode("utf-8", errors='ignore')}")
    # assert response["Contents"][0]["Key"] == "data_dump.sql"
    assert False
    
# Trying to set up the source DB with a table so that there's something to migrate

