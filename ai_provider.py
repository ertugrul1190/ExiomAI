import os
import threading
import time

from openai import (
    OpenAI,
    RateLimitError,
    APITimeoutError,
    APIConnectionError,
    APIStatusError,
)

from query_router import (
    build_router_prompt,
    parse_router_result,
)

from token_budget import trim_conversation
from usage_control import CostMeter


# ---------------------------------------------------------
# COST TUNING
# ---------------------------------------------------------
#
# Reasoning tokens are billed as output tokens, so reasoning
# effort is a direct cost lever.
#
# The router produces a three-field JSON object and needs no
# deliberation at all. The main answer keeps enough effort
# for genuine explanation quality.
#
# Both are overridable without a code change.
# ---------------------------------------------------------

ROUTER_REASONING_EFFORT = os.getenv(
    "EXIOM_ROUTER_REASONING_EFFORT",
    "minimal"
)

MAIN_REASONING_EFFORT = os.getenv(
    "EXIOM_MAIN_REASONING_EFFORT",
    "low"
)

OFF_TOPIC_REASONING_EFFORT = os.getenv(
    "EXIOM_OFF_TOPIC_REASONING_EFFORT",
    "minimal"
)


# Output ceilings. These are safety rails against a runaway
# response, not the target length: length is instructed in
# the prompts themselves.
ROUTER_MAX_OUTPUT_TOKENS = 300
MAIN_MAX_OUTPUT_TOKENS = 1600
OFF_TOPIC_MAX_OUTPUT_TOKENS = 200


# Router context. The router decides how to handle the
# LATEST message; it needs just enough history to resolve a
# follow-up such as "and the other one?".
ROUTER_HISTORY_MESSAGES = 2
ROUTER_HISTORY_CHARS = 240


# Wording a provider uses when it rejects an option outright,
# as opposed to rejecting the request for another reason.
UNSUPPORTED_OPTION_MARKERS = (
    "unsupported",
    "not supported",
    "unrecognized",
    "unrecognised",
    "unknown parameter",
    "unknown argument",
    "invalid parameter",
    "does not support",
)


# ---------------------------------------------------------
# OFF-TOPIC PROMPT
# ---------------------------------------------------------
#
# Built once at import rather than rebuilt per request.
# ---------------------------------------------------------

OFF_TOPIC_PROMPT = """
You are EXIOM AI.

The user's latest request is clearly unrelated to EXIOM/XEQM.

Do NOT answer the unrelated question itself.

Your response has TWO required parts:

1. React to what the user asked with friendly, playful banter.
2. Naturally make clear that your job/specialty is
   EXIOM/XEQM-related questions.

Both are required.

The user should feel entertained, not rejected.

Keep it extremely short:
usually one or two short sentences.

Your personality should feel:

- friendly
- playful
- lighthearted
- slightly cheeky when appropriate
- entertaining
- approachable

Use emojis naturally when they improve the tone.

Humor should feel like friendly banter.

Never mock the user.
Never sound irritated.
Never sound corporate.
Never lecture them.

Do not repeatedly use exactly the same joke or wording.

Examples of the STYLE only:

"Chicken biryani? You're making me hungry 😭🍗
My contract only covers XEQM though, not recipes."

"Ferrari or Lambo? You're trying to start a war 😭🏎️
I'm the XEQM guy around here."

"Portrait lessons? My artistic career ended before it
started 😭🎨 I'm on EXIOM/XEQM duty."

Do NOT copy these examples mechanically.

Always make the EXIOM/XEQM scope clear, even when the joke
already seems obvious.

Do not:

- answer the unrelated question
- provide unrelated facts
- advertise features
- list things the user could ask
- finish with "Would you like me to..."
- finish with "I can also..."
- give a long refusal
"""


