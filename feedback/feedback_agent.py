import re

class ExpenseFeedbackAgent:
    def generate_feedback(self, user_input, category):
        """
        Gera uma mensagem de feedback com a categoria e o valor extraído do input.
        Se o valor não for identificado, informa que o valor não foi identificado.
        """
        validation_agent = InputValidationAgent()
        if not validation_agent.is_valid_input(user_input):
            return "Ops! Parece que faltou uma descrição. Por favor, inclua uma breve explicação."

        match = re.search(r'\d+([,.]\d+)?', user_input)

        if match:
            value_str = match.group().replace(',', '.')
            try:
                value = float(value_str)
            except ValueError:
                value = None
        else:
            value = None

        if value is not None:
            formatted_value = f"R$ {value:,.2f}"
            formatted_value = formatted_value.replace(',', 'TEMP').replace('.', ',').replace('TEMP', '.')
        else:
            formatted_value = "valor não identificado"

        return f"Despesa adicionada com sucesso: {category}: {formatted_value}"

import re

class InputValidationAgent:
    def is_valid_input(self, user_input):
        # Remove o valor monetário para analisar o texto restante
        description = re.sub(r'\d+([,.]\d+)?', '', user_input)
        description = re.sub(r'[^\w\sÀ-ú]', '', description).strip()

        # Verifica se há pelo menos 1 palavra com 3+ letras e caracteres alfabéticos
        words = [word for word in description.split() if len(word) >= 3]
        return any(re.search(r'[a-zA-ZÀ-ú]{3,}', word) for word in words)