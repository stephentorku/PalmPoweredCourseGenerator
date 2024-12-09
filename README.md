# **AI-Powered Education Platform**

The AI-Powered Education Platform is an improved Flask-based web application designed to deliver a dynamic and personalized learning experience. Leveraging the power of reinforcement learning, sentiment analysis, and OpenAI's GPT-3 model, the platform adapts to individual user needs, ensuring an engaging and effective learning journey.


---
This project was forked from an existing repository. However, very few features were retained. The following shows what parts of the application were retained:
- The user model and login/logout/sign up flow
- The html and css templates
- The flow for generating quizzes and answers

Everything else is a contribution of my own
---

## **Features**

### **User-Centric Personalization**
- **Dynamic Quiz Recommendations**:
  - The platform uses a reinforcement learning model to recommend quiz difficulties (Easy, Moderate, Difficult) based on the user's proficiency level and performance.
- **Sentiment-Driven Adaptation**:
  - User feedback is analyzed using sentiment analysis to adjust quiz recommendations and ensure a positive learning experience.
- **Proficiency Tracking**:
  - Tracks user progress through predefined proficiency stages (Beginner, Intermediate, Advanced) and updates dynamically based on quiz performance and feedback.

### **AI-Powered Content**
- **Quiz Generation**:
  - Generates tailored quizzes using OpenAI's GPT-3 model, incorporating customizable parameters like difficulty and question type.
- **Topic Recommendations**:
  - Provides targeted learning content suggestions based on user proficiency, helping users strengthen specific knowledge areas.

### **Interactive User Experience**
- **Engaging Interface**:
  - Offers an intuitive interface for seamless quiz attempts and feedback collection.
- **Progress Monitoring**:
  - Users can track their proficiency and quiz history over time.

### **Robust Backend**
- **User Authentication**:
  - Secure user registration, login, and profile management.
- **Data Persistence**:
  - Uses SQLite to store user data, quiz results, and feedback for personalized recommendations.

---

## **Installation**

### **Prerequisites**
- Python 3.7 or higher
- Flask installed on your local environment

### **Steps**
1. **Clone the repository**:
    ```bash
    git clone https://github.com/yourusername/AI-Powered-Education-Platform.git
    ```
2. **Navigate to the project directory**:
    ```bash
    cd AI-Powered-Education-Platform
    ```
3. **Install the required Python packages**:
    ```bash
    pip install -r requirements.txt
    ```

---

## **Usage**

1. **Run the Flask application**:
    ```bash
    python app.py
    ```
2. **Access the application**:
    Open your browser and navigate to `http://127.0.0.1:5000/`.
3. **Explore the features**:
    - Sign up or log in to start your learning journey.
    - Attempt personalized quizzes and view your progress.
    - Provide feedback to improve future recommendations.

---

## **Acknowledgements**

This project leverages the following technologies:
- [Flask](https://flask.palletsprojects.com/) for web development.
- [OpenAI API](https://openai.com/) for AI-powered quiz generation.
- [SQLAlchemy](https://www.sqlalchemy.org/) for database management.
- [VADER Sentiment Analysis](https://github.com/cjhutto/vaderSentiment) for analyzing user feedback.
- [Bootstrap](https://getbootstrap.com/) for responsive UI design.
- mahrozmohammed922@gmail.com
