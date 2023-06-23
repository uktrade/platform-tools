import pytest

from commands.utils import check_aws_conn


def test_check_aws_conn_profile_not_configured(capsys):
    with pytest.raises(SystemExit):
        check_aws_conn("foo")

    captured = capsys.readouterr()

    assert "AWS profile not configured, please ensure they are set." in captured.out
