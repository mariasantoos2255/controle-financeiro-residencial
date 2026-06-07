import sqlite3
import os
import json
from typing import List, Dict, Any, Optional
from core.models import Morador, Categoria, Transacao, Recorrencia

DB_NAME = "financeiro.db"

def get_connection():
    """Retorna uma conexão com o banco de dados SQLite."""
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Cria as tabelas do banco de dados se não existirem e insere dados padrão."""
    conn = get_connection()
    cursor = conn.cursor()

    # Tabela de Moradores
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS moradores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        quarto TEXT,
        data_entrada TEXT,
        saldo_atual REAL DEFAULT 0.0,
        responsavel INTEGER DEFAULT 0
    )
    """)

    # Tabela de Categorias
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS categorias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT UNIQUE NOT NULL,
        tipo TEXT NOT NULL CHECK(tipo IN ('entrada', 'saida'))
    )
    """)

    # Tabela de Transações
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo TEXT NOT NULL CHECK(tipo IN ('entrada', 'saida')),
        categoria TEXT NOT NULL,
        valor REAL NOT NULL,
        descricao TEXT NOT NULL,
        data_vencimento TEXT NOT NULL,
        data_pagamento TEXT,
        status TEXT NOT NULL CHECK(status IN ('pago', 'pendente')),
        pagador_id INTEGER NOT NULL,
        moradores_dividem TEXT NOT NULL, -- Lista em JSON
        embedding TEXT, -- Vetor em JSON
        FOREIGN KEY(pagador_id) REFERENCES moradores(id)
    )
    """)

    # Tabela de Recorrências
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recorrencias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        categoria TEXT NOT NULL,
        valor REAL NOT NULL,
        descricao TEXT NOT NULL,
        dia_vencimento INTEGER NOT NULL,
        pagador_id INTEGER NOT NULL,
        moradores_dividem TEXT NOT NULL, -- Lista em JSON
        ativa INTEGER DEFAULT 1,
        FOREIGN KEY(pagador_id) REFERENCES moradores(id)
    )
    """)

    # Tabela de Fechamentos Mensais
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fechamentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mes_ano TEXT UNIQUE NOT NULL, -- Formato YYYY-MM
        total_entradas REAL NOT NULL,
        total_saidas REAL NOT NULL,
        saldo REAL NOT NULL,
        total_pendente REAL NOT NULL,
        fechado_em TEXT NOT NULL,
        fechado_por TEXT NOT NULL
    )
    """)

    # Tabela de Saldos Estáticos dos Moradores no Fechamento
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fechamentos_moradores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fechamento_id INTEGER,
        morador_id INTEGER,
        valor_balanco REAL NOT NULL,
        FOREIGN KEY(fechamento_id) REFERENCES fechamentos(id) ON DELETE CASCADE,
        FOREIGN KEY(morador_id) REFERENCES moradores(id)
    )
    """)

    conn.commit()

    # POPULAR DADOS PADRÃO SE VAZIO

    # 1. Moradores
    cursor.execute("SELECT COUNT(*) as count FROM moradores")
    row = cursor.fetchone()
    if row["count"] == 0:
        moradores_padrao = [
            ("João Silva", "Suíte master", "2026-01-10", 1),
            ("Maria Santos", "Quarto azul", "2026-02-15", 0),
            ("Pedro Oliveira", "Quarto verde", "2026-03-01", 0)
        ]
        cursor.executemany(
            "INSERT INTO moradores (nome, quarto, data_entrada, responsavel) VALUES (?, ?, ?, ?)",
            moradores_padrao
        )
        conn.commit()

    # 2. Categorias
    cursor.execute("SELECT COUNT(*) as count FROM categorias")
    row = cursor.fetchone()
    if row["count"] == 0:
        categorias_padrao = [
            ("Aluguel", "saida"),
            ("Luz", "saida"),
            ("Água", "saida"),
            ("Internet", "saida"),
            ("Gás enchendo/LPG", "saida"),
            ("Mercado", "saida"),
            ("Faxina/Diarista", "saida"),
            ("Manutenção da Casa", "saida"),
            ("Cota Inicial", "entrada"),
            ("Outros", "saida")
        ]
        cursor.executemany(
            "INSERT INTO categorias (nome, tipo) VALUES (?, ?)",
            categorias_padrao
        )
        conn.commit()

    # 3. Recorrências Padrão se vazio
    cursor.execute("SELECT COUNT(*) as count FROM recorrencias")
    row = cursor.fetchone()
    if row["count"] == 0:
        # Pega IDs dos moradores João (1), Maria (2) para associar
        cursor.execute("SELECT id FROM moradores ORDER BY id ASC")
        morador_ids = [r["id"] for r in cursor.fetchall()]
        if len(morador_ids) >= 2:
            m1, m2 = morador_ids[0], morador_ids[1]
            divisao_completa_json = json.dumps(morador_ids)
            recorrencias_padrao = [
                ("Aluguel", 1500.0, "Aluguel mensal da casa", 10, m1, divisao_completa_json, 1),
                ("Internet", 120.0, "Internet fixa fibra 500MB", 5, m2, divisao_completa_json, 1),
                ("Luz", 240.0, "Conta de energia elétrica estimada", 18, m1, divisao_completa_json, 1)
            ]
            cursor.executemany(
                "INSERT INTO recorrencias (categoria, valor, descricao, dia_vencimento, pagador_id, moradores_dividem, ativa) VALUES (?, ?, ?, ?, ?, ?, ?)",
                recorrencias_padrao
            )
            conn.commit()

    # 4. Transações iniciais se vazio (para ter dados no painel e podermos demonstrar)
    cursor.execute("SELECT COUNT(*) as count FROM transacoes")
    row = cursor.fetchone()
    if row["count"] == 0:
        cursor.execute("SELECT id FROM moradores ORDER BY id ASC")
        morador_ids = [r["id"] for r in cursor.fetchall()]
        if len(morador_ids) >= 3:
            m1, m2, m3 = morador_ids[0], morador_ids[1], morador_ids[2]
            div_all = json.dumps(morador_ids)
            # Para o mês atual do sistema
            import datetime
            hoje = datetime.date.today()
            ano_mes = hoje.strftime("%Y-%m")
            
            transacoes_padrao = [
                ("saida", "Aluguel", 1500.0, "Aluguel da República", f"{ano_mes}-10", f"{ano_mes}-10", "pago", m1, div_all),
                ("saida", "Luz", 280.0, "Conta de luz - equatorial", f"{ano_mes}-15", None, "pendente", m2, div_all),
                ("saida", "Mercado", 450.0, "Compras do mês para a despensa", f"{ano_mes}-04", f"{ano_mes}-04", "pago", m3, div_all),
                ("saida", "Internet", 120.0, "Mensalidade da internet", f"{ano_mes}-05", f"{ano_mes}-05", "pago", m2, div_all)
            ]
            cursor.executemany(
                "INSERT INTO transacoes (tipo, categoria, valor, descricao, data_vencimento, data_pagamento, status, pagador_id, moradores_dividem) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                transacoes_padrao
            )
            conn.commit()

    conn.close()

# --- OPERAÇÕES DE MORADORES ---

def listar_moradores() -> List[Morador]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM moradores")
    rows = cursor.fetchall()
    conn.close()
    
    moradores = []
    for r in rows:
        moradores.append(Morador(
            id=r["id"],
            nome=r["nome"],
            quarto=r["quarto"],
            data_entrada=r["data_entrada"],
            saldo_atual=r["saldo_atual"],
            responsavel=bool(r["responsavel"])
        ))
    return moradores

def inserir_morador(m: Morador) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO moradores (nome, quarto, data_entrada, responsavel) VALUES (?, ?, ?, ?)",
        (m.nome, m.quarto, m.data_entrada, 1 if m.responsavel else 0)
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id

def atualizar_morador(m: Morador):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE moradores SET nome=?, quarto=?, data_entrada=?, responsavel=? WHERE id=?",
        (m.nome, m.quarto, m.data_entrada, 1 if m.responsavel else 0, m.id)
    )
    conn.commit()
    conn.close()

def atualizar_saldo_morador(morador_id: int, saldo: float):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE moradores SET saldo_atual=? WHERE id=?", (saldo, morador_id))
    conn.commit()
    conn.close()

def deletar_morador(morador_id: int) -> bool:
    """Deleta o morador apenas se ele não tiver transações registradas."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Conferir se tem transações como pagador ou dividindo
    cursor.execute("SELECT COUNT(*) as count FROM transacoes WHERE pagador_id=?", (morador_id,))
    pago_count = cursor.fetchone()["count"]
    
    if pago_count > 0:
        conn.close()
        return False
        
    cursor.execute("DELETE FROM moradores WHERE id=?", (morador_id,))
    conn.commit()
    conn.close()
    return True

