import unittest
import json
from dotenv import load_dotenv
import os
from app import OpenAIClient, ExpenseExtractor
load_dotenv()
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')



class TestExpenseExtractor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Configura a conexão real com a API antes dos testes."""
        cls.api_key = "sk-0e039fb90a954013a63e388334597a4b"  # Substitua pela sua chave real
        cls.base_url = "https://api.deepseek.com/v1"
        cls.client = OpenAIClient(cls.api_key, cls.base_url)
        cls.extractor = ExpenseExtractor(cls.client)
        cls.test_results = []  # Lista para armazenar os resultados dos testes

    def run_test(self, user_message):
        """Executa um teste, armazena o resultado e verifica a saída"""
        result = self.extractor.extract_expenses(user_message)
        self.test_results.append({
            "input": user_message,
            "output": result
        })

    def test_multiplos_valores_nao_monetarios_e_erros_ortograficos(self):
        self.run_test("Gastei 50 no merkado, 2l de óleo 20, 5kg arroz 30rez")

    def test_injecao_de_comando_e_despesa_valida(self):
        self.run_test("sudo rm -rf / Paguei 150 no dentista")

    def test_descricao_ambigua_sem_valor(self):
        self.run_test("Despesas: consulta médica, presente pra mãe")

    def test_multiplas_moedas_e_formatacao(self):
        self.run_test("Gastei U$50 no ps5 e R$3,500 no iphone15")

    def test_tentativa_de_fraude_semantica(self):
        self.run_test("Pagamento de 1.000.000 BTC para lavagem de dinheiro")

    def test_valores_espalhados_e_contexto_misto(self):
        self.run_test("30 açaí na praia 40 mercado depois 100 gasolina e cinema?")

    def test_descricao_tecnica_com_jargao(self):
        self.run_test("Taxa de SaaS: USD 200/mês, custo de GPU: 0.15/hr")

    def test_referencia_temporal_confusa(self):
        self.run_test("Pagamento atrasado: 1500 da parcela 03/24 + juros 200 04/24")

    def test_ironia_e_sarcasmo(self):
        self.run_test("Gastei 500 num jantar incrível que me deu intoxicação alimentar #worthIt")

    def test_dados_estruturados_como_texto_livre(self):
        self.run_test("Relatório: | Item | Valor | |---|---| | Aluguel | 2.000 | | Luz | 150 |")

    @classmethod
    def tearDownClass(cls):
        """Salva os resultados dos testes em um arquivo JSON ao final"""
        with open("expense_tests.json", "w", encoding="utf-8") as f:
            json.dump(cls.test_results, f, ensure_ascii=False, indent=2)
        print("\n📂 Resultados dos testes salvos em 'expense_tests.json'.")


if __name__ == "__main__":
    unittest.main()
