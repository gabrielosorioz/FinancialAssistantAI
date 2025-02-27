import re
import logging
from openai import OpenAI

class ExpenseClassifier:
    def __init__(self, api_key, prompt_template):
        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
        self.prompt_template = prompt_template

    def classify(self, user_input):
        try:
            clean_input = self._sanitize_input(user_input)
            final_prompt = self.prompt_template.format(clean_input)
            response = self._call_ai(final_prompt)
            print(response.choices[0].message.content.strip())
            return response.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"Erro: {str(e)}")
            return "Erro, Por favor tente novamente!"

    def _sanitize_input(self, user_input):
        # Remove caracteres indesejados
        return re.sub(r'[^\w\s]', '', user_input)

    def _normalize_text(self, text):
        # Normaliza o texto (ex: lower case, remove espaços extras)
        return text.lower().strip()

    def _apply_rules(self, normalized_input):
        # Aplica regras pré-definidas
        for pattern, category in self.rules.items():
            if re.search(pattern, normalized_input, re.IGNORECASE):
                return category
        return None

    def _call_ai(self, prompt):
        # Chama a API da OpenAI/Deepseek
        return self.client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.1,
            max_tokens=30,
            stop=["\n", ".", "```"]
        )