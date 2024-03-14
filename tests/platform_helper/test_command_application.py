from unittest.mock import patch

from click.testing import CliRunner
from moto import mock_ecs
from moto import mock_logs
from moto import mock_sts

from dbt_platform_helper.commands.application import container_stats
from dbt_platform_helper.commands.application import task_stats

# from tests.platform_helper.conftest import mock_application


results = {
    "results": [
        [
            {"field": "TaskId", "value": "cc8c4319890d4700a94fa7ed8c8949ee"},
            {"field": "TaskDefinitionFamily", "value": "intranet-hotfix-beat"},
            {"field": "TaskDefinitionRevision", "value": "10"},
            {"field": "StorageReadBytes", "value": "121540608"},
            {"field": "StorageWriteBytes", "value": "0"},
            {"field": "NetworkRxPackets", "value": "1692606"},
            {"field": "NetworkTxBytes", "value": "613"},
            {"field": "KnownStatus", "value": "RUNNING"},
            {"field": "max(CpuUtilized)", "value": "3.6067"},
            {"field": "max(MemoryUtilized)", "value": "193"},
            {"field": "max(EphemeralStorageUtilized)", "value": "2.14"},
        ],
        [
            {"field": "TaskId", "value": "b69144bc79b04b1ba29e548abfcfa157"},
            {"field": "TaskDefinitionFamily", "value": "intranet-hotfix-worker"},
            {"field": "TaskDefinitionRevision", "value": "10"},
            {"field": "StorageReadBytes", "value": "122626048"},
            {"field": "StorageWriteBytes", "value": "196608"},
            {"field": "NetworkRxPackets", "value": "2130282"},
            {"field": "NetworkTxBytes", "value": "712"},
            {"field": "KnownStatus", "value": "RUNNING"},
            {"field": "max(CpuUtilized)", "value": "1.6322"},
            {"field": "max(MemoryUtilized)", "value": "352"},
            {"field": "max(EphemeralStorageUtilized)", "value": "2.14"},
        ],
        [
            {"field": "TaskId", "value": "67e49dd9af094474bad8f58eb6d6061e"},
            {"field": "TaskDefinitionFamily", "value": "intranet-hotfix-web"},
            {"field": "TaskDefinitionRevision", "value": "15"},
            {"field": "StorageReadBytes", "value": "253816832"},
            {"field": "StorageWriteBytes", "value": "8192"},
            {"field": "NetworkRxPackets", "value": "1114386"},
            {"field": "NetworkTxBytes", "value": "1128"},
            {"field": "KnownStatus", "value": "RUNNING"},
            {"field": "max(CpuUtilized)", "value": "7.2932"},
            {"field": "max(MemoryUtilized)", "value": "357"},
            {"field": "max(EphemeralStorageUtilized)", "value": "4.07"},
        ],
        [
            {"field": "TaskId", "value": "25aa2186290d4be3bda996a8bb5b83f9"},
            {"field": "TaskDefinitionFamily", "value": "intranet-hotfix-web"},
            {"field": "TaskDefinitionRevision", "value": "15"},
            {"field": "StorageReadBytes", "value": "280645632"},
            {"field": "StorageWriteBytes", "value": "8192"},
            {"field": "NetworkRxPackets", "value": "2458539"},
            {"field": "NetworkTxBytes", "value": "1114"},
            {"field": "KnownStatus", "value": "RUNNING"},
            {"field": "max(CpuUtilized)", "value": "6.5128"},
            {"field": "max(MemoryUtilized)", "value": "361"},
            {"field": "max(EphemeralStorageUtilized)", "value": "4.09"},
        ],
        [
            {"field": "TaskId", "value": "6dfa2088ba0f4ae7aca1d08405f3615e"},
            {"field": "TaskDefinitionFamily", "value": "intranet-hotfix-web"},
            {"field": "TaskDefinitionRevision", "value": "15"},
            {"field": "StorageReadBytes", "value": "252801024"},
            {"field": "StorageWriteBytes", "value": "8192"},
            {"field": "NetworkRxPackets", "value": "1112586"},
            {"field": "NetworkTxBytes", "value": "1496"},
            {"field": "KnownStatus", "value": "RUNNING"},
            {"field": "max(CpuUtilized)", "value": "7.5773"},
            {"field": "max(MemoryUtilized)", "value": "358"},
            {"field": "max(EphemeralStorageUtilized)", "value": "4.07"},
        ],
        [
            {"field": "TaskId", "value": "5e5e9eb34fd44bf1a6dc0a7d31435099"},
            {"field": "TaskDefinitionFamily", "value": "intranet-hotfix-web"},
            {"field": "TaskDefinitionRevision", "value": "15"},
            {"field": "StorageReadBytes", "value": "251211776"},
            {"field": "StorageWriteBytes", "value": "8192"},
            {"field": "NetworkRxPackets", "value": "1070550"},
            {"field": "NetworkTxBytes", "value": "1390"},
            {"field": "KnownStatus", "value": "RUNNING"},
            {"field": "max(CpuUtilized)", "value": "7.8469"},
            {"field": "max(MemoryUtilized)", "value": "355"},
            {"field": "max(EphemeralStorageUtilized)", "value": "4.07"},
        ],
        [
            {"field": "TaskId", "value": "0ae6a9d6ad9042e0b10a73cc8ac448c2"},
            {"field": "TaskDefinitionFamily", "value": "intranet-hotfix-s3proxy"},
            {"field": "TaskDefinitionRevision", "value": "10"},
            {"field": "StorageReadBytes", "value": "726413312"},
            {"field": "StorageWriteBytes", "value": "8192"},
            {"field": "NetworkRxPackets", "value": "1552221"},
            {"field": "NetworkTxBytes", "value": "2415"},
            {"field": "KnownStatus", "value": "RUNNING"},
            {"field": "max(CpuUtilized)", "value": "14.9255"},
            {"field": "max(MemoryUtilized)", "value": "281"},
            {"field": "max(EphemeralStorageUtilized)", "value": "2.77"},
        ],
    ],
    "statistics": {"recordsMatched": 7.0, "recordsScanned": 133.0, "bytesScanned": 113082.0},
    "status": "Complete",
    "ResponseMetadata": {
        "RequestId": "30635eb5-0b5b-4a6b-9e9e-0ff21492c1b2",
        "HTTPStatusCode": 200,
        "HTTPHeaders": {
            "x-amzn-requestid": "30635eb5-0b5b-4a6b-9e9e-0ff21492c1b2",
            "content-type": "application/x-amz-json-1.1",
            "content-length": "3965",
            "date": "Wed, 07 Feb 2024 20:07:43 GMT",
        },
        "RetryAttempts": 0,
    },
}


