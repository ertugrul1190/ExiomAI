import os
import re
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

from reliability import (
    MIN_ATTEMPT_SECONDS,
    Deadline,
    env_float,
    env_int,
    retry_delay,
)

from token_budget import trim_conversation
from usage_control import CostMeter
from security import redact_secrets


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


# A searched answer reasons over the pages it read before it
# writes, so it needs more room under the same ceiling.
SEARCH_MAX_OUTPUT_TOKENS = 2400


# ---------------------------------------------------------
# WEB SEARCH
# ---------------------------------------------------------
#
# The provider's built-in web_search tool, used only when the
# router flags a relevant question as needing current
# information nothing else supplies (price, listings, latest
# release, announcements). See "Task Docs/Task 15 - Web
# Search and Usage Page.md".
#
# Searches are restricted to these domains (subdomains
# included): XEQMLabs' own sites, its code, and the price
# trackers and exchanges that list XEQM. Overridable with a
# comma-separated EXIOM_WEB_SEARCH_DOMAINS; EXIOM_WEB_SEARCH=0
# switches search off.
# ---------------------------------------------------------

DEFAULT_WEB_SEARCH_DOMAINS = (
    "xeqmlabs.com",
    "github.com",
    "coingecko.com",
    "coinmarketcap.com",
    "livecoinwatch.com",
    "coinpaprika.com",
    "nonkyc.io",
    "mexc.com",
    "lbank.com",
)

# The API accepts at most this many allowed domains.
MAX_WEB_SEARCH_DOMAINS = 100

DOMAIN_PATTERN = re.compile(
    r"^(?=.{4,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$"
)


def parse_search_domains(configured):
    """
    Bare, valid, unique host names from a comma-separated
    list, or the defaults when none survive. The API wants
    "example.com", never "https://example.com/".
    """

    domains = []

    for part in (configured or "").split(","):

        domain = re.sub(r"^[a-z]+://", "", part.strip().lower())
        domain = domain.split("/", 1)[0]

        if DOMAIN_PATTERN.match(domain) and domain not in domains:
            domains.append(domain)

    return (
        domains[:MAX_WEB_SEARCH_DOMAINS]
        or list(DEFAULT_WEB_SEARCH_DOMAINS)
    )


WEB_SEARCH_DOMAINS = parse_search_domains(
    os.getenv("EXIOM_WEB_SEARCH_DOMAINS", "")
)


def answer_output_ceiling(web_search):
    return (
        SEARCH_MAX_OUTPUT_TOKENS
        if web_search else MAIN_MAX_OUTPUT_TOKENS
    )


def count_web_searches(response):
    """
    The web_search_call items in a response's output.
    """

    try:
        return sum(
            1
            for item in (getattr(response, "output", None) or [])
            if getattr(item, "type", None) == "web_search_call"
        )

    except TypeError:
        return 0


# Router context. The router decides how to handle the
# LATEST message; it needs just enough history to resolve a
# follow-up such as "and the other one?".
ROUTER_HISTORY_MESSAGES = 2
ROUTER_HISTORY_CHARS = 240


# ---------------------------------------------------------
# TIMEOUTS
# ---------------------------------------------------------
#
# "read" is the longest silence tolerated from the provider
# in one attempt: the whole reply for a normal call, the gap
# between events for a stream. "deadline" is the window in
# which attempts may start: no retry begins that could not
# finish inside it. A stream already delivering text is not
# cut off; its output-token ceiling bounds it.
#
# The router fails fastest because a failed route is never
# fatal: the pipeline falls back to a default route and still
# answers.
#
# All of them are overridable without a code change.
# ---------------------------------------------------------

CONNECT_TIMEOUT = env_float("EXIOM_OPENAI_CONNECT_TIMEOUT", 5.0)

CALL_LIMITS = {
    "router": {
        "read": env_float("EXIOM_ROUTER_TIMEOUT", 10.0),
        "deadline": env_float("EXIOM_ROUTER_DEADLINE", 15.0),
    },
    "answer": {
        "read": env_float("EXIOM_ANSWER_TIMEOUT", 45.0),
        "deadline": env_float("EXIOM_ANSWER_DEADLINE", 60.0),
    },
    "off_topic": {
        "read": env_float("EXIOM_OFF_TOPIC_TIMEOUT", 15.0),
        "deadline": env_float("EXIOM_OFF_TOPIC_DEADLINE", 20.0),
    },
}

