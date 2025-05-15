from unittest.mock import MagicMock
from unittest.mock import call

import pytest

from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.utilities.decorators import RetryException
from dbt_platform_helper.utilities.decorators import retry
from dbt_platform_helper.utilities.decorators import wait_until


class TestRetryDecorator:
    def test_successful_execution_no_retry(self):
        mock_func = MagicMock(return_value="success")

        wrapped_func = retry(max_attempts=3, delay=0.01)(mock_func)

        result = wrapped_func("arg", kwarg="kwarg")

        assert mock_func.__wrapped_by__ == "retry"
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

        with pytest.raises(RetryException) as actual_exec:
            wrapped_func("arg", kwarg="kwarg")

        mock_func.assert_called_with("arg", kwarg="kwarg")

        assert mock_func.__name__ in str(actual_exec.value)
        assert "3 attempts" in str(actual_exec.value)
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

        with pytest.raises(ValueError) as actual_exec:
            wrapped_func("arg", kwarg="kwarg")

        mock_func.assert_called_with("arg", kwarg="kwarg")
        assert mock_func.call_count == 3
        assert "original exception" in str(actual_exec.value)


class TestWaitUntilDecorator:
    def test_successful_execution_no_wait(self):
        mock_func = MagicMock(return_value=True)

        wrapped_func = wait_until(max_attempts=3, delay=0.01)(mock_func)

        result = wrapped_func("arg", kwarg="kwarg")

        assert mock_func.__wrapped_by__ == "wait_until"
        mock_func.assert_called_once_with("arg", kwarg="kwarg")
        assert result is True

    def test_successful_execution_after_wait(self):
        mock_func = MagicMock(side_effect=[False, False, True])
        mock_func.__name__ = "mocked"

        wrapped_func = wait_until(max_attempts=5, delay=0.01, exceptions_to_catch=(ValueError,))(
            mock_func
        )

        result = wrapped_func("arg", kwarg="kwarg")

        expected_calls = [call("arg", kwarg="kwarg")] * 3
        mock_func.call_args_list == expected_calls
        assert result is True

    def test_condition_never_met(self):
        mock_func = MagicMock(return_value=False)
        mock_func.__name__ = "mocked"

        wrapped_func = wait_until(max_attempts=3, delay=0.01)(mock_func)

        with pytest.raises(RetryException) as actual_exec:
            wrapped_func("arg", kwarg="kwarg")

        assert mock_func.__name__ in str(actual_exec.value)
        assert "3 attempts" in str(actual_exec.value)
        assert "Condition not met" in str(actual_exec.value)
        assert mock_func.call_count == 3

    def test_exception_in_function(self):
        mock_func = MagicMock(side_effect=ValueError("error in function"))
        mock_func.__name__ = "mocked"

        wrapped_func = wait_until(
            max_attempts=3,
            delay=0.01,
            exceptions_to_catch=(ValueError,),
        )(mock_func)

        with pytest.raises(RetryException) as actual_exec:
            wrapped_func("arg", kwarg="kwarg")

        assert mock_func.__name__ in str(actual_exec.value)
        assert "3 attempts" in str(actual_exec.value)
        assert "error in function" in str(actual_exec.value)
        assert mock_func.call_count == 3

    def test_wait_until_exhausted_reraising_orginal_exception(self):
        mock_func = MagicMock(side_effect=ValueError("error in function"))
        mock_func.__name__ = "mocked"

        wrapped_func = wait_until(
            max_attempts=3,
            delay=0.01,
            exceptions_to_catch=(ValueError,),
            raise_custom_exception=False,
        )(mock_func)

        with pytest.raises(ValueError) as actual_exec:
            wrapped_func("arg", kwarg="kwarg")

        assert "error in function" in str(actual_exec.value)
        assert mock_func.call_count == 3

    def test_wait_until_condition_never_met_platform_exception(self):
        mock_func = MagicMock(return_value=False)
        mock_func.__name__ = "mocked"

        wrapped_func = wait_until(max_attempts=3, delay=0.01, raise_custom_exception=False)(
            mock_func
        )

        with pytest.raises(PlatformException) as actual_exec:
            wrapped_func("arg", kwarg="kwarg")

        assert "Condition not met" in str(actual_exec.value)
        assert mock_func.call_count == 3
