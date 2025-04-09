from datetime import datetime, timedelta
from models import Income
from typing import Optional, List, Dict, Tuple, Any
from repository import IncomeRepository
import calendar
from collections import defaultdict

class IncomeService:
    """Serviço para operações relacionadas a rendimentos com análises estatísticas."""

    def __init__(self, income_repository: IncomeRepository, income_extractor=None):
        self.income_repository = income_repository
        self.income_extractor = income_extractor

    def create_income(self, description: str, value: float, source: str,
                      user_id: int, date: datetime = None, recurring: bool = False,
                      notes: str = None) -> Income:
        """
        Cria um novo registro de rendimento.

        Args:
            description: Descrição do rendimento
            value: Valor recebido
            source: Fonte do rendimento
            user_id: ID do usuário
            date: Data do recebimento (opcional)
            recurring: Se é um rendimento recorrente
            notes: Observações adicionais

        Returns:
            Objeto Income criado
        """
        # Validação
        if value <= 0:
            raise ValueError("O valor do rendimento deve ser positivo")

        income = Income(
            description=description,
            value=value,
            source=source,
            user_id=user_id,
            date=date or datetime.now(),
            recurring=recurring,
            notes=notes
        )

        return self.income_repository.create(income)

    def get_income(self, income_id: int) -> Optional[Income]:
        """Busca um rendimento pelo ID."""
        return self.income_repository.get_by_id(income_id)

    def get_user_incomes(self, user_id: int) -> List[Income]:
        """Busca todos os rendimentos de um usuário."""
        return self.income_repository.get_incomes_by_user(user_id)

    def get_incomes_by_source(self, user_id: int, source: str) -> List[Income]:
        """Busca rendimentos por fonte."""
        return self.income_repository.get_incomes_by_source(user_id, source)

    def get_monthly_incomes(self, user_id: int, year: int, month: int) -> List[Income]:
        """
        Busca rendimentos de um mês específico.

        Args:
            user_id: ID do usuário
            year: Ano
            month: Mês (1-12)

        Returns:
            Lista de rendimentos do mês
        """
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(days=1)

        return self.income_repository.get_incomes_by_date_range(user_id, start_date, end_date)

    def get_recurring_incomes(self, user_id: int) -> List[Income]:
        """Busca rendimentos recorrentes de um usuário."""
        return self.income_repository.get_recurring_incomes(user_id)

    def process_income_message(self, user_id: int, message: str) -> List[Income]:
        """
        Processa uma mensagem para extrair informações de rendimentos.

        Args:
            user_id: ID do usuário
            message: Mensagem com informações de rendimentos

        Returns:
            Lista de rendimentos extraídos e salvos
        """
        if self.income_extractor is None:
            raise ValueError("Income extractor agent is not configured")

        extracted_incomes = self.income_extractor.process(message)

        saved_incomes = []
        for income in extracted_incomes:
            income.user_id = user_id
            saved_income = self.income_repository.create(income)
            saved_incomes.append(saved_income)

        return saved_incomes

    # --- FUNCIONALIDADES DE ANÁLISE DE DADOS ---

    def get_income_by_source_period(self, user_id: int, start_date: datetime,
                                    end_date: datetime) -> Dict[str, float]:
        """
        Retorna o total de rendimentos por fonte em um período específico.

        Args:
            user_id: ID do usuário
            start_date: Data inicial
            end_date: Data final

        Returns:
            Dicionário com fontes como chaves e valores totais como valores
        """
        incomes = self.income_repository.get_incomes_by_date_range(user_id, start_date, end_date)

        totals_by_source = defaultdict(float)
        for income in incomes:
            totals_by_source[income.source] += income.value

        return dict(totals_by_source)

    def get_source_ranking(self, user_id: int, start_date: datetime,
                           end_date: datetime) -> List[Tuple[str, float]]:
        """
        Retorna ranking de fontes de rendimento por valor total em ordem decrescente.

        Args:
            user_id: ID do usuário
            start_date: Data inicial
            end_date: Data final

        Returns:
            Lista de tuplas (fonte, valor_total) ordenada por valor decrescente
        """
        source_totals = self.get_income_by_source_period(user_id, start_date, end_date)
        return sorted(source_totals.items(), key=lambda x: x[1], reverse=True)

    def get_monthly_average(self, user_id: int, months_back: int = 6) -> Dict[str, float]:
        """
        Calcula a média mensal de rendimentos por fonte nos últimos meses.

        Args:
            user_id: ID do usuário
            months_back: Número de meses para analisar

        Returns:
            Dicionário com fontes como chaves e médias mensais como valores
        """
        today = datetime.now()
        start_date = datetime(today.year, today.month, 1) - timedelta(days=1)

        # Retrocede o número de meses especificado
        for _ in range(months_back):
            if start_date.month == 1:
                start_date = datetime(start_date.year - 1, 12, 1)
            else:
                start_date = datetime(start_date.year, start_date.month - 1, 1)

        incomes = self.income_repository.get_incomes_by_date_range(
            user_id, start_date, datetime.now())

        # Agrupa por fonte e mês
        incomes_by_source_month = defaultdict(lambda: defaultdict(float))
        for income in incomes:
            month_key = f"{income.date.year}-{income.date.month}"
            incomes_by_source_month[income.source][month_key] += income.value

        # Calcula a média para cada fonte
        source_averages = {}
        for source, monthly_values in incomes_by_source_month.items():
            source_averages[source] = sum(monthly_values.values()) / len(monthly_values)

        return source_averages

    def get_monthly_trend(self, user_id: int, months: int = 6) -> List[Dict[str, Any]]:
        """
        Calcula a tendência mensal de rendimentos totais.

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

            # Obtém rendimentos do mês
            incomes = self.get_monthly_incomes(user_id, year, month)
            total = sum(income.value for income in incomes)

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
        Fornece um resumo dos rendimentos do ano até o momento.

        Args:
            user_id: ID do usuário

        Returns:
            Dicionário com resumo de rendimentos do ano
        """
        today = datetime.now()
        start_date = datetime(today.year, 1, 1)

        incomes = self.income_repository.get_incomes_by_date_range(
            user_id, start_date, today)

        # Total recebido no ano
        total_received = sum(income.value for income in incomes)

        # Rendimentos por mês
        monthly_totals = defaultdict(float)
        for income in incomes:
            month_key = calendar.month_name[income.date.month]
            monthly_totals[month_key] += income.value

        # Mês com maior rendimento
        max_income_month = max(monthly_totals.items(), key=lambda x: x[1]) if monthly_totals else None

        # Top 3 fontes
        source_totals = defaultdict(float)
        for income in incomes:
            source_totals[income.source] += income.value

        top_sources = sorted(source_totals.items(), key=lambda x: x[1], reverse=True)[:3]

        # Media mensal
        months_passed = today.month
        monthly_average = total_received / months_passed if months_passed > 0 else 0

        return {
            'year': today.year,
            'total_received': total_received,
            'monthly_average': monthly_average,
            'monthly_totals': dict(monthly_totals),
            'max_income_month': max_income_month,
            'top_sources': top_sources
        }

    def predict_monthly_income(self, user_id: int, months_ahead: int = 3) -> List[Dict[str, Any]]:
        """
        Prevê rendimentos para os próximos meses com base nos padrões históricos.

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

    def calculate_income_diversity(self, user_id: int, period_months: int = 3) -> Dict[str, Any]:
        """
        Calcula métricas de diversidade de fontes de renda.

        Args:
            user_id: ID do usuário
            period_months: Número de meses para análise

        Returns:
            Dicionário com métricas de diversidade
        """
        today = datetime.now()
        start_date = datetime(today.year, today.month, 1) - timedelta(days=1)

        # Retrocede o número de meses especificado
        for _ in range(period_months - 1):
            if start_date.month == 1:
                start_date = datetime(start_date.year - 1, 12, 1)
            else:
                start_date = datetime(start_date.year, start_date.month - 1, 1)

        incomes = self.income_repository.get_incomes_by_date_range(
            user_id, start_date, datetime.now())

        if not incomes:
            return {
                'source_count': 0,
                'diversity_index': 0,
                'main_source_dependency': 0,
                'recurring_percentage': 0
            }

        # Totais por fonte
        source_totals = defaultdict(float)
        total_income = 0
        recurring_total = 0

        for income in incomes:
            source_totals[income.source] += income.value
            total_income += income.value
            if income.recurring:
                recurring_total += income.value

        # Número de fontes
        source_count = len(source_totals)

        # Índice de diversidade (adaptado do índice de Shannon)
        diversity_index = 0
        for source, amount in source_totals.items():
            proportion = amount / total_income
            diversity_index -= proportion * (proportion.log2() if proportion > 0 else 0)

        # Normaliza para escala 0-100
        diversity_index = min(100, diversity_index * 100)

        # Dependência da principal fonte
        main_source = max(source_totals.items(), key=lambda x: x[1]) if source_totals else ("Nenhuma", 0)
        main_source_dependency = (main_source[1] / total_income * 100) if total_income > 0 else 0

        # Percentual de rendimentos recorrentes
        recurring_percentage = (recurring_total / total_income * 100) if total_income > 0 else 0

        return {
            'source_count': source_count,
            'diversity_index': diversity_index,
            'main_source': main_source[0],
            'main_source_dependency': main_source_dependency,
            'recurring_percentage': recurring_percentage
        }

    def get_income_expense_balance(self, user_id: int, expense_service, period_months: int = 3) -> Dict[str, Any]:
        """
        Analisa o balanço entre rendimentos e despesas.

        Args:
            user_id: ID do usuário
            expense_service: Serviço de despesas para obter dados comparativos
            period_months: Número de meses para análise

        Returns:
            Dicionário com análise de balanço financeiro
        """
        today = datetime.now()
        monthly_balance = []
        total_income = 0
        total_expense = 0

        # Analisa cada mês no período
        for i in range(period_months - 1, -1, -1):
            # Calcula o mês atual no loop
            if today.month - i <= 0:
                year = today.year - 1
                month = 12 + (today.month - i)
            else:
                year = today.year
                month = today.month - i

            # Obtém rendimentos e despesas do mês
            month_incomes = self.get_monthly_incomes(user_id, year, month)
            income_total = sum(income.value for income in month_incomes)
            total_income += income_total

            month_expenses = expense_service.get_monthly_expenses(user_id, year, month)
            expense_total = sum(expense.value for expense in month_expenses)
            total_expense += expense_total

            # Calcula saldo e taxa de economia
            balance = income_total - expense_total
            savings_rate = (balance / income_total * 100) if income_total > 0 else 0

            monthly_balance.append({
                'year': year,
                'month': month,
                'month_name': calendar.month_name[month],
                'income': income_total,
                'expense': expense_total,
                'balance': balance,
                'savings_rate': savings_rate
            })

        # Métricas gerais do período
        average_income = total_income / period_months if period_months > 0 else 0
        average_expense = total_expense / period_months if period_months > 0 else 0
        average_balance = average_income - average_expense
        overall_savings_rate = (average_balance / average_income * 100) if average_income > 0 else 0

        # Meses com balança negativo
        negative_months = [m for m in monthly_balance if m['balance'] < 0]

        return {
            'monthly_balance': monthly_balance,
            'period_total_income': total_income,
            'period_total_expense': total_expense,
            'period_balance': total_income - total_expense,
            'average_monthly_income': average_income,
            'average_monthly_expense': average_expense,
            'average_monthly_balance': average_balance,
            'overall_savings_rate': overall_savings_rate,
            'negative_balance_months': len(negative_months),
            'financial_health': 'Saudável' if overall_savings_rate > 10 else
            'Adequado' if overall_savings_rate > 0 else
            'Crítico'
        }

    def get_income_dashboard(self, user_id: int) -> Dict[str, Any]:
        """
        Gera um dashboard completo com análises financeiras de rendimentos para o usuário.

        Args:
            user_id: ID do usuário

        Returns:
            Dicionário com diversas métricas e análises
        """
        today = datetime.now()
        start_of_month = datetime(today.year, today.month, 1)

        # Rendimentos do mês atual
        current_month_incomes = self.income_repository.get_incomes_by_date_range(
            user_id, start_of_month, today)
        current_month_total = sum(income.value for income in current_month_incomes)

        # Resumo do ano
        ytd_summary = self.get_year_to_date_summary(user_id)

        # Tendência dos últimos meses
        monthly_trend = self.get_monthly_trend(user_id, months=6)

        # Rendimentos por fonte no mês atual
        source_totals = defaultdict(float)
        for income in current_month_incomes:
            source_totals[income.source] += income.value

        # Previsão para os próximos meses
        predictions = self.predict_monthly_income(user_id, months_ahead=3)

        # Análise de diversidade de renda
        diversity_metrics = self.calculate_income_diversity(user_id)

        # Rendimentos recorrentes
        recurring_incomes = self.get_recurring_incomes(user_id)
        recurring_total = sum(income.value for income in recurring_incomes)
        recurring_count = len(recurring_incomes)

        return {
            'current_date': today.strftime('%Y-%m-%d'),
            'current_month': {
                'name': calendar.month_name[today.month],
                'total_received': current_month_total,
                'sources': dict(source_totals),
                'day_of_month': today.day,
                'days_in_month': calendar.monthrange(today.year, today.month)[1],
                'percentage_of_month_elapsed': (today.day / calendar.monthrange(today.year, today.month)[1]) * 100
            },
            'year_summary': ytd_summary,
            'monthly_trend': monthly_trend,
            'predictions': predictions,
            'income_diversity': diversity_metrics,
            'recurring_income': {
                'count': recurring_count,
                'total': recurring_total,
                'percentage_of_monthly': (recurring_total / current_month_total * 100) if current_month_total > 0 else 0
            }
        }