# Attempts per call, the first one included.
MAX_ATTEMPTS = env_int("EXIOM_OPENAI_MAX_ATTEMPTS", 2)


# What follows a recoverable failure (see _recover).
RESEND = "resend"
RETRY = "retry"


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

        # Every call passes its own timeout; this default only
        # guards a call that somehow does not.
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            timeout=CALL_LIMITS["answer"]["read"],
            max_retries=0,
        )

        self.primary_model = "gpt-5-nano"

        # We control retries ourselves (see reliability.py) so
        # behavior is predictable and bounded.
        self.max_attempts = MAX_ATTEMPTS

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

        # Off when configured off, or once the provider has
        # rejected the tool (see _drop_unsupported_option).
        self.web_search_enabled = (
            os.getenv("EXIOM_WEB_SEARCH", "1") != "0"
        )

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


    @property
    def last_web_searches(self):
        """
        Web searches run by this thread's most recent call.
        """

        return getattr(self._thread_state, "web_searches", 0)


    # -----------------------------------------------------
    # REQUEST BUILDING
    # -----------------------------------------------------

    def _build_request(
        self,
        messages,
        max_output_tokens,
        reasoning_effort,
        json_output,
        web_search=False
    ):

        # store=False: the Responses API otherwise keeps every
        # response (question included) retrievable for 30 days.
        # Nothing here reads a stored response back; each call
        # sends its own context. Not a cost control, so never
        # dropped.
        request = {
            "model": self.primary_model,
            "input": messages,
            "store": False,
        }

        if max_output_tokens:
            request["max_output_tokens"] = max_output_tokens

        if web_search and self.web_search_enabled:

            request["tools"] = [{
                "type": "web_search",
                "filters": {"allowed_domains": WEB_SEARCH_DOMAINS},
                # A price or a release number needs a snippet,
                # not whole pages: fewer tokens read.
                "search_context_size": "low",
            }]

            # The router already decided a search is needed;
            # an answer from memory would be stale.
            request["tool_choice"] = "required"

            # Web search does not run with minimal reasoning.
            if reasoning_effort == "minimal":
                reasoning_effort = "low"

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

        # Checked first: losing search costs one answer its
        # current information, never the answer itself.
        if "tools" in request and any(
            name in names
            for name in ("web_search", "tool_choice", "tools")
        ):

            print(
                "EXIOM web search disabled: the web_search tool "
                "is not supported by this model."
            )

            self.web_search_enabled = False
            return True

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

    def _log_failure(self, error):

        if isinstance(error, RateLimitError):
            print("OpenAI rate limit:", redact_secrets(error))

        elif isinstance(error, APITimeoutError):
            print("OpenAI timeout:", redact_secrets(error))

        elif isinstance(error, APIConnectionError):
            print("OpenAI connection error:", redact_secrets(error))

        else:
            print("OpenAI API status error:", error.status_code)


    def _recover(self, error, request, attempt, deadline):
        """
        Decide what follows a failed attempt.

        Returns RESEND to send again at once without using
        up an attempt (a rejected cost control was dropped;
        each can only be dropped once, so this is bounded),
        or RETRY after waiting out the backoff. Raises the
        error when it is final.
        """

        self._log_failure(error)

        if (
            isinstance(error, APIStatusError)
            and 400 <= error.status_code < 500
            and error.status_code != 429
            and self._drop_unsupported_option(error, request)
        ):

            if deadline.remaining() <= MIN_ATTEMPT_SECONDS:
                raise error

            return RESEND

        delay = retry_delay(error, attempt)

        if (
            delay is None
            or attempt >= self.max_attempts - 1
            or not deadline.allows(delay)
        ):
            raise error

        time.sleep(delay)

        return RETRY


    def _create_response(
        self,
        messages,
        route="unknown",
        max_output_tokens=None,
        reasoning_effort=None,
        json_output=False,
        web_search=False
    ):

        """
        Central place for all OpenAI requests.

        Handles:
        - rate limits
        - temporary server errors
        - connection failures
        - timeouts
        - unsupported cost-control options

        Retries follow reliability.py and never start after
        the route's deadline. Every successful call is metered.
        """

        limits = CALL_LIMITS.get(route, CALL_LIMITS["answer"])
        deadline = Deadline(limits["deadline"])

        attempt = 0

        # A stale reading must never be charged to a later
        # request that failed or was served from cache.
        self._thread_state.usage = None
        self._thread_state.web_searches = 0

        while True:

            request = self._build_request(
                messages,
                max_output_tokens,
                reasoning_effort,
                json_output,
                web_search
            )

            try:

                response = self.client.responses.create(
                    **request,
                    timeout=deadline.attempt_timeout(
                        CONNECT_TIMEOUT,
                        limits["read"]
                    )
                )

                self._meter(response, route)

                return response

            except (APIStatusError, APIConnectionError) as error:

                if self._recover(
                    error,
                    request,
                    attempt,
                    deadline
                ) == RETRY:
                    attempt += 1


    def _meter(self, response, route):
        """
        Record a completed response's tokens and searches.
        """

        self._thread_state.usage = self.cost_meter.record_usage(
            self.primary_model,
            getattr(response, "usage", None),
            route
        )

        searches = count_web_searches(response)

        self._thread_state.web_searches = searches
        self.cost_meter.record_web_searches(searches, route)


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
        question,
        web_search=False
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
            max_output_tokens=answer_output_ceiling(web_search),
            reasoning_effort=MAIN_REASONING_EFFORT,
            web_search=web_search
        )

        return {
            "answer": response.output_text,
            "provider": "openai",
            "model": self.primary_model,
            "searched": self.last_web_searches > 0
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


    # -----------------------------------------------------
    # SAFE OPENAI STREAM
    # -----------------------------------------------------

    def _stream_response(
        self,
        messages,
        route="unknown",
        max_output_tokens=None,
        reasoning_effort=None,
        web_search=False
    ):

        """
        Streaming twin of _create_response.

        Yields text deltas as they arrive, then meters the
        completed response exactly like a normal call.

        Retries follow the same rules as _create_response
        with one addition: once a delta has been handed to
        the caller the answer is already partly on screen,
        so retrying would duplicate text. After the first
        delta every failure is final.
        """

        limits = CALL_LIMITS.get(route, CALL_LIMITS["answer"])
        deadline = Deadline(limits["deadline"])

        attempt = 0

        # A stale reading must never be charged to a later
        # request that failed or was served from cache.
        self._thread_state.usage = None
        self._thread_state.web_searches = 0

        while True:

            request = self._build_request(
                messages,
                max_output_tokens,
                reasoning_effort,
                json_output=False,
                web_search=web_search
            )

            # Nothing has reached the caller yet, so this
            # attempt is still safe to abandon.
            started = False

            try:

                with self.client.responses.stream(
                    **request,
                    timeout=deadline.attempt_timeout(
                        CONNECT_TIMEOUT,
                        limits["read"]
                    )
                ) as stream:

                    for event in stream:

                        if getattr(
                            event,
                            "type",
                            ""
                        ) != "response.output_text.delta":
                            continue

                        delta = getattr(event, "delta", "")

                        if delta:
                            started = True
                            yield delta

                    final = stream.get_final_response()

                self._meter(final, route)

                return

            except (APIStatusError, APIConnectionError) as error:

                # Text already on screen can never be replayed.
                if started:
                    self._log_failure(error)
                    raise

                if self._recover(
                    error,
                    request,
                    attempt,
                    deadline
                ) == RETRY:
                    attempt += 1


    # -----------------------------------------------------
    # STREAMED EXIOM AI RESPONSE
    # -----------------------------------------------------

    def stream_generate(
        self,
        system_prompt,
        conversation,
        question,
        web_search=False
    ):

        """
        Streaming twin of generate().
        """

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

        return self._stream_response(
            messages,
            route="answer",
            max_output_tokens=answer_output_ceiling(web_search),
            reasoning_effort=MAIN_REASONING_EFFORT,
            web_search=web_search
        )


    # -----------------------------------------------------
    # STREAMED OFF-TOPIC PERSONALITY
    # -----------------------------------------------------

    def stream_generate_off_topic(
        self,
        conversation,
        question
    ):

        """
        Streaming twin of generate_off_topic().
        """

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

        return self._stream_response(
            messages,
            route="off_topic",
            max_output_tokens=OFF_TOPIC_MAX_OUTPUT_TOKENS,
            reasoning_effort=OFF_TOPIC_REASONING_EFFORT
        )
