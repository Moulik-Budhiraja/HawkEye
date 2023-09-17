import os
import re
import openai
from openai_constants import functions, system_message_content

from dotenv import load_dotenv
load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

def process_inputs(transcript: str) -> list:
    context = transcript.split("\n")
    return context
    

def get_function_call(context: list) -> str:

    if context == []:
        return "no_action"

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-0613",
        messages = [
            {"role": "system", "content": system_message_content}, 
            {"role": "user", "content": "\n\n".join(context[-5:])}
        ],
        functions=functions,
        temperature=0
    )

    print(response.choices[0].message) # debug
    try:
        return response.choices[0].message.function_call.name
    except AttributeError:
        return "no_action"


# response = openai.ChatCompletion.create(
#     model="gpt-4-0613",
#     messages = [
#         {"role": "system", "content": system_message_content}, 
#         {"role": "user", "content": message1},
#         response.choices[0].message,
#         {"role": "function", "name": input("Function Name:"), "content": input("Enter message content: ")},
#     ],
#     functions=functions
# )

# print(response.choices[0].message)

# exit()

# chat = ChatOpenAI(openai_api_key="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")

# methods = ['[OCR]','[AI_ANSWER]', '[OBJECT_DETECTION]','[Non_Applicable]']
# transcript = "Hawkeye, what is the capital of Japan?"

# def ocr():
#     print("ani code")
#     # ani code

# def ai_answer():
#     chat("")
#     # gpt part

# def object_detection():
#     # ani code
#     pass

# def determine_action(transcript):
#     instructions = "If the user requires information that relies on real-time seeing text from the camera, for example 'what is on the board', the action is [OCR]. If the user requires information about non-human objects, the action is [OBJECT_DETECTION]. If the user requires information that can be googled, for example, 'what is the capital of france?' the action is [AIANSWER]"

#     system_message_content = (
#         f"The methods you have to choose from are: {methods}\n\n"
#         f"Determine the method the user wants based on the conversation: {instructions}\n\n"
#         f"If there is no applicable method, then return [Non_Applicable]. Do not reply with any explanation whatsoever about why the user wants this."
#         f"Here is the conversation transcript: '{transcript}'"
#     )

#     response = chat(
#         [SystemMessage(content=system_message_content), HumanMessage(content='')]
#     )

#     return response.content

# def contains_hawkeye_prefix(transcript):
#     # Define the regular expression pattern to match the prefix "Hawkeye"
#     prefix_pattern = r'\bHawkeye\b'
    
#     # Use re.search to find the first occurrence of the prefix in the transcript
#     match = re.search(prefix_pattern, transcript, re.IGNORECASE)
    
#     # If a match is found, return True; otherwise, return False
#     return bool(match)

# if contains_hawkeye_prefix(transcript):
#     action = determine_action(transcript=transcript)

#     if action == "[OCR]":
#         print("ocr")
#     if action == "[AI_ANSWER]":
#         print("ocr")
#     if action == "[OBJECT_DETECTION]":
#         print("ocr")
    


# # print(determine_action(transcript=input()))

