from dataclasses import dataclass, field
from typing import List, Optional, Dict

@dataclass
class Morador:
    """Representa um participante/morador da república."""
    id: Optional[int] = None
    nome: str = ""
    quarto: str = ""
    data_entrada: str = ""
    saldo_atual: float = 0.0
    responsavel: bool = False

@dataclass
class Categoria:
    """Categoria para classificar transações (ex: Aluguel, Luz, Gás, Mercado, Diarista)."""
    id: Optional[int] = None
    nome: str = ""
    tipo: str = "saida" # "entrada" ou "saida"

@dataclass
class Transacao:
    """Representa uma despesa ou receita do controle financeiro."""
    id: Optional[int] = None
    tipo: str = "saida" # "entrada" ou "saida"
    categoria: str = ""
    valor: float = 0.0
    descricao: str = ""
    data_vencimento: str = "" # YYYY-MM-DD
    data_pagamento: Optional[str] = None # YYYY-MM-DD ou None
    status: str = "pendente" # "pago" ou "pendente"
    pagador_id: int = 1
    moradores_dividem: List[int] = field(default_factory=list) # IDs dos moradores que dividem
    embedding: Optional[List[float]] = None

@dataclass
class Recorrencia:
    """Representa uma cobrança ou receita recorrente que se repete mensalmente."""
    id: Optional[int] = None
    categoria: str = ""
    valor: float = 0.0
    descricao: str = ""
    dia_vencimento: int = 5
    pagador_id: int = 1
    moradores_dividem: List[int] = field(default_factory=list)
    ativa: bool = True