# @mock_logs
# @mock_ecs
# @mock_sts
# @mock_ssm
# @patch("dbt_platform_helper.commands.application.load_application")
# def test_get_query_results(alias_session, mock_application):
#     session = boto3.Session(region_name="eu-west-2")
#     session.client("ecs").create_cluster(clusterName="testapp-dev-Cluster-blah")
#     session.client("ecs").create_cluster(clusterName="testapp-test-Cluster-blah")

#     # Currently get_query_results is not returning anything for our query, as per doc
#     # not all query results are implemented.   http://docs.getmoto.org/en/latest/docs/services/logs.html
#     # So for now we will only check for 200 success code.
#     #
#     session.client("logs").create_log_group(
#         logGroupName="/aws/ecs/containerinsights/testapp-test-Cluster-blah/performance"
#     )
#     session.client("logs").create_log_stream(
#         logGroupName="/aws/ecs/containerinsights/testapp-test-Cluster-blah/performance",
#         logStreamName="FargateTelemetry-7624",
#     )
#     message = '{"Version":"0","Type":"Task","TaskId":"3f6db7f58bd145c7a668f562ff896fb7","TaskDefinitionFamily":"testapp-test-web","TaskDefinitionRevision":"2","ServiceName":"testapp-test-web-Service-blah","ClusterName":"testapp-test-Cluster-blah","KnownStatus":"RUNNING","CreatedAt":1707384290000,"StartedAt":1707384290000,"Timestamp":1707384300000,"CpuUtilized":23.619295457204185,"CpuReserved":256,"MemoryUtilized":277,"MemoryReserved":1024,"StorageReadBytes":138981376,"StorageWriteBytes":1806336,"NetworkRxBytes":2198,"NetworkRxPackets":3125725,"NetworkTxBytes":1005,"NetworkTxPackets":3039639}'
#     session.client("logs").put_log_events(
#         logGroupName="/aws/ecs/containerinsights/testapp-test-Cluster-blah/performance",
#         logStreamName="FargateTelemetry-7624",
#         logEvents=[
#             {"timestamp": 1707469200000, "message": message},
#         ],
#     )

