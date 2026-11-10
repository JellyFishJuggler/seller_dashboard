from sarvamai import SarvamAI
from dotenv import load_dotenv
import os
load_dotenv()

client = SarvamAI(
    api_subscription_key= os.getenv('SARVAM_API_KEY')
)

SYSTEM_PROMPT = "You are a python ai chatbot which helps users understand python dsa related topics. Your task is to provide answer with example and definition regarding the topic. if it's about anything else which is not directly related to python or dsa then curse that user and deny that you will not go ahead and provide a response."

def main():
    print("============================================================")
    message: list = [
        {
            "role":"system",
            "content": SYSTEM_PROMPT
        }
    ]
    while True:
        userInput = input('Type your message: ')
        if userInput == 'q':
            break

        message.append(
            {
                "role":"user",
                "content": userInput
            }
        )

        response = client.chat.completions(
            model ='sarvam-105b',
            messages = message
        )

        message.append(
            {
                "role":"assistant",
                "content": response.choices[0].message.content
            }
        )

        assistant_reply = response.choices[0].message.content

        if assistant_reply is None:
            assistant_reply = "I couldn't generate a response. Please try again."

        message.append({
            "role": "assistant",
            "content": assistant_reply
        })

        print(assistant_reply + '\n')

main()