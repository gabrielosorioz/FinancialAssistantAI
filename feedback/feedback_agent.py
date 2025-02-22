import re

class ExpenseFeedbackAgent:
    def generate_feedback(self, user_input, category):
        """
        Gera uma mensagem de feedback humanizada com base na categoria e no input do usuário.
        """
        validation_agent = InputValidationAgent()

        # Verifica se a entrada é válida
        if not validation_agent.is_valid_input(user_input):
            return "Ops! Parece que faltou uma descrição. Por favor, inclua uma breve explicação."

        # Extrai o valor monetário do input
        value = self._extract_value(user_input)

        # Gera feedback com base na categoria
        if category == "Irrelevante":
            return self._generate_irrelevant_feedback(user_input)
        elif category == "Tentativa de injeção":
            return self._generate_injection_feedback()
        elif category == "Outros":
            return self._generate_others_feedback(user_input, value)
        else:
            return self._generate_valid_category_feedback(category, value)

    def _extract_value(self, user_input):
        """
        Extrai o valor monetário do input do usuário.
        """
        match = re.search(r'\d+([,.]\d+)?', user_input)
        if match:
            value_str = match.group().replace(',', '.')
            try:
                return float(value_str)
            except ValueError:
                return None
        return None

    def _format_value(self, value):
        """
        Formata o valor monetário para exibição.
        """
        if value is not None:
            formatted_value = f"R$ {value:,.2f}"
            return formatted_value.replace(',', 'TEMP').replace('.', ',').replace('TEMP', '.')
        return "valor não identificado"

    def _generate_irrelevant_feedback(self, user_input):
        """
        Gera feedback para entradas irrelevantes.
        """
        return f"Parece que '{user_input}' não está relacionado a despesas ou finanças. Estou aqui para ajudar com suas finanças! Caso tenha algum gasto para registrar, é só me informar."

    def _generate_injection_feedback(self):
        """
        Gera feedback para tentativas de injeção.
        """
        return "Ops! Parece que você tentou inserir um comando inválido. Por favor, descreva sua despesa de forma clara."

    def _generate_others_feedback(self, user_input, value):
        """
        Gera feedback para despesas classificadas como 'Outros'.
        """
        formatted_value = self._format_value(value)
        return f"Despesa adicionada com sucesso: '{user_input}' foi categorizada como 'Outros' no valor de {formatted_value}."

    def _generate_valid_category_feedback(self, category, value):
        """
        Gera feedback para categorias válidas.
        """
        formatted_value = self._format_value(value)
        return f"Despesa adicionada com sucesso: {category} no valor de {formatted_value}."


class InputValidationAgent:
    def is_valid_input(self, user_input):
        """
        Verifica se a entrada do usuário é válida.
        """
        # Remove o valor monetário para analisar o texto restante
        description = re.sub(r'\d+([,.]\d+)?', '', user_input)
        description = re.sub(r'[^\w\sÀ-ú]', '', description).strip()

        # Verifica se há pelo menos 1 palavra com 3+ letras e caracteres alfabéticos
        words = [word for word in description.split() if len(word) >= 3]
        return any(re.search(r'[a-zA-ZÀ-ú]{3,}', word) for word in words)