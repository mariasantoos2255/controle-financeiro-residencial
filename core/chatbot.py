import json
from typing import List, Dict, Any, Optional
from core.database import listar_moradores, listar_categorias, listar_transacoes
from core.gemini_client import chat, get_gemini_api_key

def processar(mensagem: str, historico: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Processa a mensagem em linguagem natural do morador usando Gemini 1.5 Flash.
    Recupera listas ativas de moradores, categorias e transações recentes para contextualizar a IA.
    Retorna um dicionário contendo 'intent', 'transaction_draft' e 'answer'.
    """
    api_key = get_gemini_api_key()
    
    # 1. Obter estado do banco do co-living para contextualizar
    moradores = listar_moradores()
    categorias = listar_categorias()
    transacoes = listar_transacoes()[:15] # Últimas 15
    
    # Formata contextos legíveis para a IA
    contexto_moradores = "\n".join([
        f"- ID: {m.id}, Nome: {m.nome}, Quarto: {m.quarto or 'Não especificado'}, Responsável: {'Sim' if m.responsavel else 'Não'}"
        for m in moradores
    ])
    
    contexto_categorias = ", ".join([f"'{c.nome}'" for c in categorias])
    
    contexto_transacoes = "\n".join([
        f"- ID: {t.id}, Tipo: {t.tipo}, Categoria: {t.categoria}, Valor: R$ {t.valor:.2f}, Descrição: '{t.descricao}', Status: {t.status}, Pago por ID: {t.pagador_id}, Vencimento: {t.data_vencimento}"
        for t in transacoes
    ])
    
    # ID padrão de morador para fallback seguro
    default_morador_id = moradores[0].id if moradores else 1
    todos_moradores_ids = [m.id for m in moradores]

    # Se a chave do Gemini não está configurada, usar um fallback regex de regras simples para João, Maria e Pedro
    if not api_key:
        return processar_fallback_regex(mensagem, moradores, categorias, todos_moradores_ids, default_morador_id)

    # 2. Construir o Prompt de Sistema com instruções rígidas e contexto rico
    prompt_sistema = f"""Você é o Rover, o assistente virtual financeiro oficial da república/co-living. 
Sua tarefa é ajudar os moradores a controlar custos e interpretar comandos em linguagem natural em português.

Abaixo está o estado atual do banco de dados (use esses dados EXATAMENTE para responder perguntas ou extrair IDs de moradores):

=== MORADORES ===
{contexto_moradores}

=== CATEGORIAS DE DESPESA E RECEITA ===
{contexto_categorias}

=== ÚLTIMAS 15 TRANSAÇÕES ===
{contexto_transacoes}

---
REGRAS ÚTEIS:
1. Ao identificar compras de mercado ("compro mercado de 100", "gastei 50 feira"), tente associar à categoria 'Mercado'.
2. "Luz", "Internet", "Aluguel", "Água", "Gás Encanado" ou "Luz Equatorial" devem ser correlacionadas com categorias idênticas ou semelhantes.
3. Se o locutor disser "comprei", "paguei" ou "gastei" sem falar um nome, examine se há pistas. Se não souber quem é, tente extrair o nome do sujeito se citado ("Maria pagou aluguel" -> pagador_id = ID correspondente ao nome Maria).
4. O status de transação é:
   - "pago": se disser coisas como "paguei", "comprou de", "gastei", "Maria pagou", "já pago", "paguei hoje".
   - "pendente": se disser coisas como "lança a conta de luz que chegou de 200", "vence dia 10", "para pagar", "conta de água nova de 80".
5. O rateio padrão se não for dito o contrário é igual entre todos os moradores ativos (moradores_dividem = {todos_moradores_ids}).

Você DEVE retornar obrigatoriamente um objeto JSON com o seguinte formato, sem formatações de markdown adicionais outside (por exemplo, sem ```json):
{{
  "intent": "create_transaction" | "query" | "general",
  "transaction_draft": {{
    "tipo": "entrada" ou "saida",
    "valor": float (representando o valor monetário extraído),
    "categoria": "Nome exato de uma das categorias acima" (ex: 'Mercado' ou 'Luz'),
    "descricao": "Uma descrição curta resumida (ex: 'Compra de pão e frios')",
    "status": "pago" ou "pendente",
    "pagador_id": int (ID do morador que pagou),
    "moradores_dividem": list de int (IDs de todos que dividirão este custo, por padrão todos: {todos_moradores_ids}),
    "data_vencimento": "YYYY-MM-DD" (a data de hoje ou a informada),
    "data_pagamento": "YYYY-MM-DD" ou null (se status for pago, preencha com a data de hoje, se pendente deixe nulo)
  }},
  "answer": "Sua resposta simpática e precisa para o usuário em português. Use markdown para tabelas e layout limpo."
}}

Se a intenção for 'query', responda à pergunta do usuário baseando-se estritamente nas listas enviadas nos blocos acima. Seja amigável, faça contas matemáticas exatas e mostre o resultado em formato de tabela elegante quando útil!
Se a intenção for 'general', responda de maneira descontraída dando dicas de como usar a plataforma.
"""

    try:
        # Chama o cliente Gemini utilizando a biblioteca google-generativeai
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        # Como o helper de chat já foi definido, podemos usá-lo ou chamar diretamente o GenerativeModel
        model = genai.GenerativeModel(
            model_name="models/gemini-1.5-flash",
            generation_config={"response_mime_type": "application/json"}
        )
        
        # Preparar histórico
        contents_history = []
        for h in historico[-6:]: # Pegar as últimas 6 interações para dar continuidade
            role = "user" if h["role"] == "user" else "model"
            contents_history.append({
                "role": role,
                "parts": [h["content"]]
            })
            
        res = model.generate_content(
            contents=contents_history + [{"role": "user", "parts": [mensagem]}],
            system_instruction=prompt_sistema
        )
        
        texto_resposta = res.text.strip()
        resultado_json = json.loads(texto_resposta)
        return resultado_json
        
    except Exception as e:
        print(f"Erro no processamento do chatbot inteligente: {e}")
        # Retorna uma mensagem amigável no formato esperado
        return {
            "intent": "general",
            "transaction_draft": None,
            "answer": f"Infelizmente, tive um contratempo técnico para ler essa mensagem estruturalmente via Gemini: {str(e)}. No entanto, posso responder no modo simples!"
        }

def processar_fallback_regex(mensagem: str, moradores: List[Any], categorias: List[Any], todos_ids: List[int], default_id: int) -> Dict[str, Any]:
    """Fallback heurístico para quando a chave de API do Gemini não está preenchida."""
    msg = mensagem.lower()
    
    # Tenta extrair um valor numérico simples
    import re
    valores = re.findall(r"\d+(?:[.,]\d+)?", msg)
    valor_extraido = 0.0
    if valores:
        # Pega o primeiro e converte
        val_str = valores[0].replace(",", ".")
        try:
            valor_extraido = float(val_str)
        except Exception:
            pass

    # Identificar morador
    pagador_id = default_id
    for m in moradores:
        p_nome = m.nome.split()[0].lower() # Pega apenas o primeiro nome
        if p_nome in msg:
            pagador_id = m.id
            break

    # Identificar categoria
    categoria_f = "Outros"
    for c in categorias:
        if c.nome.lower() in msg:
            categoria_f = c.nome
            break
        elif "mercado" in msg or "comida" in msg or "feira" in msg:
            if c.nome == "Mercado":
                categoria_f = "Mercado"
        elif "luz" in msg or "energia" in msg:
            if c.nome == "Luz":
                categoria_f = "Luz"
        elif "net" in msg or "wifi" in msg or "internet" in msg:
            if c.nome == "Internet":
                categoria_f = "Internet"
        elif "faxina" in msg or "diarista" in msg or "limpeza" in msg:
            if c.nome == "Faxina/Diarista":
                categoria_f = "Faxina/Diarista"

    # Criar data de hoje
    import datetime
    hoje_str = datetime.date.today().strftime("%Y-%m-%d")

    # É cadastro de conta?
    eh_cadastro = valor_extraido > 0 and any(keyword in msg for keyword in ["comprou", "paguei", "luz", "gás", "fatura", "mercado", "aluguel", "reais", "custa"])

    if eh_cadastro:
        nome_pagador = "Alguém"
        for m in moradores:
            if m.id == pagador_id:
                nome_pagador = m.nome
                break
                
        status = "pago" if any(k in msg for k in ["paguei", "pago", "comprei", "gastei"]) else "pendente"
        
        # Montar rascunho
        draft = {
            "tipo": "saida",
            "valor": valor_extraido,
            "categoria": categoria_f,
            "descricao": f"Lançamento via chat: {categoria_f}",
            "status": status,
            "pagador_id": pagador_id,
            "moradores_dividem": todos_ids,
            "data_vencimento": hoje_str,
            "data_pagamento": hoje_str if status == "pago" else None
        }
        
        answer = f"""Entendi no **modo de segurança (offline)**! Detectei que você deseja cadastrar uma transação:
- **Valor**: R$ {valor_extraido:.2f}
- **Devedor que pagou**: {nome_pagador}
- **Categoria**: {categoria_f}
- **Status sugerido**: {status.upper()}

Gostaria de registrar essa despesa dividida entre todos os {len(todos_ids)} moradores? *(Clique nos botões de rascunho que apareceram abaixo para confirmar)*.

*Nota: Para que o Rover interprete textos e tire dúvidas conversacionais exatas, adicione sua **Chave de API do Gemini** nas Configurações.*"""
        return {
            "intent": "create_transaction",
            "transaction_draft": draft,
            "answer": answer
        }
    else:
        # Responder genérico ensinando
        answer = f"""Olá! Estou operando em **modo offline** porque nenhuma Chave do Gemini foi inserida ainda.

Eu posso te ajudar a lançar contas rapidamente se você digitar frases como:
- *"Luz veio 240 reais para pagar"*
- *"Maria pagou 150 de mercado"*

Para fazer consultas automáticas, gráficos e extração profunda, adicione sua **Chave de API do Gemini** no menu de **Configurações ⚙️**!"""
        
        return {
            "intent": "general",
            "transaction_draft": None,
            "answer": answer
        }
