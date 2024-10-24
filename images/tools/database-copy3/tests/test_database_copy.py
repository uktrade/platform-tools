import boto3
import psycopg2
import pytest

S3_CONFIG = {
    "endpoint_url": "http://localhost:9000",
    "aws_access_key_id": "minioadmin",
    "aws_secret_access_key": "minioadmin",
    "region_name": "eu-west-2",
}

DESTINATION_DB_CONNECTION_STRING = "postgresql://user:pwd@destination_db:5432/destination_db"
SOURCE_DB_CONNECTION_STRING = "postgresql://user:pwd@source_db:5432/source_db"


@pytest.fixture(scope="module")
def s3_client():
    return boto3.client("s3", **S3_CONFIG)


@pytest.fixture(scope="module")
def source_db():
    conn = psycopg2.connect(SOURCE_DB_CONNECTION_STRING)
    yield conn
    conn.close()


# @pytest.fixture(scope="module")
# def destination_db():
#     conn = psycopg2.connect(DESTINATION_DB_CONNECTION_STRING)
#     yield conn
#     conn.close()


def test_can_speak_to_s3(s3_client):
    response = s3_client.list_objects_v2(Bucket="test-dump-bucket")
    print(response)
    assert "Contents" in response
