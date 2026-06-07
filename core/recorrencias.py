from core.database import listar_recorrencias, listar_transacoes, inserir_transacao
from core.models import Transacao, Recorrencia
from typing import List, Dict, Any

def extrair_vencimento_data(mes_ano: str, dia: int) -> str:
    """Toma '2026-06' e o dia 5, e formula '2026-06-05' com padding para segurança."""
    dia_str = str(dia).zfill(2)
    return f"{mes_ano}-{dia_str}"

def gerar_recorrentes_pro_mes(mes_ano: str) -> List[Dict[str, Any]]:
    """
    Varre todas as recorrências ativas no cadastro da república.
    Gera automaticamente uma transação do tipo 'pendente' no mês indicado (mes_ano, e.g. '2026-06'),
    garantindo que se já houver transação equivalente lançada para evitar duplicidade.
    Retorna uma lista resumindo o que foi gerado.
    """
    recorrencias = listar_recorrencias()
    transacoes_existentes = listar_transacoes(mes_ano=mes_ano)
    
    gerados = []
    
    # Mapear chaves de identificação simples para evitar duplicados
    lista_chaves = []
    for tx in transacoes_existentes:
        lista_chaves.append((tx.categoria.lower(), round(tx.valor, 2), tx.descricao.lower()))
        
    for r in recorrencias:
        if not r.ativa:
            continue
            
        chave_reg = (r.categoria.lower(), round(r.valor, 2), r.descricao.lower())
        if chave_reg in lista_chaves:
            # Já existe uma transação idêntica lançada neste mês
            continue
            
        # Montar a nova transacao pendente
        data_vencimento = extrair_vencimento_data(mes_ano, r.dia_vencimento)
        
        nova_tx = Transacao(
            tipo="saida",
            categoria=r.categoria,
            valor=r.valor,
            descricao=r.descricao,
            data_vencimento=data_vencimento,
            data_pagamento=None,
            status="pendente",
            pagador_id=r.pagador_id,
            moradores_dividem=r.moradores_dividem,
            embedding=None
        )
        
        novo_id = inserir_transacao(nova_tx)
        gerados.append({
            "id": novo_id,
            "descricao": r.descricao,
            "valor": r.valor,
            "categoria": r.categoria,
            "data_vencimento": data_vencimento
        })
        
    return gerados
