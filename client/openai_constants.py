functions = [
    {
        "name": "ocr",
        "description": "Pull text from what the user is seeing to get more context about their question.",
        "parameters":{
            "type":"object",
            "properties": {
                "fast": {
                    "type": "boolean",

                },
            },
        }
    },
    {
        "name": "ai_answer",
        "parameters":
        {
            "type":"object",
            "properties": {
                "answer": {
                    "type": "string",
                    "description": "The answer to the question."
                }
            },
            "required": ["answer"]
        }
    },
    {
        "name": "no_action",
        "description": "Perform a null action when nothing is required.",
        "parameters":{
            "type":"object",
            "properties": {
                "fast": {
                    "type": "boolean",

                },
            },
        }

    }
]

system_message_content = """You are 'Hawkeye', a large language model that always calls the correct method. If you are addressed directly, it likely means that the user wants you to take an action. Thus, you must always respond by calling a function. 
In all other cases, call 'no_action' unless you are addressed by the user as 'Hawkeye' with a query."""