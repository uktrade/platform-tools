import json
import logging
from typing import Dict
from typing import List
from typing import Tuple

import requests

logger = logging.getLogger()


class SlackNotificationService:
    def __init__(self, slack_token: str, slack_channel: str, aws_account: str):
        self.slack_token = slack_token
        self.slack_channel = slack_channel
        self.aws_account = aws_account
        self.slack_api_url = "https://slack.com/api/chat.postMessage"

    def send_test_failures(
        self,
        failures: List[Dict],
        environment: str,
        application: str,
        channel: str = None,
    ) -> None:
        """Send formatted test failure notifications to Slack."""
        try:
            message_blocks, summary_text, failure_text = self._build_failure_message(
                failures, environment, application
            )
            logger.info("Attempt sending Slack notification for test failures")

            # Send the initial message to Slack
            response = self._send_message(
                channel or self.slack_channel, summary_text, message_blocks
            )

            # If there's overflow text, send it as threaded messages
            max_length = 2900
            if len(failure_text) > max_length:
                for i in range(0, len(failure_text), max_length):
                    thread_text = failure_text[i : i + max_length]
                    self._send_message(
                        channel or self.slack_channel,
                        thread_text,
                        thread_ts=response["ts"],
                    )
                    logger.info("Additional failure details sent in thread")

        except Exception as e:
            logger.error(f"Failed to send Slack notification: {str(e)}")

    def _send_message(
        self, channel: str, text: str, blocks: List[Dict] = None, thread_ts: str = None
    ) -> Dict:
        """Sends a message to Slack using the Slack API."""
        headers = {
            "Content-type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {self.slack_token}",
        }

        payload = {
            "channel": channel,
            "text": text,
            "blocks": blocks or [],
        }

        if thread_ts:
            payload["thread_ts"] = thread_ts

        response = requests.post(self.slack_api_url, headers=headers, data=json.dumps(payload))

        if response.status_code != 200 or not response.json().get("ok", False):
            raise ValueError(
                f"Error sending message to Slack: {response.status_code}, {response.text}"
            )

        return response.json()

    def _build_failure_message(
        self, failures: List[Dict], environment: str, application: str
    ) -> Tuple[List[Dict], str, str]:
        message_blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":rotating_light: Secret Rotation Test Failures",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Environment:* {environment}\n*Application:* {application}\n*Application AWS account:* {self.aws_account}",
                },
            },
        ]

        # Prepare the detailed failure text
        failure_text = ""
        for failure in failures:
            entry = f"• Domain: {failure['domain']}\n"
            if "secret_type" in failure:
                entry += f"  Secret Type: {failure['secret_type']}\n"
            if "error" in failure:
                entry += f"  Error: {failure['error']}\n"
            failure_text += entry

        # Truncate main message if needed and indicate continuation in thread
        max_length = 2900
        truncated_text = failure_text[:max_length]
        if len(failure_text) > max_length:
            truncated_text += "\n*...continued in thread.*"

        message_blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Failures:*\n{truncated_text}"},
            }
        )

        # Summary text for accessibility
        summary_text = f"Secret Rotation Test Failures for {application} in {environment}"

        return message_blocks, summary_text, failure_text
