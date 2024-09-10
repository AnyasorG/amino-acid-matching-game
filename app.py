from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
import random
import json

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Amino acid data with one-letter codes
amino_acids = [
    {'name': 'Alanine', 'polarity': 'Nonpolar', 'charge': 'Neutral', 'code': 'A'},
    {'name': 'Arginine', 'polarity': 'Polar', 'charge': 'Positive', 'code': 'R'},
    {'name': 'Asparagine', 'polarity': 'Polar', 'charge': 'Neutral', 'code': 'N'},
    {'name': 'Aspartic acid', 'polarity': 'Polar', 'charge': 'Negative', 'code': 'D'},
    {'name': 'Cysteine', 'polarity': 'Nonpolar', 'charge': 'Neutral', 'code': 'C'},
    {'name': 'Glutamine', 'polarity': 'Polar', 'charge': 'Neutral', 'code': 'Q'},
    {'name': 'Glutamic acid', 'polarity': 'Polar', 'charge': 'Negative', 'code': 'E'},
    {'name': 'Glycine', 'polarity': 'Nonpolar', 'charge': 'Neutral', 'code': 'G'},
    {'name': 'Histidine', 'polarity': 'Polar', 'charge': 'Positive', 'code': 'H'},
    {'name': 'Isoleucine', 'polarity': 'Nonpolar', 'charge': 'Neutral', 'code': 'I'},
    {'name': 'Leucine', 'polarity': 'Nonpolar', 'charge': 'Neutral', 'code': 'L'},
    {'name': 'Lysine', 'polarity': 'Polar', 'charge': 'Positive', 'code': 'K'},
    {'name': 'Methionine', 'polarity': 'Nonpolar', 'charge': 'Neutral', 'code': 'M'},
    {'name': 'Phenylalanine', 'polarity': 'Nonpolar', 'charge': 'Neutral', 'code': 'F'},
    {'name': 'Proline', 'polarity': 'Nonpolar', 'charge': 'Neutral', 'code': 'P'},
    {'name': 'Serine', 'polarity': 'Polar', 'charge': 'Neutral', 'code': 'S'},
    {'name': 'Threonine', 'polarity': 'Polar', 'charge': 'Neutral', 'code': 'T'},
    {'name': 'Tryptophan', 'polarity': 'Nonpolar', 'charge': 'Neutral', 'code': 'W'},
    {'name': 'Tyrosine', 'polarity': 'Polar', 'charge': 'Neutral', 'code': 'Y'},
    {'name': 'Valine', 'polarity': 'Nonpolar', 'charge': 'Neutral', 'code': 'V'}
]

# Hint data
hints = {
    'polarity': [
        "This amino acid prefers to interact with water rather than with oils.",
        "This amino acid's side chain has a strong affinity for water.",
    ],
    'charge': [
        "This amino acid will be attracted to oppositely charged environments.",
        "The side chain of this amino acid is often involved in ionic interactions.",
    ],
    'structure': [
        "This amino acid has a side chain with a ring structure.",
        "This amino acid's side chain contains a unique ring structure.",
    ],
    'functional_group': [
        "This amino acid contains a side chain that can form hydrogen bonds.",
        "Look for an amino acid with a side chain that can participate in hydrogen bonding.",
    ],
    'biological_context': [
        "This amino acid is often found in the active sites of enzymes where it helps stabilize the structure.",
        "This amino acid plays a crucial role in enzyme function and stability.",
    ],
}

# Connect to SQLite database
def connect_db():
    return sqlite3.connect('amino_game.db')