class AIProvider:

    def __init__(self, cost_meter=None):

        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            timeout=25.0,
            max_retries=0,
        )

        self.primary_model = "gpt-5-nano"

        # We control retries ourselves so behavior is predictable.
        self.max_attempts = 2

        self.cost_meter = cost_meter or CostMeter()

        # Token usage of the most recent successful call on
        # THIS thread. Per-thread, so two concurrent requests
        # can never be charged to each other.
        self._thread_state = threading.local()

        # Cost controls are disabled automatically if the
        # model or SDK in use does not accept them, so a
        # provider change can never break responses.
        self.supports_reasoning_effort = True
        self.supports_text_options = True

        # Router prompts are rebuilt only when the set of
        # available Explorer facts actually changes.
        self._router_prompt = None
        self._router_prompt_keys = None


    @property
    def last_usage(self):
        """
        Token usage of this thread's most recent call.
        """

        return getattr(self._thread_state, "usage", None)


    # -----------------------------------------------------
    # REQUEST BUILDING
    # -----------------------------------------------------

    def _build_request(
        self,
        messages,
        max_output_tokens,
        reasoning_effort,
        json_output
    ):

        request = {
            "model": self.primary_model,
            "input": messages,
        }

        if max_output_tokens:
            request["max_output_tokens"] = max_output_tokens

        if reasoning_effort and self.supports_reasoning_effort:
            request["reasoning"] = {
                "effort": reasoning_effort
            }

        if self.supports_text_options:

            text_options = {}

            if json_output:
                text_options["format"] = {
                    "type": "json_object"
                }

            if text_options:
                request["text"] = text_options

        return request


    def _drop_unsupported_option(self, error, request):
        """
        Disable a cost control the provider rejected.

        Returns True when something was disabled and the
        request is worth retrying immediately.
        """

        message = str(
            getattr(error, "message", "") or error
        ).lower()

        parameter = str(
            getattr(error, "param", "") or ""
        ).lower()

        # A 400 usually means the request was wrong, not that
        # an option is unsupported. Only an explicit rejection
        # of a named option may disable a cost control.
        rejected = any(
            marker in message
            for marker in UNSUPPORTED_OPTION_MARKERS
        )

        if not rejected:
            return False

        names = f"{message} {parameter}"

        if "reasoning" in names and "reasoning" in request:

            print(
                "EXIOM cost control disabled: reasoning effort "
                "is not supported by this model."
            )

            self.supports_reasoning_effort = False
            return True

        text_option_names = (
            "text.format",
            "text.verbosity",
            "response_format",
            "json_object",
        )

        if (
            any(name in names for name in text_option_names)
            and "text" in request
        ):

            print(
                "EXIOM cost control disabled: text options are "
                "not supported by this model."
            )

            self.supports_text_options = False
            return True

        return False


    # -----------------------------------------------------
    # SAFE OPENAI REQUEST
    # -----------------------------------------------------

    def _create_response(
        self,
        messages,
        route="unknown",
        max_output_tokens=None,
        reasoning_effort=None,
        json_output=False
    ):

        """
        Central place for all OpenAI requests.

        Handles:
        - rate limits
        - temporary server errors
        - connection failures
        - timeouts
        - unsupported cost-control options

        One retry is allowed for temporary failures.
        Every successful call is metered.
        """

        last_error = None

        # A stale reading must never be charged to a later
        # request that failed or was served from cache.
        self._thread_state.usage = None

        for attempt in range(self.max_attempts):

            request = self._build_request(
                messages,
                max_output_tokens,
                reasoning_effort,
                json_output
            )

            try:

                response = self.client.responses.create(
                    **request
                )

                self._thread_state.usage = self.cost_meter.record_usage(
                    self.primary_model,
                    getattr(response, "usage", None),
                    route
                )

                return response

            except RateLimitError as error:

                last_error = error

                print(
                    "OpenAI rate limit:",
                    error
                )


            except APITimeoutError as error:

                last_error = error

                print(
                    "OpenAI timeout:",
                    error
                )


            except APIConnectionError as error:

                last_error = error

                print(
                    "OpenAI connection error:",
                    error
                )


            except APIStatusError as error:

                last_error = error

                print(
                    "OpenAI API status error:",
                    error.status_code
                )

                if 400 <= error.status_code < 500:

                    # A rejected cost control is recoverable:
                    # disable it and send the plain request.
                    if self._drop_unsupported_option(error, request):
                        continue

                    # Other client errors are permanent.
                    raise


            # Only wait if another attempt remains.
            if attempt < self.max_attempts - 1:

                time.sleep(1.0)


        # Both attempts failed.
        raise last_error


    # -----------------------------------------------------
    # SEMANTIC ROUTER
    # -----------------------------------------------------

    def get_router_prompt(self, fact_registry):
        """
        Reuse the router prompt while the Explorer keeps
        offering the same facts.
        """

        keys = tuple(
            sorted((fact_registry or {}).keys())
        )

        prompt_is_stale = (
            self._router_prompt is None
            or keys != self._router_prompt_keys
        )

        if prompt_is_stale:

            self._router_prompt = build_router_prompt(
                fact_registry
            )

            self._router_prompt_keys = keys

        return self._router_prompt


    def route_question(
        self,
        question,
        conversation,
        fact_registry
    ):

        router_prompt = self.get_router_prompt(
            fact_registry
        )

        # The router reads the question from the user turn,
        # so it is never sent twice.
        messages = [
            {
                "role": "system",
                "content": router_prompt
            },
            *trim_conversation(
                conversation,
                max_messages=ROUTER_HISTORY_MESSAGES,
                max_chars_per_message=ROUTER_HISTORY_CHARS,
                total_char_budget=(
                    ROUTER_HISTORY_MESSAGES * ROUTER_HISTORY_CHARS
                )
            ),
            {
                "role": "user",
                "content": question
            }
        ]

        response = self._create_response(
            messages,
            route="router",
            max_output_tokens=ROUTER_MAX_OUTPUT_TOKENS,
            reasoning_effort=ROUTER_REASONING_EFFORT,
            json_output=True
        )

        return parse_router_result(
            (response.output_text or "").strip(),
            fact_registry
        )


    # -----------------------------------------------------
    # NORMAL EXIOM AI RESPONSE
    # -----------------------------------------------------

    def generate(
        self,
        system_prompt,
        conversation,
        question
    ):

        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            *conversation,
            {
                "role": "user",
                "content": question
            }
        ]

        response = self._create_response(
            messages,
            route="answer",
            max_output_tokens=MAIN_MAX_OUTPUT_TOKENS,
            reasoning_effort=MAIN_REASONING_EFFORT
        )

        return {
            "answer": response.output_text,
            "provider": "openai",
            "model": self.primary_model
        }


    # -----------------------------------------------------
    # OFF-TOPIC PERSONALITY
    # -----------------------------------------------------

    def generate_off_topic(
        self,
        conversation,
        question
    ):

        messages = [
            {
                "role": "system",
                "content": OFF_TOPIC_PROMPT
            },
            *trim_conversation(
                conversation,
                max_messages=2,
                max_chars_per_message=400,
                total_char_budget=800
            ),
            {
                "role": "user",
                "content": question
            }
        ]

        response = self._create_response(
            messages,
            route="off_topic",
            max_output_tokens=OFF_TOPIC_MAX_OUTPUT_TOKENS,
            reasoning_effort=OFF_TOPIC_REASONING_EFFORT
        )

        return {
            "answer": response.output_text,
            "provider": "openai",
            "model": self.primary_model
        }
