from flask import Flask, render_template, request, session, redirect, url_for
from flask import render_template_string
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import google.generativeai as palm
import markdown
from markdown.extensions.fenced_code import FencedCodeExtension
import re
import os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import openai  # don't go for upgraded version
import json
import requests
from flask_weasyprint import HTML, render_pdf
from weasyprint import CSS
from r_learning import *
from datetime import datetime
from models import db, User, UserProficiency, Course
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from keys import open_ai_key

app = Flask(__name__)
app.config['SECRET_KEY'] = 'alpha-beta'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
# db = SQLAlchemy(app)
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
openai.api_key = open_ai_key

# Create a Markdown instance with the FencedCodeExtension
md = markdown.Markdown(extensions=[FencedCodeExtension()])

with app.app_context():
    db.create_all()




def update_user_proficiency(user_proficiency, performance, quiz_params, sentiment_score):
    """
    Update user proficiency with a controlled, staged progression and consecutive performance tracking.
    
    Args:
        user_proficiency (UserProficiency): User's proficiency model instance
        performance (float): Quiz performance percentage (0-100)
        quiz_params (dict): Quiz parameters including difficulty
        sentiment_score (float): Sentiment score from feedback (-1 to 1)
    """
    # Define progression stages with specific thresholds
    progression_stages = [
        (0, 20),    # Beginner Stage
        (20, 40),   # Basic Understanding Stage
        (40, 60),   # Intermediate Stage
        (60, 80),   # Advanced Intermediate Stage
        (80, 90),   # Advanced Stage
        (90, 100)   # Expert Stage
    ]
    
    # Determine current stage
    current_level = user_proficiency.proficiency_level
    current_stage_index = next(
        (i for i, (low, high) in enumerate(progression_stages) 
         if low <= current_level < high), 
        0
    )
    
    # Difficulty-based adjustment weights
    difficulty_weights = {
        'easy': 2,
        'moderate': 2.5,
        'difficult': 3.5
    }
    
    # Performance evaluation
    difficulty_multiplier = difficulty_weights.get(quiz_params['difficulty'], 1.0)
    performance_threshold = 60  # Consider quiz successful if above this percentage
    is_success = performance >= performance_threshold
    
    # Update consecutive performance tracking
    if is_success:
        if hasattr(user_proficiency, 'consecutive_successes'):
            user_proficiency.consecutive_successes += 1
            user_proficiency.consecutive_failures = 0
        else:
            user_proficiency.consecutive_successes = 1
            user_proficiency.consecutive_failures = 0
    else:
        if hasattr(user_proficiency, 'consecutive_failures'):
            user_proficiency.consecutive_failures += 1
            user_proficiency.consecutive_successes = 0
        else:
            user_proficiency.consecutive_failures = 1
            user_proficiency.consecutive_successes = 0
    
    # Cap consecutive counts
    user_proficiency.consecutive_successes = min(user_proficiency.consecutive_successes, 5)
    user_proficiency.consecutive_failures = min(user_proficiency.consecutive_failures, 3)
    
    # Performance and consistency factors
    performance_factor = performance / 100
    base_learning_rates = [1.2, 1.0, 0.8, 0.6, 0.4, 0.2]
    base_learning_rate = base_learning_rates[current_stage_index]
    
    # Adjust learning based on performance, difficulty, and sentiment
    learning_adjustment = (
        base_learning_rate * 
        performance_factor * 
        difficulty_multiplier
    )
    
    # Adjust proficiency based on sentiment feedback (use sentiment score)
    sentiment_adjustment = sentiment_score * 0.3  # Adjust learning based on feedback sentiment (-1 to 1)
    
    # Consistency bonus/penalty
    consistency_bonus = (
        user_proficiency.consecutive_successes * 2 - 
        user_proficiency.consecutive_failures
    ) * 0.5
    
    # Calculate potential new level
    potential_new_level = current_level + learning_adjustment + sentiment_adjustment + consistency_bonus
    
    # Find the appropriate stage
    new_stage_index = next(
        (i for i, (low, high) in enumerate(progression_stages) 
         if low <= potential_new_level < high), 
        current_stage_index
    )
    
    # Ensure gradual progression
    if new_stage_index > current_stage_index:
        # Slow down progression between stages
        potential_new_level = progression_stages[new_stage_index][0] + (
            (potential_new_level - progression_stages[new_stage_index][0]) * 0.5
        )
    
    # Bounded update
    new_proficiency = max(0, min(100, potential_new_level))
    
    # Update user proficiency
    user_proficiency.proficiency_level = new_proficiency
    user_proficiency.quizzes_taken += 1
    user_proficiency.last_updated = datetime.now()
    
    return user_proficiency

