import re
import unicodedata

class TextProcessor:
    @staticmethod
    def sanitize_input(user_input):
        """Remove caracteres especiais e limita o tamanho do input"""
        sanitized = re.sub(r'[{}[\]()<>"\\;]', '', user_input)
        return sanitized[:100].strip()

    @staticmethod
    def normalize_text(text):
        """Normaliza o texto para comparação (remove acentos e converte para minúsculas)"""
        text = unicodedata.normalize('NFKD', text)
        text = text.encode('ascii', 'ignore').decode('utf-8')
        return text.strip().lower()

    