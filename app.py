import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather
import openai
from models import db, User, Task
from agent import ProactiveAgent
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')

# Initialize Twilio client
twilio_client = Client(
    os.getenv('TWILIO_ACCOUNT_SID'),
    os.getenv('TWILIO_AUTH_TOKEN')
)
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')

# Initialize AI agent
agent = ProactiveAgent()

# Store conversation history for each call
conversation_history = {}

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    """Show the phone number to call."""
    return render_template('base.html', twilio_phone_number=TWILIO_PHONE_NUMBER)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        phone_number = request.form.get('phone_number')

        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))

        user = User(username=username, email=email, phone_number=phone_number)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        return redirect(url_for('dashboard'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))

        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    tasks = Task.query.filter_by(user_id=current_user.id).order_by(Task.created_at.desc()).all()
    return render_template('dashboard.html', tasks=tasks)

@app.route('/tasks', methods=['POST'])
@login_required
def create_task():
    data = request.json
    task = Task(
        title=data['title'],
        description=data['description'],
        priority=data.get('priority', 'medium'),
        due_date=datetime.fromisoformat(data['due_date']) if data.get('due_date') else None,
        task_type=data.get('task_type', 'chat'),
        user_id=current_user.id
    )
    db.session.add(task)
    db.session.commit()

    # Process task with AI
    response = agent.process_input(task.description)
    task.ai_response = response
    task.status = 'completed'
    db.session.commit()

    return jsonify(task.to_dict())

@app.route('/tasks/<int:task_id>', methods=['PUT'])
@login_required
def update_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.json
    for key, value in data.items():
        if hasattr(task, key):
            setattr(task, key, value)
    
    db.session.commit()
    return jsonify(task.to_dict())

@app.route('/tasks/<int:task_id>', methods=['DELETE'])
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    db.session.delete(task)
    db.session.commit()
    return jsonify({'message': 'Task deleted'})

@app.route('/call', methods=['POST'])
@login_required
def initiate_call():
    """Initiate a call to the user's phone number."""
    try:
        call = twilio_client.calls.create(
            to=current_user.phone_number,
            from_=TWILIO_PHONE_NUMBER,
            url=url_for('handle_call', _external=True)
        )
        return jsonify({'message': 'Call initiated', 'call_sid': call.sid})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/handle-call', methods=['POST'])
def handle_call():
    """Handle incoming calls."""
    response = VoiceResponse()
    
    # Get the call SID for conversation tracking
    call_sid = request.values.get('CallSid')
    
    # If this is the start of the call
    if request.values.get('SpeechResult') is None:
        gather = Gather(
            input='speech',
            action=url_for('handle_call', _external=True),
            method='POST',
            speech_timeout='auto',
            language='en-US'
        )
        gather.say('Hello! I am your AI assistant. How can I help you today?')
        response.append(gather)
    else:
        # Process the speech input
        speech_input = request.values.get('SpeechResult', '')
        ai_response = get_ai_response(speech_input, call_sid)
        
        # Create a new gather for the next interaction
        gather = Gather(
            input='speech',
            action=url_for('handle_call', _external=True),
            method='POST',
            speech_timeout='auto',
            language='en-US'
        )
        gather.say(ai_response)
        response.append(gather)
    
    return str(response)

@app.route('/end-call', methods=['POST'])
def end_call():
    """Clean up when call ends."""
    call_sid = request.values.get('CallSid')
    if call_sid in conversation_history:
        del conversation_history[call_sid]
    return '', 200

def get_ai_response(speech_input, call_sid):
    """Get response from OpenAI with conversation history."""
    if call_sid not in conversation_history:
        conversation_history[call_sid] = []
    
    # Add user input to history
    conversation_history[call_sid].append({"role": "user", "content": speech_input})
    
    try:
        # Get response from OpenAI
        response = openai.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant on a phone call. Keep your responses concise and natural for voice conversation. Speak in a friendly, conversational tone."},
                *conversation_history[call_sid]
            ],
            max_tokens=150,  # Keep responses brief for phone conversation
            temperature=0.7
        )
        
        ai_message = response.choices[0].message.content
        
        # Add AI response to history
        conversation_history[call_sid].append({"role": "assistant", "content": ai_message})
        
        # Keep only last 5 exchanges to maintain context without using too much memory
        if len(conversation_history[call_sid]) > 10:
            conversation_history[call_sid] = conversation_history[call_sid][-10:]
        
        return ai_message
    except Exception as e:
        print(f"Error getting AI response: {str(e)}")
        return "I apologize, but I'm having trouble processing that right now. Could you please try again?"

if __name__ == '__main__':
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
    app.run(debug=True) 