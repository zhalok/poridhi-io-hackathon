import os
import openai
from dotenv import load_dotenv
load_dotenv()

from groq import Groq

client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)




def redefine_query(query):
    chat_completion = client.chat.completions.create(
    messages=[
        {
            "role": "system",
            "content": "You will receive a query and you need to rephrase it as a standard english text, the text can be in bengali or english transliteration of bengali",
        },
        {
            "role": "user",
            "content": query,
        }
    ],
    model="llama-3.3-70b-versatile",
    stream=False,
    )

    return chat_completion.choices[0].message.content
    response = client.responses.create(
    model="gpt-4.1",
    instructions="You will receive a query and you need to rephrase it as a standard english text, the text can be in bengali or english transliteration of bengali",
    input=query
    )

    return response.output_text