#     result = get_query_results("test", "testapp", "query_string", -1)
#     assert result["ResponseMetadata"]["HTTPStatusCode"] == 200


@mock_logs
@mock_ecs
@mock_sts
@patch("dbt_platform_helper.commands.application.get_query_results", return_value=results)
def test_stats(alias_session):
    runner = CliRunner()
    result = runner.invoke(task_stats, ["--app", "app", "--env", "env"])

    assert (
        "beat     cc8c4319890d4700a94fa7ed8c8949ee  10        RUNNING  3.6%   193M" in result.output
    )
    assert (
        "web      25aa2186290d4be3bda996a8bb5b83f9  15        RUNNING  6.5%   361M" in result.output
    )
    assert (
        "s3proxy  0ae6a9d6ad9042e0b10a73cc8ac448c2  10        RUNNING  14.9%  281M" in result.output
    )
    assert (
        "worker   b69144bc79b04b1ba29e548abfcfa157  10        RUNNING  1.6%   352M" in result.output
    )


@mock_logs
@mock_ecs
@mock_sts
@patch("dbt_platform_helper.commands.application.get_query_results", return_value=results)
def test_stats_all_options(alias_session):
    runner = CliRunner()
    result = runner.invoke(
        task_stats,
        ["--app", "app", "--env", "env", "--storage", "--network"],
    )

    assert (
        "beat     cc8c4319890d4700a94fa7ed8c8949ee  10        RUNNING  3.6%   193M    121540608  0           1692606   613"
        in result.output
    )
    assert (
        "web      25aa2186290d4be3bda996a8bb5b83f9  15        RUNNING  6.5%   361M    280645632  8192        2458539   1114"
        in result.output
    )
    assert (
        "s3proxy  0ae6a9d6ad9042e0b10a73cc8ac448c2  10        RUNNING  14.9%  281M    726413312  8192        1552221   2415"
        in result.output
    )
    assert (
        "worker   b69144bc79b04b1ba29e548abfcfa157  10        RUNNING  1.6%   352M    122626048  196608      2130282   712"
        in result.output
    )


@mock_logs
@mock_ecs
@mock_sts
@patch("dbt_platform_helper.commands.application.get_query_results", return_value=results)
def test_container_stats(alias_session):
    runner = CliRunner()
    result = runner.invoke(container_stats, ["--app", "app", "--env", "env"])

    assert (
        "intranet-hotfix-beat  193.0%  2.14M   121540608  0     \n\nType:     10\nTask ID:  b69144bc79b04b1ba29e548abfcfa157"
        in result.output
    )
    assert (
        "intranet-hotfix-web  361.0%  4.09M   280645632  8192  \n\nType:     15\nTask ID:  6dfa2088ba0f4ae7aca1d08405f3615e"
        in result.output
    )
    assert (
        "intranet-hotfix-worker  352.0%  2.14M   122626048  196608 \n\nType:     15\nTask ID:  67e49dd9af094474bad8f58eb6d6061e"
        in result.output
    )
    assert (
        "intranet-hotfix-web  355.0%  4.07M   251211776  8192  \n\nType:     10\nTask ID:  0ae6a9d6ad9042e0b10a73cc8ac448c2"
        in result.output
    )


@mock_logs
@mock_ecs
@mock_sts
@patch("dbt_platform_helper.commands.application.get_query_results", return_value=results)
def test_container_stats_all_options(alias_session):
    runner = CliRunner()
    result = runner.invoke(
        container_stats,
        ["--app", "app", "--env", "env", "--storage", "--network"],
    )

    assert "intranet-hotfix-beat  193.0%  2.14M   121540608  1692606    613" in result.output
    assert "intranet-hotfix-web  361.0%  4.09M   280645632  2458539    1114" in result.output
    assert "intranet-hotfix-worker  352.0%  2.14M   122626048  2130282    712" in result.output
    assert "intranet-hotfix-web  355.0%  4.07M   251211776  1070550    1390" in result.output