def recommend_num_quizzes(user_proficiency):
    """
    Recommend the number of quizzes a user should take based on their proficiency level.
    
    Args:
        user_proficiency (UserProficiency): User's proficiency instance.
        
    Returns:
        int: Recommended number of quizzes.
    """
    base_recommendations = {
        "Beginner": 10,
        "Intermediate": 7,
        "Advanced": 5,
    }

    # Default recommendation based on proficiency category
    recommended = base_recommendations[user_proficiency.proficiency_category]

    # Adjust based on consecutive successes and failures
    if user_proficiency.consecutive_successes >= 3:
        # Reduce recommendations for consistent success
        recommended -= 2
    elif user_proficiency.consecutive_failures >= 2:
        # Increase recommendations for consecutive failures
        recommended += 2

    # Cap recommendations between 1 and 15
    return max(1, min(recommended, 15))

# Sentiment analysis function
def analyze_sentiment(feedback_text):
    """
    Analyze sentiment from user feedback text.
    Returns a sentiment score between -1 (negative) and 1 (positive).
    """
    analyzer = SentimentIntensityAnalyzer()
    sentiment_score = analyzer.polarity_scores(feedback_text)['compound']
    return sentiment_score

def recommend_content(user_proficiency):
    """
    Recommend additional learning content based on user proficiency.
    """

    # Recommend content based on proficiency level
    if user_proficiency.proficiency_level < 30:  # Beginner
        return ["Introduction to programming.","Basic concepts: Variables, Data Types, and Operators.","Beginner's guide to control flow (if-else, loops)."]
    elif user_proficiency.proficiency_level < 60:  # Intermediate
        return ["Intermediate: Functions and Modules.","Data Structures","Object-Oriented Programming (OOP) basics."]
    else:  # Advanced
        return ["Advanced: Frameworks.","Deep dive into algorithms and data structures.","Advanced concepts in multi-threading and concurrency."]

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route("/quiz_interface")
def quiz_interface():
    return render_template("home.html")



@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        hashed_password = generate_password_hash(request.form['password'], method='pbkdf2:sha256')
        new_user = User(username=request.form['username'], email=request.form['email'], password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('dashboard'))
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    session.clear()
    logout_user()
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_authenticated:
        return render_template('dashboard.html', user=current_user)
    else:
        return redirect(url_for('login'))
    

@app.route('/')
def home():
    if current_user.is_authenticated:
        courses = Course.query.all()
        # recommended_courses = generate_recommendations(saved_courses)
        return render_template('app.html', courses=courses, user=current_user)
    else:
        return redirect(url_for('login'))



def markdown_to_list(markdown_string):
    # Split the string into lines
    lines = markdown_string.split('\n')
    # Use a regular expression to match lines that start with '* '
    list_items = [re.sub(r'\* ', '', line) for line in lines if line.startswith('* ')]
    return list_items

###### HERE

@app.route('/about')
def about():
    return render_template('about.html')



# Updated routes.py
@app.route("/select_course")
@login_required
def select_course():
    courses = Course.query.all()
    proficiencies = {p.course_id: p for p in UserProficiency.query.filter_by(user_id=current_user.id).all()}
    
    course_data = []
    for course in courses:
        proficiency = proficiencies.get(course.id, UserProficiency(proficiency_level=0, quizzes_taken=0))
        course_data.append({
            'course': course,
            'proficiency': proficiency.proficiency_category,
            'recommended_quizzes': proficiency.recommended_quizzes
        })
    
    return render_template("select_course.html", course_data=course_data)


