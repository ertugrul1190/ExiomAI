import os
from groq import Groq


class AIProvider:
    def __init__(self):
        self.groq_client = Groq(
            api_key=os.getenv("GROQ_API_KEY")
        )

        self.primary_model = "openai/gpt-oss-20b"


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

        response = self.groq_client.chat.completions.create(
            model=self.primary_model,
            messages=messages
        )

        return {
            "answer": response.choices[0].message.content,
            "provider": "groq",
            "model": self.primary_model
        }