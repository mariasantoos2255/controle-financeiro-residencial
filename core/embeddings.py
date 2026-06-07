import numpy as np
from typing import List, Dict, Any, Tuple
from core.gemini_client import gerar_embedding

def calcular_similaridade_cosseno(v1: List[float], v2: List[float]) -> float:
    """Calcula a similaridade cosseno entre dois vetores."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    try:
        a = np.array(v1)
        b = np.array(v2)
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot_product / (norm_a * norm_b))
    except Exception as e:
        print(f"Erro ao calcular similaridade cosseno: {e}")
        return 0.0

def buscar_semantica(query: str, transacoes: List[Any], top_k: int = 5) -> List[Tuple[Any, float]]:
    """
    Busca transações mais semelhantes à consulta usando similaridade cosseno.
    Retorna uma lista de tuplas (Transacaobj, score_similaridade).
    Caso a API Key do Gemini esteja inativa ou falhe, faz uma busca por substring.
    """
    if not query:
        return [(t, 1.0) for t in transacoes]

    query_emb = gerar_embedding(query)

    # Se falhar o embedding, faz fallback de busca textual insensível a maiúsculas/minúsculas
    if not query_emb:
        print("Buscando por texto simples (fallback)...")
        resultados = []
        termos = query.lower().split()
        for t in transacoes:
            conteudo = f"{t.descricao} {t.categoria}".lower()
            # Score baseado em quantos termos batem
            bates = sum(1 for termo in termos if termo in conteudo)
            if bates > 0:
                score = bates / len(termos)
                resultados.append((t, score))
        # Ordenar por score descendente
        resultados.sort(key=lambda x: x[1], reverse=True)
        return resultados[:top_k]

    # Busca vetorial real
    scored_transactions = []
    for t in transacoes:
        if t.embedding:
            similarity = calcular_similaridade_cosseno(query_emb, t.embedding)
            scored_transactions.append((t, similarity))
        else:
            # Caso essa transação não tenha embedding calculado, gera agora de forma preguiçosa
            emb = gerar_embedding(f"{t.descricao} {t.categoria}")
            if emb:
                t.embedding = emb
                # Importa aqui para salvar no banco o embedding novo
                from core.database import atualizar_transacao
                atualizar_transacao(t)
                similarity = calcular_similaridade_cosseno(query_emb, emb)
                scored_transactions.append((t, similarity))
            else:
                scored_transactions.append((t, 0.0))

    # Remove duplicates or just sort
    scored_transactions.sort(key=lambda x: x[1], reverse=True)
    return scored_transactions[:top_k]