@app.route("/course_quiz", methods=["GET", "POST"])
@login_required
def course_quiz():
    if request.method == "GET":
        try:
            # Calculate score
            score = 0
            given_answers = list(request.args.values()) or []
            feedback = given_answers.pop()

            # Retrieve quiz data from the session
            quiz_data = session.get('quiz_data')
            actual_answers = quiz_data['actual_answers']

            # Calculate score
            if given_answers:
                score = sum(1 for actual, given in zip(actual_answers, given_answers) 
                            if actual == given)
            
            # Calculate performance percentage
            performance = (score / len(actual_answers)) * 100

            # Get user proficiency
            user_proficiency = UserProficiency.query.filter_by(
                user_id=current_user.id,
                course_id=quiz_data['course_id']
            ).first()

            # Get RL state (based on user proficiency)
            rl_agent = PersistentQuizRL(current_user.id)
            action_data = rl_agent.get_action(user_proficiency.proficiency_level)

            # Prepare quiz parameters
            quiz_params = {
                'difficulty': action_data['difficulty'],  # Use the RL model's recommended difficulty
                'questions': len(actual_answers),
                'choices': 4
            }

            # Get feedback from the user (feedback is sent as a form field or via another input method)
            feedback_text = feedback
            sentiment_score = analyze_sentiment(feedback_text)  # Sentiment analysis on the feedback

            # Update user proficiency using performance and sentiment
            updated_proficiency = update_user_proficiency(
                user_proficiency, 
                performance, 
                quiz_params,
                sentiment_score  # Use sentiment to adjust the user's proficiency
            )

             # Commit changes to the database
            db.session.add(updated_proficiency)
            db.session.commit()

            recommended_content = recommend_content(updated_proficiency) 
            # Update RL model based on feedback
            rl_agent.update_q_table(action_data['state'], action_data['action'], 
                                    rl_agent.calculate_reward(user_proficiency.proficiency_level, 
                                    action_data['action'], sentiment_score), 
                                    action_data['state'])

            # Save the updated RL model
            # save_rl_model(q_table, EPSILON)  # Save the model after each quiz

            # Return score and performance results
            return render_template("score.html", 
                                   actual_answers=actual_answers,
                                   given_answers=given_answers,
                                   total_questions=len(actual_answers), 
                                   score=score,
                                   performance=performance,
                                   user_proficiency=updated_proficiency,
                                   recommended_content = recommended_content,
                                   user=current_user)

        except Exception as e:
            print(f"Error processing quiz results: {str(e)}")
            db.session.rollback()
            return "An error occurred while processing your quiz results.", 500


@app.route("/quiz/<int:course_id>", methods=["GET", "POST"])
@login_required
def quiz_detail(course_id):
    # Get the course information
    course = Course.query.get_or_404(course_id)
    
    # Fetch user proficiency for the course
    user_proficiency = UserProficiency.query.filter_by(
        user_id=current_user.id,
        course_id=course_id
    ).first()
    
    # If no user proficiency exists, initialize it
    if not user_proficiency:
        user_proficiency = UserProficiency(
            user_id=current_user.id,
            course_id=course_id,
            proficiency_level=0
        )
        db.session.add(user_proficiency)
        db.session.commit()
    
    if request.method == "POST":
        # Use RL agent to get the recommended action
        rl_agent = PersistentQuizRL(current_user.id)
        action_data = rl_agent.get_action(user_proficiency.proficiency_level)  # Get state and action
        
        # Map the action to quiz parameters
        difficulty = action_data['difficulty']
        num_questions = 5 if difficulty == "Easy" else 10 if difficulty == "Moderate" else 15  # Example logic
        params = {
            "difficulty": difficulty,
            "questions": num_questions,
            "choices": 4
        }
        
        # Generate quiz using OpenAI API
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "system",
                "content": f"Create a {params['difficulty']} difficulty quiz on {course.name} programming language. "
                           f"Include {params['questions']} questions with {params['choices']} choices each. "
                           "Return a JSON object with 'questions' array containing 'question', 'choices', and 'answer' fields."
            }],
            temperature=0.7,
        )
        
        # Parse the OpenAI response
        quiz_content = json.loads(response['choices'][0]['message']['content'])
        actual_answers = [q['answer'] for q in quiz_content['questions']]
        print(quiz_content)
        # Store quiz details in the session
        session['quiz_data'] = {
            'content': quiz_content,
            'course_id': course_id,
            'difficulty': params['difficulty'],
            'actual_answers': actual_answers,
        }
        
        # Render the quiz page
        return render_template("quiz.html", 
                               quiz_content=quiz_content, 
                               course=course,
                               user_proficiency=user_proficiency)
    
    # Recommend the number of quizzes to take
    recommended_num_quizzes = recommend_num_quizzes(user_proficiency)
    
    # Render the quiz detail page
    return render_template("quiz_detail.html", 
                           course=course,
                           user_proficiency=user_proficiency, 
                           recommended_num_quizzes=recommended_num_quizzes)



