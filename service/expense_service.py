from datetime import datetime, timedelta
from models import Expense
from repository import ExpenseRepository
from agents.expense_agents import ExpenseExtractorAgent
from typing import Optional, List, Dict, Tuple, Any
import calendar
from collections import defaultdict


class ExpenseService:
    """Serviço para operações relacionadas a despesas com análises estatísticas."""

    def __init__(self, expense_repository: ExpenseRepository, expense_extractor: ExpenseExtractorAgent = None):
        self.expense_repository = expense_repository
        self.expense_extractor = expense_extractor

    def create_expense(self, description: str, value: float, category: str, user_id: int, installments: int = None,
                       date: datetime = None) -> Expense:
        # Validação de dados de entrada
        if value <= 0:
            raise ValueError("O valor da despesa deve ser positivo")

        expense = Expense(
            description=description,
            value=value,
            category=category,
            user_id=user_id,
            installments=installments,
            date=date or datetime.now()
        )
        return self.expense_repository.create(expense)

    def get_expense(self, expense_id: int) -> Optional[Expense]:
        return self.expense_repository.get_by_id(expense_id)

    def get_user_expenses(self, user_id: int) -> List[Expense]:
        return self.expense_repository.get_expenses_by_user(user_id)

    def get_expenses_by_category(self, user_id: int, category: str) -> List[Expense]:
        return self.expense_repository.get_expenses_by_category(user_id, category)

    def get_monthly_expenses(self, user_id: int, year: int, month: int) -> List[Expense]:
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(days=1)

        return self.expense_repository.get_expenses_by_date_range(user_id, start_date, end_date)

    def get_installment_expenses(self, user_id: int) -> List[Expense]:
        return self.expense_repository.get_installment_expenses(user_id)

    def process_expense_message(self, user_id: int, message: str) -> List[Expense]:
        if self.expense_extractor is None:
            raise ValueError("Expense extractor agent is not configured")

        extracted_expenses = self.expense_extractor.process(message)

        saved_expenses = []
        for expense_data in extracted_expenses:
            expense = Expense(
                description=expense_data.description,
                value=expense_data.value,
                category=expense_data.category,
                user_id=user_id,
                installments=getattr(expense_data, 'installments', None)
            )
            saved_expense = self.expense_repository.create(expense)
            saved_expenses.append(saved_expense)

        return saved_expenses

    # --- NOVAS FUNCIONALIDADES DE ANÁLISE DE DADOS ---

    def get_expenses_by_category_period(self, user_id: int, start_date: datetime,
                                        end_date: datetime) -> Dict[str, float]:
        """
        Retorna o total de despesas por categoria em um período específico.

        Args:
            user_id: ID do usuário
            start_date: Data inicial do período
            end_date: Data final do período

        Returns:
            Dicionário com categorias como chaves e valores totais como valores
        """
        expenses = self.expense_repository.get_expenses_by_date_range(user_id, start_date, end_date)

        totals_by_category = defaultdict(float)
        for expense in expenses:
            totals_by_category[expense.category] += expense.value

        return dict(totals_by_category)

    def get_category_ranking(self, user_id: int, start_date: datetime,
                             end_date: datetime) -> List[Tuple[str, float]]:
        """
        Retorna ranking de categorias por valor total de despesas em ordem decrescente.

        Args:
            user_id: ID do usuário
            start_date: Data inicial do período
            end_date: Data final do período

        Returns:
            Lista de tuplas (categoria, valor_total) ordenada por valor decrescente
        """
        category_totals = self.get_expenses_by_category_period(user_id, start_date, end_date)
        return sorted(category_totals.items(), key=lambda x: x[1], reverse=True)

    def get_monthly_average(self, user_id: int,
                            months_back: int = 6) -> Dict[str, float]:
        """
        Calcula a média mensal de gastos por categoria nos últimos meses.

        Args:
            user_id: ID do usuário
            months_back: Número de meses para olhar para trás

        Returns:
            Dicionário com categorias como chaves e médias mensais como valores
        """
        today = datetime.now()
        start_date = datetime(today.year, today.month, 1) - timedelta(days=1)

        # Retrocede o número de meses especificado
        for _ in range(months_back):
            if start_date.month == 1:
                start_date = datetime(start_date.year - 1, 12, 1)
            else:
                start_date = datetime(start_date.year, start_date.month - 1, 1)

        expenses = self.expense_repository.get_expenses_by_date_range(
            user_id, start_date, datetime.now())

        # Agrupa por categoria e mês
        expenses_by_category_month = defaultdict(lambda: defaultdict(float))
        for expense in expenses:
            month_key = f"{expense.date.year}-{expense.date.month}"
            expenses_by_category_month[expense.category][month_key] += expense.value

        # Calcula a média para cada categoria
        category_averages = {}
        for category, monthly_values in expenses_by_category_month.items():
            category_averages[category] = sum(monthly_values.values()) / len(monthly_values)

        return category_averages

    def detect_expense_anomalies(self, user_id: int, threshold_percent: float = 50.0) -> List[Expense]:
        """
        Detecta despesas anômalas que excedem a média da categoria por um percentual.

        Args:
            user_id: ID do usuário
            threshold_percent: Percentual acima da média para considerar anômalo

        Returns:
            Lista de despesas consideradas anômalas
        """
        # Obtém os últimos 3 meses de despesas
        today = datetime.now()
        start_date = datetime(today.year, today.month, 1) - timedelta(days=1)
        if start_date.month < 3:
            # Ajusta para ano anterior se necessário
            if start_date.month == 2:
                start_date = datetime(start_date.year - 1, 12, 1)
            elif start_date.month == 1:
                start_date = datetime(start_date.year - 1, 11, 1)
        else:
            start_date = datetime(start_date.year, start_date.month - 2, 1)

        expenses = self.expense_repository.get_expenses_by_date_range(
            user_id, start_date, datetime.now())

        # Calcula média por categoria
        category_values = defaultdict(list)
        for expense in expenses:
            category_values[expense.category].append(expense.value)

        category_averages = {
            cat: sum(values) / len(values)
            for cat, values in category_values.items()
        }

        # Identifica anomalias
        anomalies = []
        for expense in expenses:
            if expense.category in category_averages:
                avg = category_averages[expense.category]
                if expense.value > avg * (1 + threshold_percent / 100):
                    anomalies.append(expense)

        return anomalies

    def get_monthly_trend(self, user_id: int, months: int = 6) -> List[Dict[str, Any]]:
        """
        Calcula a tendência mensal de gastos totais.

        Args:
            user_id: ID do usuário
            months: Número de meses para analisar

        Returns:
            Lista de dicionários com dados mensais e percentuais de variação
        """
        today = datetime.now()
        results = []

        for i in range(months - 1, -1, -1):
            # Calcula o mês atual no loop
            if today.month - i <= 0:
                year = today.year - 1
                month = 12 + (today.month - i)
            else:
                year = today.year
                month = today.month - i

            # Obtém despesas do mês
            expenses = self.get_monthly_expenses(user_id, year, month)
            total = sum(expense.value for expense in expenses)

            # Calcula variação percentual (exceto para o primeiro mês)
            percent_change = None
            if i < months - 1 and results[-1]['total'] > 0:
                percent_change = ((total - results[-1]['total']) / results[-1]['total']) * 100

            results.append({
                'year': year,
                'month': month,
                'month_name': calendar.month_name[month],
                'total': total,
                'percent_change': percent_change
            })

        return results

    def get_year_to_date_summary(self, user_id: int) -> Dict[str, Any]:
        """
        Fornece um resumo dos gastos do ano até o momento.

        Args:
            user_id: ID do usuário

        Returns:
            Dicionário com resumo de gastos do ano
        """
        today = datetime.now()
        start_date = datetime(today.year, 1, 1)

        expenses = self.expense_repository.get_expenses_by_date_range(
            user_id, start_date, today)

        # Total gasto no ano
        total_spent = sum(expense.value for expense in expenses)

        # Gastos por mês
        monthly_totals = defaultdict(float)
        for expense in expenses:
            month_key = calendar.month_name[expense.date.month]
            monthly_totals[month_key] += expense.value

        # Mês com maior gasto
        max_spending_month = max(monthly_totals.items(), key=lambda x: x[1]) if monthly_totals else None

        # Top 3 categorias
        category_totals = defaultdict(float)
        for expense in expenses:
            category_totals[expense.category] += expense.value

        top_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)[:3]

        # Media mensal
        months_passed = today.month
        monthly_average = total_spent / months_passed if months_passed > 0 else 0

        return {
            'year': today.year,
            'total_spent': total_spent,
            'monthly_average': monthly_average,
            'monthly_totals': dict(monthly_totals),
            'max_spending_month': max_spending_month,
            'top_categories': top_categories
        }

    def predict_monthly_expenses(self, user_id: int, months_ahead: int = 3) -> List[Dict[str, Any]]:
        """
        Prevê gastos para os próximos meses com base nos padrões históricos.

        Args:
            user_id: ID do usuário
            months_ahead: Número de meses para prever

        Returns:
            Lista de dicionários com previsões mensais
        """
        # Obtém dados dos últimos 6 meses para análise
        monthly_trend = self.get_monthly_trend(user_id, months=6)

        if not monthly_trend:
            return []

        # Calcula a taxa média de crescimento mensal
        growth_rates = []
        for i in range(1, len(monthly_trend)):
            if monthly_trend[i - 1]['total'] > 0:
                rate = (monthly_trend[i]['total'] - monthly_trend[i - 1]['total']) / monthly_trend[i - 1]['total']
                growth_rates.append(rate)

        # Se não houver taxas de crescimento calculáveis, usa o último mês como base
        avg_growth_rate = sum(growth_rates) / len(growth_rates) if growth_rates else 0

        # Mês e ano base (último mês nos dados)
        base_month = monthly_trend[-1]['month']
        base_year = monthly_trend[-1]['year']
        base_amount = monthly_trend[-1]['total']

        predictions = []
        for i in range(1, months_ahead + 1):
            # Calcula o próximo mês
            next_month = base_month + i
            next_year = base_year

            # Ajusta para virada de ano
            if next_month > 12:
                next_month = next_month - 12
                next_year += 1

            # Prevê o valor com crescimento composto
            predicted_amount = base_amount * ((1 + avg_growth_rate) ** i)

            predictions.append({
                'year': next_year,
                'month': next_month,
                'month_name': calendar.month_name[next_month],
                'predicted_amount': predicted_amount,
                'growth_rate_applied': avg_growth_rate
            })

        return predictions

    def get_expense_dashboard(self, user_id: int) -> Dict[str, Any]:
        """
        Gera um dashboard completo com análises financeiras para o usuário.

        Args:
            user_id: ID do usuário

        Returns:
            Dicionário com diversas métricas e análises
        """
        today = datetime.now()
        start_of_month = datetime(today.year, today.month, 1)
        start_of_year = datetime(today.year, 1, 1)

        # Despesas do mês atual
        current_month_expenses = self.expense_repository.get_expenses_by_date_range(
            user_id, start_of_month, today)
        current_month_total = sum(expense.value for expense in current_month_expenses)

        # Resumo do ano
        ytd_summary = self.get_year_to_date_summary(user_id)

        # Tendência dos últimos meses
        monthly_trend = self.get_monthly_trend(user_id, months=6)

        # Despesas por categoria no mês atual
        category_totals = defaultdict(float)
        for expense in current_month_expenses:
            category_totals[expense.category] += expense.value

        # Previsão para os próximos meses
        predictions = self.predict_monthly_expenses(user_id, months_ahead=3)

        # Anomalias detectadas
        anomalies = self.detect_expense_anomalies(user_id)

        # Análise de parcelamentos ativos
        installments = self.get_installment_expenses(user_id)
        total_installment_commitment = sum(expense.value for expense in installments)

        return {
            'current_date': today.strftime('%Y-%m-%d'),
            'current_month': {
                'name': calendar.month_name[today.month],
                'total_spent': current_month_total,
                'categories': dict(category_totals),
                'day_of_month': today.day,
                'days_in_month': calendar.monthrange(today.year, today.month)[1],
                'percentage_of_month_elapsed': (today.day / calendar.monthrange(today.year, today.month)[1]) * 100
            },
            'year_summary': ytd_summary,
            'monthly_trend': monthly_trend,
            'predictions': predictions,
            'anomalies': [
                {'id': expense.id, 'description': expense.description,
                 'value': expense.value, 'category': expense.category}
                for expense in anomalies
            ],
            'installments': {
                'active_count': len(installments),
                'total_commitment': total_installment_commitment
            }
        }