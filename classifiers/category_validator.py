from classifiers.text_processor import TextProcessor

class CategoryValidator:
    def __init__(self, valid_categories):
        self.valid_categories = valid_categories
        self.valid_normalized = {TextProcessor.normalize_text(cat): cat for cat in valid_categories}

    def validate(self, raw_response):
        """Garante que a resposta esteja na lista de categorias válidas"""
        clean_response = TextProcessor.normalize_text(raw_response)
        return self.valid_normalized.get(clean_response, "Outros")