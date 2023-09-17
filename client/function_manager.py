import os
import re
import openai
import json
from openai_constants import functions, system_message_content

from dotenv import load_dotenv
load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

def process_inputs(transcript: str) -> list:
    context = transcript.split("\n")
    return context
    

def get_function_call(context: list) -> (str, str):

    if context == []:
        return ("no_action", "")

    response = openai.ChatCompletion.create(
        model="gpt-4-0613",
        messages = [
            {"role": "system", "content": system_message_content}, 
            {"role": "user", "content": "\n\n".join(context[-5:])}
        ],
        functions=functions,
        temperature=0
    )

    print(response.choices[0].message) # debug
    try:
        result =  (response.choices[0].message.function_call.name, context[-1])

        if result[0] == "ai_answer":
            result = ("ai_answer", json.loads(response.choices[0].message.function_call.arguments)["answer"])

        return result

    except AttributeError as e:
        print(e)
        return ("no_action", context[-1])

