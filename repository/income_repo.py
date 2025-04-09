
from datetime import datetime, timedelta
from models import Income
from typing import Optional, List, Dict, Tuple, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, desc

class IncomeRepository:
    """Repositório para operações com rendimentos no banco de dados."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, income: Income) -> Income:
        """Cria um novo registro de rendimento no banco de dados."""
        self.session.add(income)
        self.session.commit()
        self.session.refresh(income)
        return income

    def get_by_id(self, income_id: int) -> Optional[Income]:
        """Busca um rendimento pelo ID."""
        return self.session.query(Income).filter(Income.id == income_id).first()

    def get_incomes_by_user(self, user_id: int) -> List[Income]:
        """Busca todos os rendimentos de um usuário."""
        return self.session.query(Income).filter(Income.user_id == user_id).all()

    def get_incomes_by_source(self, user_id: int, source: str) -> List[Income]:
        """Busca rendimentos por fonte."""
        return self.session.query(Income).filter(
            Income.user_id == user_id,
            Income.source == source
        ).all()

    def get_incomes_by_date_range(self, user_id: int, start_date: datetime, end_date: datetime) -> List[Income]:
        """Busca rendimentos em um intervalo de datas."""
        return self.session.query(Income).filter(
            Income.user_id == user_id,
            Income.date >= start_date,
            Income.date <= end_date
        ).all()

    def get_recurring_incomes(self, user_id: int) -> List[Income]:
        """Busca rendimentos recorrentes de um usuário."""
        return self.session.query(Income).filter(
            Income.user_id == user_id,
            Income.recurring == True
        ).all()

    def get_monthly_total(self, user_id: int, year: int, month: int) -> float:
        """Retorna o total de rendimentos de um mês específico."""
        result = self.session.query(func.sum(Income.value)).filter(
            Income.user_id == user_id,
            extract('year', Income.date) == year,
            extract('month', Income.date) == month
        ).scalar()

        return result or 0.0

    def get_yearly_total(self, user_id: int, year: int) -> float:
        """Retorna o total de rendimentos de um ano específico."""
        result = self.session.query(func.sum(Income.value)).filter(
            Income.user_id == user_id,
            extract('year', Income.date) == year
        ).scalar()

        return result or 0.0

    def get_top_sources(self, user_id: int, limit: int = 5) -> List[Tuple[str, float]]:
        """Retorna as principais fontes de rendimento por valor total."""
        result = self.session.query(
            Income.source,
            func.sum(Income.value).label('total')
        ).filter(
            Income.user_id == user_id
        ).group_by(
            Income.source
        ).order_by(
            desc('total')
        ).limit(limit).all()

        return result

    def update(self, income: Income) -> Income:
        """Atualiza um rendimento existente."""
        self.session.commit()
        return income

    def delete(self, income_id: int) -> bool:
        """Remove um rendimento pelo ID."""
        income = self.get_by_id(income_id)
        if income:
            self.session.delete(income)
            self.session.commit()
            return True
        return False
