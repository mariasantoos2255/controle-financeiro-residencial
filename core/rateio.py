from typing import List, Dict, Any

def calcular_acertos(moradores_lista: List[Any]) -> List[Dict[str, Any]]:
    """
    Algoritmo de reconciliação de dívidas domésticas (quem deve para quem).
    Pega os moradores com seus respectivos saldos atuais (líquidos):
    - Saldo positivo (> 0): Credores (pagaram mais do que lhes cabia, têm a receber).
    - Saldo negativo (< 0): Devedores (pagaram menos do que consumiram, têm a pagar).
    Retorna uma lista de transferências sugeridas de menor volume para liquidar as contas.
    """
    # Separar em credores e devedores usando margem de 1 centavo
    credores = []
    devedores = []
    
    for m in moradores_lista:
        saldo = getattr(m, "saldo_atual", 0.0)
        # Convertemos para float caso seja retornado outro tipo de dado numérico
        saldo = float(saldo)
        
        if saldo > 0.01:
            credores.append({
                "id": m.id,
                "nome": m.nome,
                "saldo": saldo
            })
        elif saldo < -0.01:
            devedores.append({
                "id": m.id,
                "nome": m.nome,
                "saldo": abs(saldo)
            })
            
    # Ordenar maiores credores e maiores devedores para otimizar as transações sugeridas
    credores.sort(key=lambda x: x["saldo"], reverse=True)
    devedores.sort(key=lambda x: x["saldo"], reverse=True)
    
    transferencias = []
    i, j = 0, 0
    
    while i < len(devedores) and j < len(credores):
        dev = devedores[i]
        cred = credores[j]
        
        # O valor é o mínimo necessário para sanar um dos lados
        valor_transferencia = min(dev["saldo"], cred["saldo"])
        
        if valor_transferencia > 0.009:
            transferencias.append({
                "de_id": dev["id"],
                "de_nome": dev["nome"],
                "para_id": cred["id"],
                "para_nome": cred["nome"],
                "valor": round(valor_transferencia, 2)
            })
            
        dev["saldo"] -= valor_transferencia
        cred["saldo"] -= valor_transferencia
        
        # Avança para o próximo se este morador já zerou sua pendência
        if dev["saldo"] < 0.01:
            i += 1
        if cred["saldo"] < 0.01:
            j += 1
            
    return transferencias

def calcular_resumo_mes(transacoes_mes: List[Any], moradores_lista: List[Any]) -> Dict[str, Any]:
    """
    Calcula os indicadores sumários de competência de um mês selecionado:
    - total_entradas: quanto entrou
    - total_saidas: quanto saiu
    - saldo: entradas - saídas
    - total_pendente: despesas que ainda não foram pagas
    """
    total_entradas = 0.0
    total_saidas = 0.0
    total_pendente = 0.0
    
    for t in transacoes_mes:
        v = float(t.valor)
        if t.tipo == "entrada":
            total_entradas += v
        else:
            total_saidas += v
            if t.status == "pendente":
                total_pendente += v
                
    return {
        "total_entradas": round(total_entradas, 2),
        "total_saidas": round(total_saidas, 2),
        "saldo": round(total_entradas - total_saidas, 2),
        "total_pendente": round(total_pendente, 2)
    }
