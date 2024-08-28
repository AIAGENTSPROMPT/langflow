from astra_assistants import patch  # type: ignore
from typing import Any, Optional

from langflow.custom import Component
from openai import OpenAI
from openai.lib.streaming import AssistantEventHandler
from langflow.inputs import MultilineInput
from langflow.schema import dotdict
from langflow.schema.message import Message
from langflow.template import Output


class AssistantsRun(Component):
    display_name = "Run Assistant"
    description = "Executes an Assistant Run against a thread"

    def update_build_config(
        self,
        build_config: dotdict,
        field_value: Any,
        field_name: Optional[str] = None,
    ):
        if field_name == "thread_id":
            if field_value is None:
                thread = self.client.beta.threads.create()
                self.thread_id = thread.id
                field_value
            build_config["thread_id"] = field_value

    inputs = [
        MultilineInput(
            name="assistant_id",
            display_name="Assistant ID",
            info=(
                "The ID of the assistant to run. \n\n"
                "Can be retrieved using the List Assistants component or created with the Create Assistant component."
            ),
        ),
        MultilineInput(
            name="user_message",
            display_name="User Message",
            info="User message to pass to the run.",
        ),
        MultilineInput(
            name="thread_id",
            display_name="Thread ID",
            required=False,
            info="Thread ID to use with the run. If not provided, a new thread will be created.",
        ),
        MultilineInput(
            name="env_set",
            display_name="Environment Set",
            info="Dummy input to allow chaining with Dotenv Component.",
        ),
    ]

    outputs = [Output(display_name="Assistant Response", name="assistant_response", method="process_inputs")]

    def process_inputs(self) -> Message:
        patch(OpenAI())
        try:
            text = ""

            if self.thread_id is None:
                thread = self.client.beta.threads.create()
                self.thread_id = thread.id

            # add the user message
            self.client.beta.threads.messages.create(thread_id=self.thread_id, role="user", content=self.user_message)

            class EventHandler(AssistantEventHandler):
                def __init__(self):
                    super().__init__()

                def on_exception(self, exception: Exception) -> None:
                    print(f"Exception: {exception}")
                    raise exception

            event_handler = EventHandler()
            with self.client.beta.threads.runs.create_and_stream(
                thread_id=self.thread_id,
                assistant_id=self.assistant_id,
                event_handler=event_handler,
            ) as stream:
                # return stream.text_deltas
                for part in stream.text_deltas:
                    text += part
                    print(part)
            message = Message(text=text)
            return message
        except Exception as e:
            print(e)
            raise Exception(f"Error running assistant: {e}")
