import os
import time
import schedule
import google.generativeai as genai
import openai
from dotenv import load_dotenv
from pushover import Client as PushoverClient

# Load environment variables
load_dotenv()

# Configure APIs
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
openai.api_key = OPENAI_API_KEY
genai.configure(api_key=GOOGLE_API_KEY)

# Configure Pushover
PUSHOVER_USER_KEY = os.getenv('PUSHOVER_USER_KEY')
PUSHOVER_API_TOKEN = os.getenv('PUSHOVER_API_TOKEN')
pushover_client = PushoverClient(PUSHOVER_USER_KEY, api_token=PUSHOVER_API_TOKEN)

class ProactiveAgent:
    def __init__(self):
        # Initialize OpenAI chat
        self.openai_client = openai.OpenAI()
        self.openai_messages = []
        
        # Initialize Gemini Pro for coding/research
        self.gemini_model = genai.GenerativeModel('gemini-pro')
        self.gemini_chat = self.gemini_model.start_chat(history=[])
        
    def is_coding_or_research_task(self, text):
        """Determine if the task is coding or research related."""
        coding_keywords = ['code', 'program', 'function', 'class', 'algorithm', 'debug', 'implement', 
                         'optimize', 'refactor', 'test', 'documentation', 'api', 'database']
        research_keywords = ['research', 'analyze', 'study', 'investigate', 'explore', 'compare', 
                           'evaluate', 'review', 'literature', 'survey', 'data analysis']
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in coding_keywords + research_keywords)
    
    def process_with_openai(self, input_text):
        """Process chat-based input using OpenAI."""
        try:
            self.openai_messages.append({"role": "user", "content": input_text})
            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=self.openai_messages,
                temperature=0.7,
                max_tokens=500
            )
            assistant_message = response.choices[0].message.content
            self.openai_messages.append({"role": "assistant", "content": assistant_message})
            return assistant_message
        except Exception as e:
            return f"Error processing with OpenAI: {str(e)}"

    def process_with_gemini(self, input_text):
        """Process coding/research tasks using Gemini Pro."""
        try:
            response = self.gemini_chat.send_message(input_text)
            return response.text
        except Exception as e:
            return f"Error processing with Gemini: {str(e)}"

    def process_input(self, input_text):
        """Route the input to the appropriate AI model based on the task type."""
        if self.is_coding_or_research_task(input_text):
            return self.process_with_gemini(input_text)
        else:
            return self.process_with_openai(input_text)

    def send_notification(self, message, title="AI Agent Notification"):
        """Send a notification to the user's phone."""
        try:
            pushover_client.send_message(message, title=title)
            print(f"Notification sent: {title} - {message}")
        except Exception as e:
            print(f"Error sending notification: {str(e)}")

    def run_cycle(self):
        """Run one cycle of the agent's operation."""
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Example inputs for both chat and coding/research
        chat_input = f"Current time is {current_time}. What's an interesting conversation starter or thought-provoking question?"
        research_input = f"Current time is {current_time}. Analyze the latest trends in AI development and provide a brief technical summary."
        
        # Process both types of inputs
        chat_response = self.process_with_openai(chat_input)
        research_response = self.process_with_gemini(research_input)
        
        # Send notifications
        self.send_notification(chat_response, title="AI Chat Update")
        self.send_notification(research_response, title="AI Research Update")
        
        print(f"Cycle completed at {current_time}")

def main():
    # Initialize the agent
    agent = ProactiveAgent()
    
    # Schedule the agent to run every hour
    schedule.every(1).hours.do(agent.run_cycle)
    
    # Run immediately on startup
    agent.run_cycle()
    
    print("Agent started. Press Ctrl+C to stop.")
    print("Using OpenAI for chat and Gemini Pro for coding/research tasks.")
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute for scheduled tasks

if __name__ == "__main__":
    # Verify environment variables
    required_vars = ['OPENAI_API_KEY', 'GOOGLE_API_KEY', 'PUSHOVER_USER_KEY', 'PUSHOVER_API_TOKEN']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set them in your .env file")
        exit(1)
        
    main() 