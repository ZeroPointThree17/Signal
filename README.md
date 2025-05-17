# AI Phone Assistant

A simple AI phone assistant that uses OpenAI's GPT-4 to handle phone conversations. Users can call a dedicated phone number to have natural conversations with an AI assistant.

## Features

- Phone-based AI conversation using OpenAI's GPT-4
- Natural voice interaction
- Conversation history tracking for context
- Simple web interface displaying the phone number
- Secure call handling with Twilio

## Prerequisites

- Python 3.8 or higher
- Twilio account with a phone number
- OpenAI API key

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd <repository-name>
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file:
```bash
cp .env.template .env
```

5. Update the `.env` file with your credentials:
- `FLASK_SECRET_KEY`: Generate a secure random key
- `OPENAI_API_KEY`: Your OpenAI API key
- `TWILIO_ACCOUNT_SID`: Your Twilio account SID
- `TWILIO_AUTH_TOKEN`: Your Twilio auth token
- `TWILIO_PHONE_NUMBER`: Your Twilio phone number (format: +1234567890)

## Running the Application

1. Start the Flask application:
```bash
python app.py
```

2. Access the web interface:
- Open your browser and go to `http://localhost:5000`
- You'll see the phone number to call

3. Make a call:
- Call the displayed phone number
- The AI assistant will answer and engage in conversation
- Speak naturally and the AI will respond
- The conversation will maintain context throughout the call

## How It Works

1. When a user calls the Twilio phone number, the call is routed to the Flask application
2. The application uses OpenAI's GPT-4 to process speech input and generate responses
3. Conversation history is maintained during the call for context
4. The AI responds using natural language, optimized for voice conversation
5. The call continues until the user hangs up

## Security Notes

- All API keys and credentials are stored in the `.env` file
- The `.env` file should never be committed to version control
- Calls are handled securely through Twilio's infrastructure
- Conversation history is maintained only during active calls

## Support

For issues or questions, please open an issue in the repository. 