@app.route("/quiz", methods=["GET", "POST"])
@login_required
def quiz():
    if request.method == "POST":
        try:
            language = request.form["language"]
            
            # Get quiz parameters from RL system
            previous_quiz_data = session.get('previous_quiz')
            quiz_rl = PersistentQuizRL(current_user.id)
            
            # Get current state and choose action
            state = quiz_rl.get_state() if not previous_quiz_data else \
                   quiz_rl.get_state(previous_quiz_data['score'], 
                                   previous_quiz_data['total_questions'])
            
            action = quiz_rl.choose_action(state)
            params = quiz_rl.map_difficulty_to_parameters(action)

            # Generate quiz using OpenAI
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{
                    "role": "system",
                    "content": f"Prepare a quiz on {language}. Include {params['questions']} questions with {params['choices']} choices each. Return a JSON object with a 'topic' field and a 'questions' array, where each question includes 'question', 'choices', and 'answer'."
                }],
                temperature=0.7,
            )
            
            quiz_content = json.loads(response['choices'][0]['message']['content'])
            print("regenerayted")
            
            
            print("1 :" + actual_answers)
            session['response'] = quiz_content
            session['current_rl_state'] = {
                'state': state,
                'action': action,
                'params': params
            }
            
            return render_template("quiz.html", quiz_content=quiz_content, user=current_user)
            
        except Exception as e:
            print(f"Error generating quiz: {str(e)}")
            return "An error occurred while generating the quiz. Please try again.", 500
            
    elif request.method == "GET":
        try:
            
            # Calculate score
            score = 0
            # actual_answers = []
            given_answers = list(request.args.values()) or []

            quiz_data = session.get('quiz_data')
            actual_answers = quiz_data['actual_answers']
            if given_answers:
                score = sum(1 for actual, given in zip(actual_answers, given_answers) 
                          if actual == given)
            print(score)
            # Update RL system with results
            rl_state = session.get('current_rl_state')
            if rl_state:
                quiz_rl = PersistentQuizRL(current_user.id)
                next_state = quiz_rl.get_state(score, len(actual_answers))
                reward = calculate_quiz_performance_score(score, len(actual_answers))
                
                quiz_rl.update(
                    rl_state['state'],
                    rl_state['action'],
                    reward,
                    next_state
                )
            
            # Save quiz data for next iteration
            session['previous_quiz'] = {
                'score': score,
                'total_questions': len(actual_answers)
            }
            
            # Get user proficiency
            user_proficiency = UserProficiency.query.filter_by(
                user_id=current_user.id,
                course_id=quiz_data['course_id']
            ).first()

            quiz_rl = PersistentQuizRL(current_user.id, quiz_data['course_id'])
            next_state = quiz_rl.get_state(previous_score=score, total_questions=len(actual_answers))
            reward = calculate_quiz_performance_score(score=score,total_questions=len(actual_answers))
            quiz_rl.update(
                quiz_data['rl_state'],
                quiz_data['rl_action'],
                reward,
                next_state
            )


            return render_template("score.html", 
                                actual_answers=actual_answers,
                                given_answers=given_answers,
                                total_questions = len(actual_answers), 
                                score=score,
                                user=current_user)
                                
        except Exception as e:
            print(f"Error processing quiz results: {str(e)}")
            return "An error occurred while processing your quiz results.", 500


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="127.0.0.1", debug=True)
