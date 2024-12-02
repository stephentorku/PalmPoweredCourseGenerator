import numpy as np
import random
import pickle

# Load the RL model (Q-table and epsilon)
def load_rl_model(filename="rl_model.pkl"):
    """
    Load the Q-table and epsilon from a file.
    """
    try:
        with open(filename, 'rb') as f:
            model = pickle.load(f)
        print("RL model loaded successfully.")
        return model['q_table'], model.get('epsilon', 1.0)  # Default epsilon is 1.0
    except FileNotFoundError:
        print("RL model file not found. Please ensure the Q-table is trained and saved.")
        return np.zeros((3, 3)), 1.0  # Default Q-table for 3 states and 3 actions

# Load Q-table and epsilon globally
q_table, epsilon = load_rl_model()

class PersistentQuizRL:
    def __init__(self, user_id, num_difficulty_levels=3):
        self.user_id = user_id
        self.num_difficulty_levels = num_difficulty_levels

    def proficiency_to_category(self, proficiency):
        """
        Map proficiency score (0-100) to a proficiency category.
        """
        if proficiency < 30:
            return 0  # Beginner
        elif proficiency < 60:
            return 1  # Intermediate
        else:
            return 2  # Advanced

    def choose_action(self, state):
        """
        Choose an action using epsilon-greedy strategy.
        """
        global q_table, epsilon
        if random.random() < epsilon:
            return random.randint(0, self.num_difficulty_levels - 1)  # Explore
        else:
            return np.argmax(q_table[state])  # Exploit

    def get_action(self, proficiency):
        """
        Get the recommended action (quiz difficulty) based on the user's proficiency.
        """
        state = self.proficiency_to_category(proficiency)
        action = self.choose_action(state)
        return {
            "state": state,
            "action": action,
            "difficulty": ['Easy', 'Moderate', 'Difficult'][action]
        }

    def calculate_reward(self, proficiency, action, sentiment_score):
        """
        Calculate reward based on proficiency, action, and sentiment feedback.
        """
        # Performance-based reward (score from quiz)
        performance_reward = 0.0
        if proficiency > 80 and action == 2:  # Advanced taking difficult quizzes
            performance_reward = 2.0  # High reward for good match
        elif proficiency < 30 and action == 0:  # Beginner taking easy quizzes
            performance_reward = 1.0  # Moderate reward for good match
        elif abs(self.proficiency_to_category(proficiency) - action) <= 1:
            performance_reward = 0.5  # Moderate reward for reasonable match
        else:
            performance_reward = -1.0  # Penalty for mismatch

        # Sentiment-based adjustment
        sentiment_adjustment = sentiment_score * 0.5  # Example weight (scale of -1 to 1)

        # Total reward is a combination of performance and sentiment
        total_reward = performance_reward + sentiment_adjustment
        return total_reward

    def update_q_table(self, state, action, reward, next_state):
        """
        Update the Q-value for the given state-action pair in the global Q-table.
        """
        global q_table
        learning_rate = 0.1
        discount_factor = 0.9

        best_future_q = np.max(q_table[next_state])
        current_q = q_table[state, action]
        new_q = current_q + learning_rate * (reward + discount_factor * best_future_q - current_q)
        q_table[state, action] = new_q