# Initialize the database
def init_db():
    with connect_db() as db:
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                score INTEGER DEFAULT 0,
                streak INTEGER DEFAULT 0,
                difficulty TEXT DEFAULT 'easy'
            )
        ''')
        db.commit()

# Function to get a subtle hint based on hint type
def get_hint(hint_type):
    return random.choice(hints.get(hint_type, []))

# Register route - to create a new user
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with connect_db() as db:
            try:
                db.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
                db.commit()
                return redirect(url_for('login'))  # Redirect to login after successful registration
            except sqlite3.IntegrityError:
                return render_template('register.html', error="Username already taken")

    return render_template('register.html')

# User login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with connect_db() as db:
            user = db.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()

            if user:
                session['user_id'] = user[0]  # Store user_id in session
                session['username'] = username
                session['score'] = user[3]
                session['streak'] = user[4]
                session['difficulty'] = user[5]
                return redirect(url_for('profile'))  # Go to profile page after login
            else:
                return render_template('login.html', error="Invalid credentials")
    
    return render_template('login.html')


# User profile route
@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redirect to login if user is not logged in
    
    with connect_db() as db:
        user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
        if user:
            return render_template('profile.html', user=user)
        else:
            return redirect(url_for('login'))  # Redirect to login if user is not found

# Set difficulty level route
@app.route('/set_difficulty', methods=['POST'])
def set_difficulty():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    difficulty = request.form['difficulty']
    with connect_db() as db:
        db.execute('UPDATE users SET difficulty = ? WHERE id = ?', (difficulty, session['user_id']))
        db.commit()
    
    session['difficulty'] = difficulty  # Update session with the new difficulty level
    return redirect(url_for('profile'))

# Game start route
@app.route("/", methods=["GET", "POST"])
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    achievements = []
    leaderboard = []

    if request.method == "POST":
        if "start" in request.form:
            started = True

            # Randomly select an amino acid and create choices
            correct_acid = random.choice(amino_acids)
            incorrect_options = [acid for acid in amino_acids if acid['name'] != correct_acid['name']]
            incorrect_choices = random.sample(incorrect_options, 3)
            options = incorrect_choices + [correct_acid]
            random.shuffle(options)

            # Build the correct amino acid image path
            correct_acid_image = f'images/{correct_acid["name"]}.png'

            return render_template('index.html',
                                   correct_acid=correct_acid,
                                   correct_acid_image=correct_acid_image,  # Pass the image path
                                   options=options,
                                   started=started,
                                   score=session.get('score', 0),
                                   streak=session.get('streak', 0),
                                   difficulty=session.get('difficulty', 'easy'),
                                   options_json=json.dumps(options),
                                   correct=None,  # No answer submitted yet
                                   hint=None,
                                   error_message=None,
                                   reward_message=None,
                                   achievements=achievements,
                                   leaderboard=leaderboard)

        elif "submit" in request.form:
            correct_acid = {
                'name': request.form.get("correct_name"),
                'polarity': request.form.get("correct_polarity"),
                'charge': request.form.get("correct_charge"),
                'code': request.form.get("correct_code")
            }
            options = json.loads(request.form.get("options_json"))
            correct_acid_image = f'images/{correct_acid["name"]}.png'  # Add the image path

            # Check if the user has selected an option
            user_choice = request.form.get("choice")
            if user_choice is None:
                return render_template('index.html',
                                       correct_acid=correct_acid,
                                       correct_acid_image=correct_acid_image,  # Pass the image path
                                       options=options,
                                       started=True,
                                       score=session.get('score', 0),
                                       streak=session.get('streak', 0),
                                       difficulty=session.get('difficulty', 'easy'),
                                       options_json=json.dumps(options),
                                       correct=None,
                                       hint=None,
                                       error_message="Please select an option before submitting!",
                                       reward_message=None,
                                       achievements=achievements,
                                       leaderboard=leaderboard)

            # Convert user choice to integer
            user_choice = int(user_choice)
            selected_acid = options[user_choice]

            # Check if the user's choice is correct
            correct = selected_acid['name'] == correct_acid['name']

            # Update score and streak
            if correct:
                session['score'] = session.get('score', 0) + 1
                session['streak'] = session.get('streak', 0) + 1
                if session.get('streak') == 5 and "First Streak" not in achievements:
                    achievements.append("First Streak")
                elif session.get('streak') == 10 and "Amino Acid Master" not in achievements:
                    achievements.append("Amino Acid Master")
                leaderboard.append({'score': session.get('score'), 'streak': session.get('streak')})
            else:
                session['streak'] = 0  # Reset streak

            return render_template('index.html',
                                   correct_acid=correct_acid,
                                   correct_acid_image=correct_acid_image,  # Pass the image path
                                   options=options,
                                   correct=correct,
                                   started=True,
                                   score=session.get('score', 0),
                                   streak=session.get('streak', 0),
                                   difficulty=session.get('difficulty', 'easy'),
                                   options_json=json.dumps(options),
                                   hint=None,
                                   error_message=None,
                                   reward_message=None,
                                   achievements=achievements,
                                   leaderboard=leaderboard)

        elif "hint" in request.form:
            correct_acid = {
                'name': request.form.get("correct_name"),
                'polarity': request.form.get("correct_polarity"),
                'charge': request.form.get("correct_charge"),
                'code': request.form.get("correct_code")
            }
            options = json.loads(request.form.get("options_json"))
            correct_acid_image = f'images/{correct_acid["name"]}.png'  # Add the image path

            difficulty = session.get('difficulty', 'easy')
            hint_type = random.choice(['polarity', 'charge', 'structure', 'functional_group', 'biological_context'])

            # Provide a hint based on hint type
            hint = get_hint(hint_type)

            return render_template('index.html',
                                   correct_acid=correct_acid,
                                   correct_acid_image=correct_acid_image,  # Pass the image path
                                   options=options,
                                   started=True,
                                   score=session.get('score', 0),
                                   streak=session.get('streak', 0),
                                   difficulty=session.get('difficulty', 'easy'),
                                   options_json=json.dumps(options),
                                   correct=None,
                                   hint=hint,
                                   error_message=None,
                                   reward_message=None,
                                   achievements=achievements,
                                   leaderboard=leaderboard)

        elif "refresh" in request.form:
            session['score'] = 0
            session['streak'] = 0
            correct_acid = random.choice(amino_acids)
            incorrect_options = [acid for acid in amino_acids if acid['name'] != correct_acid['name']]
            incorrect_choices = random.sample(incorrect_options, 3)
            options = incorrect_choices + [correct_acid]
            random.shuffle(options)
            correct_acid_image = f'images/{correct_acid["name"]}.png'  # Add the image path

            return render_template('index.html',
                                   correct_acid=correct_acid,
                                   correct_acid_image=correct_acid_image,  # Pass the image path
                                   options=options,
                                   started=True,
                                   score=session.get('score', 0),
                                   streak=session.get('streak', 0),
                                   difficulty=session.get('difficulty', 'easy'),
                                   options_json=json.dumps(options),
                                   correct=None,
                                   hint=None,
                                   error_message=None,
                                   reward_message=None,
                                   achievements=achievements,
                                   leaderboard=leaderboard)

    return render_template('index.html',
                           started=False,
                           score=session.get('score', 0),
                           streak=session.get('streak', 0),
                           difficulty=session.get('difficulty', 'easy'),
                           achievements=achievements,
                           leaderboard=leaderboard)

# User logout route
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('score', None)
    session.pop('streak', None)
    session.pop('difficulty', None)
    return redirect(url_for('login'))

# Initialize the database and run the app
if __name__ == "__main__":
    init_db()  # Ensure the database is initialized
    app.run(debug=True)