# --- OPERAÇÕES DE CATEGORIAS ---

def listar_categorias() -> List[Categoria]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM categorias ORDER BY nome ASC")
    rows = cursor.fetchall()
    conn.close()
    return [Categoria(id=r["id"], nome=r["nome"], tipo=r["tipo"]) for r in rows]

def inserir_categoria(cat: Categoria) -> Optional[int]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO categorias (nome, tipo) VALUES (?, ?)", (cat.nome, cat.tipo))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return new_id
    except sqlite3.IntegrityError:
        conn.close()
        return None

# --- OPERAÇÕES DE TRANSAÇÕES ---

def listar_transacoes(mes_ano: Optional[str] = None, q: Optional[str] = None) -> List[Transacao]:
    """Retorna lista de transações filtradas por mês/ano (YYYY-MM) se fornecido."""
    conn = get_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM transacoes"
    params = []
    
    conditions = []
    if mes_ano:
        conditions.append("strftime('%Y-%m', data_vencimento) = ?")
        params.append(mes_ano)
        
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
        
    query += " ORDER BY data_vencimento DESC, id DESC"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    transacoes = []
    for r in rows:
        dividem_ids = []
        try:
            dividem_ids = json.loads(r["moradores_dividem"])
        except Exception:
            # Fallback em caso de erros de parse
            dividem_ids = [int(i) for i in r["moradores_dividem"].split(",") if i.strip()]
            
        emb = None
        if r["embedding"]:
            try:
                emb = json.loads(r["embedding"])
            except Exception:
                pass
                
        transacoes.append(Transacao(
            id=r["id"],
            tipo=r["tipo"],
            categoria=r["categoria"],
            valor=r["valor"],
            descricao=r["descricao"],
            data_vencimento=r["data_vencimento"],
            data_pagamento=r["data_pagamento"],
            status=r["status"],
            pagador_id=r["pagador_id"],
            moradores_dividem=dividem_ids,
            embedding=emb
        ))
    return transacoes

