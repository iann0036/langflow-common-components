# pyright: reportCallIssue=false
import requests
import json
from typing import Any
from lfx.custom.custom_component.component import Component
from lfx.io import MessageTextInput, StrInput, Output
from lfx.schema.data import Data


class SlackMessage(Component):
    display_name = "Slack Message"
    description = "Sends a message to a Slack channel via webhook."
    documentation: str = "https://github.com/iann0036/langflow-common-components"
    icon = "slack" # https://lucide.dev/icons/
    name = "SlackMessage"

    inputs: list[Any] = [
        StrInput(
            name="webhook_url",
            display_name="Webhook URL",
            info="The Slack webhook URL to send messages to.",
            required=True,
        ),
        MessageTextInput(
            name="message",
            display_name="Message",
            info="The message to send to Slack.",
            required=True,
            tool_mode=True,
        ),
        MessageTextInput(
            name="blocks_data",
            display_name="Blocks Data",
            info="The blocks data to send alongside the message, as a JSON string.",
            tool_mode=True,
        ),
    ]

    outputs = [
        Output(display_name="Status", name="output", method="send_slack_message"),
    ]

    def send_slack_message(self) -> Data:
        payload = {
            "text": self.message
        }

        if self.blocks_data:
            try:
                blocks = json.loads(self.blocks_data.message)
                if not isinstance(blocks, list):
                    raise ValueError("Blocks data must be a JSON array.")
                payload["blocks"] = blocks
            except Exception as e:
                raise ValueError(f"Invalid blocks data: {e}")
        
        response = requests.post(self.webhook_url, json=payload)
        response.raise_for_status()
        data = Data(data={"status": "success"})
        self.status = "Sent Slack Message"
        return data
