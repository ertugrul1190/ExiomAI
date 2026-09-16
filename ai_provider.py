import os
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


class AIProvider:

    def __init__(self):

        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            timeout=25.0,
            max_retries=0,
        )

        self.primary_model = "gpt-5-nano"

        # We control retries ourselves so behavior is predictable.
        self.max_attempts = 2


    # -----------------------------------------------------
    # SAFE OPENAI REQUEST
    # -----------------------------------------------------

    def _create_response(self, messages):

        """
        Central place for all OpenAI requests.

        Handles:
        - rate limits
        - temporary server errors
        - connection failures
        - timeouts

        One retry is allowed for temporary failures.
        """

        last_error = None

        for attempt in range(self.max_attempts):

            try:

                return self.client.responses.create(
                    model=self.primary_model,
                    input=messages,
                )

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

                # Don't retry permanent client errors.
                if 400 <= error.status_code < 500:
                    raise


            # Only wait if another attempt remains.
            if attempt < self.max_attempts - 1:

                time.sleep(1.0)


        # Both attempts failed.
        raise last_error


    # -----------------------------------------------------
    # SEMANTIC ROUTER
    # -----------------------------------------------------

    def route_question(
        self,
        question,
        conversation,
        fact_registry
    ):

        router_prompt = build_router_prompt(
            question,
            fact_registry
        )

        messages = [
            {
                "role": "system",
                "content": router_prompt
            },
            *conversation[-6:],
            {
                "role": "user",
                "content": question
            }
        ]

        response = self._create_response(
            messages
        )

        return parse_router_result(
            response.output_text.strip(),
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
            messages
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

        personality_prompt = """
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

        messages = [
            {
                "role": "system",
                "content": personality_prompt
            },
            *conversation[-4:],
            {
                "role": "user",
                "content": question
            }
        ]

        response = self._create_response(
            messages
        )

        return {
            "answer": response.output_text,
            "provider": "openai",
            "model": self.primary_model
        }