def inserir_transacao(t: Transacao) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    dividem_str = json.dumps(t.moradores_dividem)
    emb_str = json.dumps(t.embedding) if t.embedding else None
    
    cursor.execute(
        "INSERT INTO transacoes (tipo, categoria, valor, descricao, data_vencimento, data_pagamento, status, pagador_id, moradores_dividem, embedding) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (t.tipo, t.categoria, t.valor, t.descricao, t.data_vencimento, t.data_pagamento, t.status, t.pagador_id, dividem_str, emb_str)
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    
    # Recalcular saldos após alteração
    recalcular_saldos_moradores()
    return new_id

def atualizar_transacao(t: Transacao):
    conn = get_connection()
    cursor = conn.cursor()
    dividem_str = json.dumps(t.moradores_dividem)
    emb_str = json.dumps(t.embedding) if t.embedding else None
    
    cursor.execute(
        "UPDATE transacoes SET tipo=?, categoria=?, valor=?, descricao=?, data_vencimento=?, data_pagamento=?, status=?, pagador_id=?, moradores_dividem=?, embedding=? WHERE id=?",
        (t.tipo, t.categoria, t.valor, t.descricao, t.data_vencimento, t.data_pagamento, t.status, t.pagador_id, dividem_str, emb_str, t.id)
    )
    conn.commit()
    conn.close()
    recalcular_saldos_moradores()

def deletar_transacao(t_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM transacoes WHERE id=?", (t_id,))
    conn.commit()
    conn.close()
    recalcular_saldos_moradores()

# --- OPERAÇÕES DE RECORRÊNCIAS ---

def listar_recorrencias() -> List[Recorrencia]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM recorrencias ORDER BY dia_vencimento ASC")
    rows = cursor.fetchall()
    conn.close()
    
    recorp = []
    for r in rows:
        dividem_ids = []
        try:
            dividem_ids = json.loads(r["moradores_dividem"])
        except Exception:
            dividem_ids = [int(i) for i in r["moradores_dividem"].split(",") if i.strip()]
            
        recorp.append(Recorrencia(
            id=r["id"],
            categoria=r["categoria"],
            valor=r["valor"],
            descricao=r["descricao"],
            dia_vencimento=r["dia_vencimento"],
            pagador_id=r["pagador_id"],
            moradores_dividem=dividem_ids,
            ativa=bool(r["ativa"])
        ))
    return recorp

def inserir_recorrencia(rec: Recorrencia) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    dividem_str = json.dumps(rec.moradores_dividem)
    cursor.execute(
        "INSERT INTO recorrencias (categoria, valor, descricao, dia_vencimento, pagador_id, moradores_dividem, ativa) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (rec.categoria, rec.valor, rec.descricao, rec.dia_vencimento, rec.pagador_id, dividem_str, 1 if rec.ativa else 0)
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id

def atualizar_recorrencia(rec: Recorrencia):
    conn = get_connection()
    cursor = conn.cursor()
    dividem_str = json.dumps(rec.moradores_dividem)
    cursor.execute(
        "UPDATE recorrencias SET categoria=?, valor=?, descricao=?, dia_vencimento=?, pagador_id=?, moradores_dividem=?, ativa=? WHERE id=?",
        (rec.categoria, rec.valor, rec.descricao, rec.dia_vencimento, rec.pagador_id, dividem_str, 1 if rec.ativa else 0, rec.id)
    )
    conn.commit()
    conn.close()

def deletar_recorrencia(rec_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM recorrencias WHERE id=?", (rec_id,))
    conn.commit()
    conn.close()

# --- OPERAÇÕES DE FECHAMENTO MENSAL ---

def verificar_mes_fechado(mes_ano: str) -> bool:
    """Verifica se um mês está fechado (formato YYYY-MM)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM fechamentos WHERE mes_ano=?", (mes_ano,))
    fechado = cursor.fetchone()["count"] > 0
    conn.close()
    return fechado

def listar_fechamentos() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM fechamentos ORDER BY mes_ano DESC")
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(r) for r in rows]

def buscar_fechamento_detalhes(mes_ano: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM fechamentos WHERE mes_ano=?", (mes_ano,))
    f_row = cursor.fetchone()
    
    if not f_row:
        conn.close()
        return None
        
    fechamento = dict(f_row)
    
    # Pegar balanço dos moradores estático do fechamento
    cursor.execute("""
        SELECT fm.valor_balanco, m.nome, m.id as morador_id
        FROM fechamentos_moradores fm
        JOIN moradores m ON fm.morador_id = m.id
        WHERE fm.fechamento_id = ?
    """, (f_row["id"],))
    fm_rows = cursor.fetchall()
    conn.close()
    
    fechamento["balanco_moradores"] = [{"morador_id": r["morador_id"], "nome": r["nome"], "valor": r["valor_balanco"]} for r in fm_rows]
    return fechamento

def fechar_mes(mes_ano: str, fechado_por: str, total_entradas: float, total_saidas: float, saldo: float, total_pendente: float, balancos: List[Dict[str, Any]]) -> int:
    """Grava o fechamento do mês no banco de dados com valores estáticos."""
    import datetime
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Inserir fechamento principal
    fechado_em = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO fechamentos (mes_ano, total_entradas, total_saidas, saldo, total_pendente, fechado_em, fechado_por) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (mes_ano, total_entradas, total_saidas, saldo, total_pendente, fechado_em, fechado_por)
    )
    fechamento_id = cursor.lastrowid
    
    # 2. Inserir balanços estáticos por morador
    for b in balancos:
        cursor.execute(
            "INSERT INTO fechamentos_moradores (fechamento_id, morador_id, valor_balanco) VALUES (?, ?, ?)",
            (fechamento_id, b["morador_id"], b["valor"])
        )
        
    conn.commit()
    conn.close()
    recalcular_saldos_moradores()
    return fechamento_id

def reabrir_mes(mes_ano: str):
    """Remove o fechamento do mês (reabre)."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Pegar o ID do fechamento primeiro
    cursor.execute("SELECT id FROM fechamentos WHERE mes_ano=?", (mes_ano,))
    row = cursor.fetchone()
    if row:
        f_id = row["id"]
        # Deleta fechamento, os registros dependentes de fechamentos_moradores são removidos via ON DELETE CASCADE (se habilitado) ou faremos manualmente para garantir:
        cursor.execute("DELETE FROM fechamentos_moradores WHERE fechamento_id=?", (f_id,))
        cursor.execute("DELETE FROM fechamentos WHERE id=?", (f_id,))
        conn.commit()
        
    conn.close()
    recalcular_saldos_moradores()

# --- RECALCULADOR DE BALANÇOS DINÂMICOS ---

def recalcular_saldos_moradores():
    """
    Recalcula as contas fluidas de cada morador:
    Soma do que o morador pagou (em transações marcadas como 'pago') 
    subtraindo sua fração dividida em todas as transações ativas 
    (fora dos meses que já foram fechados e tiveram balanços congelados).
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Pegar todos os moradores
    cursor.execute("SELECT id FROM moradores")
    m_ids = [r["id"] for r in cursor.fetchall()]
    saldos = {m_id: 0.0 for m_id in m_ids}
    
    # 2. Encontrar meses fechados para pular transações deles
    cursor.execute("SELECT mes_ano FROM fechamentos")
    meses_fechados = set([r["mes_ano"] for r in cursor.fetchall()])
    
    # 3. Ler todas as transações
    cursor.execute("SELECT * FROM transacoes")
    tx_rows = cursor.fetchall()
    
    for tx in tx_rows:
        data_v_str = tx["data_vencimento"]
        mes_ano_tx = data_v_str[:7] if len(data_v_str) >= 7 else ""
        
        # Pular se o mês já está fechado (o saldo congelado é guardado estaticamente)
        if mes_ano_tx in meses_fechados:
            continue
            
        valor = tx["valor"]
        pagador_id = tx["pagador_id"]
        
        # Parse moradores que dividem
        try:
            dividem = json.loads(tx["moradores_dividem"])
        except Exception:
            dividem = [int(i) for i in tx["moradores_dividem"].split(",") if i.strip()]
            
        split_count = len(dividem)
        if split_count == 0:
            continue
            
        # Crédito para o pagador (se já pago)
        if tx["status"] == "pago" and pagador_id in saldos:
            saldos[pagador_id] += valor
            
        # Débito da divisão (para cada integrante da divisão)
        fatia = valor / split_count
        for r_id in dividem:
            if r_id in saldos:
                saldos[r_id] -= fatia
                
    # 4. Atualizar cada morador no banco
    for m_id, saldo in saldos.items():
        cursor.execute("UPDATE moradores SET saldo_atual=? WHERE id=?", (round(saldo, 2), m_id))
        
    conn.commit()
    conn.close()
