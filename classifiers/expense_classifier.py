from openai import OpenAI
import re
import logging
from classifiers.text_processor import TextProcessor
from rules.classification_rules import CLASSIFICATION_RULES

class ExpenseClassifier:

    def __init__(self, api_key, prompt_template, validator):
        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
        self.prompt_template = prompt_template
        self.validator = validator
        self.rules = CLASSIFICATION_RULES

    def classify(self, user_input):
        try:
            clean_input = TextProcessor.sanitize_input(user_input)
            normalized_input = TextProcessor.normalize_text(clean_input)

            # Verifica regras antes de chamar a IA
            for pattern, category in self.rules.items():
                if re.search(pattern, normalized_input, re.IGNORECASE):
                    print("Categoria retornada sem API: " + category)
                    return category

            # Se nenhuma regra for aplicada, chama a IA
            final_prompt = self.prompt_template.format(clean_input)
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "system", "content": final_prompt}],
                temperature=0.1,
                max_tokens=30,
                stop=["\n", ".", "```"]
            )
            raw_category = response.choices[0].message.content
            return self.validator.validate(raw_category)
        except Exception as e:
            logging.error(f"Erro: {str(e)}")
            return "Outros"