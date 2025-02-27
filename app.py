from dotenv import load_dotenv
import os
from classifiers import ExpenseClassifier
from feedback import ExpenseFeedbackAgent
from ui.streamlit_ui import ExpenseClassifierUI

# Carrega variáveis de ambiente
load_dotenv()

# Configurações globais
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')

def main():
    classifier = ExpenseClassifier(DEEPSEEK_API_KEY)
    feedback_agent = ExpenseFeedbackAgent()
    ui = ExpenseClassifierUI(classifier, feedback_agent)
    ui.run()

if __name__ == "__main__":
    main()