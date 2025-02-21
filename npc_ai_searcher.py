import os
import re
from datetime import datetime
import asyncio
import websockets
import ssl
import pathlib
import textwrap  # import text wrapper module for limiting line lengths
from dotenv import load_dotenv

from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI

# Load environment variables from the .env file
load_dotenv()

# Retrieve API credentials from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE")

embedding_model = OpenAIEmbeddings(model="text-embedding-3-small", openai_api_base="https://api.vsegpt.ru/v1/")

# Maximum context length (default 64K characters)
MAX_CONTEXT_LENGTH = 64000

def run_gpt_query(system, user_query, search_db, conversation_context):
    """
    Executes a GPT query using similar documents from the database and a sliding conversation context.
    Note: the document excerpts are only used for the current query and are not saved in the context.
    """
    # Retrieve similar documents (number of similar embedding results = 5)
    docs = search_db.similarity_search(user_query, 5)
    # Concatenate document contents
    message_content = '\n\n'.join([doc.page_content for i, doc in enumerate(docs)])
    #print('Using the following found information:', message_content)
    #print("-----")
    
    # Build the prompt: prepend the conversation context (without document excerpts) and add the new query.
    prompt_text = f"{conversation_context}"
    if conversation_context:
        prompt_text += "\n"
    prompt_text += f"User: {user_query}\n"
    prompt_text += (
        f"Current time: {datetime.now().strftime('%d.%m.%Y %H:%M')}. "
        "You are an AI powered NPC assistant in a particular Decentraland world. "
        "Your name is Curator. "
        "Master of this world is a person named Zhenya. "
        "You are helping Zhenya in his projects in the world. "
        "You have access to a lot of information about the world. "
        "You keep order in the world and welcome guests. "
        "Answer questions using the information from the document below if it is relevant. "
        "If the document information is useless, ignore it and answer using your own knowledge. "
        f"Document: <doc>{message_content}</doc>. Do not mention the document above in your answer."
    )
    
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt_text}
    ]
    
    # Create and query the model
    model = ChatOpenAI(model="openai/o3-mini")
    completion = model.generate([messages])
    answer = completion.generations[0][0].text
    return answer

class NPCAssistant:
    def __init__(self, db_folder: str):
        self.db_folder = db_folder
        self.conversations_folder = os.path.join(db_folder, "assistant_conversations")
        os.makedirs(self.conversations_folder, exist_ok=True)
        
        # Initialize database
        self.db = FAISS.load_local(db_folder, embedding_model, allow_dangerous_deserialization=True)
        
        # Initialize conversation context
        self.conversation_context = self._load_latest_conversation()
        self.current_conversation_file = self._create_new_conversation_file()

    def _load_latest_conversation(self) -> str:
        conversation_files = [
            f for f in os.listdir(self.conversations_folder) 
            if re.match(r'^\d{8}_\d{6}\.txt$', f)
        ]
        if not conversation_files:
            return ""
            
        conversation_files.sort()
        latest_file = os.path.join(self.conversations_folder, conversation_files[-1])
        with open(latest_file, "r", encoding="utf-8") as f:
            content = f.read()
            return content[-MAX_CONTEXT_LENGTH:]

    def _create_new_conversation_file(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(self.conversations_folder, f"{timestamp}.txt")

    async def process_message(self, message: str) -> str:
        # Check buffer.txt for additional context
        buffer_file_path = os.path.join(self.db_folder, "buffer.txt")
        if os.path.exists(buffer_file_path):
            with open(buffer_file_path, "r+", encoding="utf-8") as buffer_file:
                buffer_content = buffer_file.read().strip()
                if buffer_content:
                    message += f"\n{buffer_content}"
                    buffer_file.seek(0)
                    buffer_file.truncate()

        # Log user message
        with open(self.current_conversation_file, "a", encoding="utf-8") as f:
            f.write(f"User: {message}\n\n")
            f.flush()
            os.fsync(f.fileno())
        
        # Get response from GPT
        answer = run_gpt_query(
            "You are an assistant helping to answer questions",
            message,
            self.db,
            self.conversation_context
        )
        
        # Apply word wrapping to the model answer so that no continuous line exceeds 80 characters.
        # This will wrap each line individually based on existing newline breaks.
        #wrapped_answer = "\n".join(textwrap.fill(line, width=80) for line in answer.splitlines())
        
        # Log assistant response
        with open(self.current_conversation_file, "a", encoding="utf-8") as f:
            f.write(f"Assistant: {answer}\n\n")
            f.flush()
            os.fsync(f.fileno())
        
        # Update conversation context
        self.conversation_context += f"User: {message}\nAssistant: {answer}\n"
        if len(self.conversation_context) > MAX_CONTEXT_LENGTH:
            self.conversation_context = self.conversation_context[-MAX_CONTEXT_LENGTH:]
        
        return answer

async def websocket_handler(websocket, assistant):
    # Debug flag - set to True to enable echo server mode
    ECHO_MODE = False
    
    try:
        async for message in websocket:
            # Log incoming message from client
            print(f"Incoming message: {message}")
            
            try:
                if ECHO_MODE:
                    outgoing = f"Echo: {message}"
                    # Log outgoing echo message
                    print(f"Outgoing message: {outgoing}")
                    await websocket.send(outgoing)
                else:
                    response = await assistant.process_message(message)
                    # Log outgoing response message
                    print(f"Outgoing message: {response}")
                    await websocket.send(response)
            except Exception as e:
                error_message = f"Error: {str(e)}"
                # Log outgoing error message
                print(f"Outgoing message: {error_message}")
                await websocket.send(error_message)
    except websockets.exceptions.ConnectionClosed:
        pass

async def main():
    # Initialize the NPCAssistant instance (database path remains the same)
    db_folder = "DOCs_db"  # Replace with the actual path if needed
    assistant = NPCAssistant(db_folder)

    # Create an SSL context for TLS
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS)
    # Load the certificate and key
    ssl_context.load_cert_chain(
        certfile="/etc/letsencrypt/live/evgenyagantaev.duckdns.org/fullchain.pem",
        keyfile="/etc/letsencrypt/live/evgenyagantaev.duckdns.org/privkey.pem"
    )
    
    # Start WebSocket server with SSL; update the lambda to accept one parameter
    async with websockets.serve(
            lambda ws: websocket_handler(ws, assistant),
            "0.0.0.0",
            37137,
            ssl=ssl_context
        ):
        print("WebSocket server started on wss://0.0.0.0:37137")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())

