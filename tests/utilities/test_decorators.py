from unittest.mock import MagicMock
from unittest.mock import call

import pytest

from dbt_platform_helper.utilities.decorators import RetryException
from dbt_platform_helper.utilities.decorators import retry


class TestRetryDecorator:
    def test_successful_execution_no_retry(self):
        mock_func = MagicMock(return_value="success")

        wrapped_func = retry(max_attempts=3, delay=0.01)(mock_func)

        result = wrapped_func("arg", kwarg="kwarg")

        mock_func.assert_called_once_with("arg", kwarg="kwarg")
        assert result == "success"

    def test_retry_after_failures(self):
        mock_func = MagicMock(side_effect=[ValueError("error-1"), ValueError("error-2"), "success"])
        mock_func.__name__ = "mocked"

        wrapped_func = retry(max_attempts=3, delay=0.01, exceptions_to_catch=(ValueError,))(
            mock_func
        )

        result = wrapped_func("arg", kwarg="kwarg")
        expected_calls = [call("arg", kwarg="kwarg")] * 3
        mock_func.call_args_list == expected_calls
        assert result == "success"

    def test_retry_exhausted_raises_custom_exception(self):
        mock_func = MagicMock(side_effect=ValueError("error"))
        mock_func.__name__ = "mocked"

        wrapped_func = retry(max_attempts=3, delay=0.01, exceptions_to_catch=(ValueError,))(
            mock_func
        )

        with pytest.raises(RetryException) as actul_exec:
            wrapped_func("arg", kwarg="kwarg")

        mock_func.assert_called_with("arg", kwarg="kwarg")

        assert mock_func.__name__ in str(actul_exec.value)
        assert "3 attempts" in str(actul_exec.value)
        assert mock_func.call_count == 3

    def test_retry_exhausted_reraising_orginal_exception(self):
        mock_func = MagicMock(side_effect=ValueError("original exception"))
        mock_func.__name__ = "mocked"

        wrapped_func = retry(
            max_attempts=3,
            delay=0.01,
            exceptions_to_catch=(ValueError,),
            raise_custom_exception=False,
        )(mock_func)

        with pytest.raises(ValueError) as actul_exec:
            wrapped_func("arg", kwarg="kwarg")

        mock_func.assert_called_with("arg", kwarg="kwarg")
        assert mock_func.call_count == 3
        assert "original exception" in str(actul_exec.value)
