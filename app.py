import streamlit as st
import datetime
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Importar core
from core.database import (
    init_db, listar_moradores, listar_transacoes, verificar_mes_fechado,
    fechar_mes, reabrir_mes, buscar_fechamento_detalhes, recalcular_saldos_moradores
)
from core.rateio import calcular_acertos, calcular_resumo_mes
from core.utils import formatar_dinheiro, extrair_mes_ano_extenso, formatar_data_br

# Inicializar o banco de dados na primeira execução
init_db()
recalcular_saldos_moradores()

# Configuração da Página do Streamlit
st.set_page_config(
    page_title="Controle Financeiro Co-Living",
    page_icon="🏠",
    layout="wide",
)

# Estilização básica e container principal
st.markdown("<h1 style='text-align: center; color: #1e293b; font-family: sans-serif; font-weight: 800;'>🏠 Controle Financeiro Residencial</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #64748b; font-size: 14px;'>Gestão inteligente compartilhada de contas, rateio automático e conciliação de saldos</p>", unsafe_allow_html=True)
st.markdown("---")

# Barra de controle do painel - Seletor de Competência (Mês/Ano)
hoje = datetime.date.today()
meses_lista = [f"2026-{str(m).zfill(2)}" for m in range(1, 13)]
mes_atual_idx = meses_lista.index(hoje.strftime("%Y-%m")) if hoje.strftime("%Y-%m") in meses_lista else 5

# Colunas para filtros globais no topo
col_filt_1, col_filt_2 = st.columns([1, 3])
with col_filt_1:
    mes_selecionado = st.selectbox(
        "📅 Selecionar Mês / Competência",
        options=meses_lista,
        index=mes_atual_idx,
        format_func=extrair_mes_ano_extenso
    )

# Verificar se mês está fechado
mes_fechado = verificar_mes_fechado(mes_selecionado)

if mes_fechado:
    detalhes_fechamento = buscar_fechamento_detalhes(mes_selecionado)
    st.info(
        f"🔒 **Este mês está FECHADO e congelado!** "
        f"Competência liquidada em {formatar_data_br(detalhes_fechamento['fechado_em'])} por **{detalhes_fechamento['fechado_por']}**."
    )
else:
    st.success("🟢 **Competência Aberta** - Lançamentos e edições estão permitidos no momento.")

# Obter moradores e transações do mês selecionado
moradores = listar_moradores()
transacoes_todas = listar_transacoes()
transacoes_mes = [t for t in transacoes_todas if t.data_vencimento.startswith(mes_selecionado)]

# Se o mês estiver fechado, vamos ler as contas calculadas com base nos dados congelados, senão calculamos dinamicamente
resumo_mes = calcular_resumo_mes(transacoes_mes, moradores)

# --- PANEL INDICADORES DE KPI ---
st.subheader("📊 Indicadores Gerais - " + extrair_mes_ano_extenso(mes_selecionado))
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.metric(
        label="💰 Total Entradas (Caixa)",
        value=formatar_dinheiro(resumo_mes["total_entradas"]),
        help="Soma de todos os aportes ou receitas integradas do mês."
    )
with kpi2:
    st.metric(
        label="💸 Total Saídas (Despesas)",
        value=formatar_dinheiro(resumo_mes["total_saidas"]),
        delta_color="inverse",
        help="Soma de todas as contas, consumos ou rateios do mês."
    )
with kpi3:
    saldo_liquido = resumo_mes["saldo"]
    st.metric(
        label="⚖️ Saldo Líquido do Mês",
        value=formatar_dinheiro(saldo_liquido),
        help="Total Entradas subtraído do Total Saídas."
    )
with kpi4:
    st.metric(
        label="⚠️ Contas Pendentes de Pagamento",
        value=formatar_dinheiro(resumo_mes["total_pendente"]),
        help="Faturas em aberto que ainda não foram dadas como pagas."
    )

st.markdown("<br>", unsafe_allow_html=True)

# --- SEÇÃO BENTO GRID COM GRÁFICOS E ACERTO DE CONTAS ---
col_graf1, col_graf2 = st.columns([1, 1])

with col_graf1:
    st.subheader("🍕 Despesas por Categoria")
    if transacoes_mes:
        # Agrupar despesas por categoria
        despesas_mes = [t for t in transacoes_mes if t.tipo == "saida"]
        if despesas_mes:
            df_despesas = pd.DataFrame([
                {"Categoria": t.categoria, "Valor": t.valor} for t in despesas_mes
            ])
            df_agrupado = df_despesas.groupby("Categoria").sum().reset_index()
            fig = px.pie(
                df_agrupado,
                values="Valor",
                names="Categoria",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Slate
            )
            fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=300)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhuma despesa (saída) lançada neste mês.")
    else:
        st.info("Nenhuma movimentação lançada para gerar gráficos de despesa.")

with col_graf2:
    st.subheader("📈 Histórico dos Últimos 6 Meses")
    # Agrupar dados históricos
    historico_dados = []
    # Cria uma lista dos últimos 6 meses retroativos a partir de hoje
    hoje_ref = datetime.date.today()
    for offset in range(5, -1, -1):
        # Simplificação aproximada de meses retroativos
        m_offset = (hoje_ref.month - offset - 1) % 12 + 1
        y_offset = hoje_ref.year + (hoje_ref.month - offset - 1) // 12
        m_str = f"{y_offset}-{str(m_offset).zfill(2)}"
        
        txs_month = [t for t in transacoes_todas if t.data_vencimento.startswith(m_str)]
        calc_res = calcular_resumo_mes(txs_month, moradores)
        # Formata o rótulo para a legenda
        label_mes_graf = extrair_mes_ano_extenso(m_str).split(" de ")[0] + f"/{m_str[2:4]}"
        
        historico_dados.append({"Mês": label_mes_graf, "Tipo": "Entradas", "Valor": calc_res["total_entradas"]})
        historico_dados.append({"Mês": label_mes_graf, "Tipo": "Saídas", "Valor": calc_res["total_saidas"]})
        
    df_hist = pd.DataFrame(historico_dados)
    fig_hist = px.bar(
        df_hist,
        x="Mês",
        y="Valor",
        color="Tipo",
        barmode="group",
        color_discrete_map={"Entradas": "#10b981", "Saídas": "#ef4444"}
    )
    fig_hist.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=300)
    st.plotly_chart(fig_hist, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- ACERTO DE CONTAS (QUEM DEVE PARA QUEM) ---
st.subheader("🤝 Balanço Acordo do Mês (Quem deve para quem)")
st.caption("Reconciliação calculada dinamicamente com base nas diferenças entre o que foi efetivamente pago por cada morador "
           "e a quota-parte/rateio devida de todas as despesas da república.")

# Se o mês está fechado, lemos o balanço congelado, senão calculamos na hora
if mes_fechado and detalhes_fechamento:
    balancos_reconciliar = []
    # Simula um morador temporário
    class MoradorFechamento:
        def __init__(self, id, nome, saldo):
            self.id = id
            self.nome = nome
            self.saldo_atual = saldo
            
    for item in detalhes_fechamento["balanco_moradores"]:
        balancos_reconciliar.append(MoradorFechamento(item["morador_id"], item["nome"], item["valor"]))
    solucoes = calcular_acertos(balancos_reconciliar)
else:
    solucoes = calcular_acertos(moradores)

if solucoes:
    cols_sol = st.columns(len(solucoes) if len(solucoes) <= 4 else 4)
    for idx, s in enumerate(solucoes):
        col_atual = cols_sol[idx % len(cols_sol)]
        with col_atual:
            st.markdown(
                f"""
                <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; padding: 15px; border-radius: 12px; margin-bottom: 10px; border-left: 5px solid #3b82f6;">
                    <p style="margin: 0; font-size: 11px; color: #64748b; font-weight: bold; text-transform: uppercase;">Transferência {idx+1}</p>
                    <p style="margin: 5px 0 2px 0; font-size: 14px; font-weight: bold; color: #0f172a;">👥 <b>{s['de_nome']}</b></p>
                    <p style="margin: 0; font-size: 12px; color: #ef4444; font-weight: bold;">Deve transferir para:</p>
                    <p style="margin: 2px 0 5px 0; font-size: 14px; font-weight: bold; color: #0f172a;">👑 <b>{s['para_nome']}</b></p>
                    <hr style="margin: 8px 0; border: none; border-top: 1px solid #cbd5e1;">
                    <p style="margin: 0; font-size: 16px; font-weight: black; color: #10b981;">💰 {formatar_dinheiro(s['valor'])}</p>
                </div>
                """,
                unsafe_allow_html=True
            )
else:
    st.info("🎉 **Tudo liquidado!** Com as movimentações atuais deste mês, as frações de consumo bateram perfeitamente e ninguém precisa fazer transferências.")

st.markdown("<br>", unsafe_allow_html=True)

# --- TABELA DE CONTAS REGISTRADAS NO MÊS ---
st.subheader("📋 Transações Registradas na Competência")

if transacoes_mes:
    # Formatar dados das contas para exibir em uma tabela nativa amigável do Streamlit
    moradores_map = {m.id: m.nome for m in moradores}
    
    t_data = []
    for t in transacoes_mes:
        pagador_nome = moradores_map.get(t.pagador_id, "Desconhecido")
        split_names = [moradores_map.get(pid, "Desconhecido") for pid in t.moradores_dividem]
        status_fancy = "✅ Pago" if t.status == "pago" else "⏳ Pendente"
        
        t_data.append({
            "Vencimento": formatar_data_br(t.data_vencimento),
            "Descrição/Histórico": t.descricao,
            "Categoria": t.categoria,
            "Tipo": "Receita" if t.tipo == "entrada" else "Despesa",
            "Soma Total": formatar_dinheiro(t.valor),
            "Responsável (Pagou)": pagador_nome,
            "Rateado por": ", ".join(split_names),
            "Status": status_fancy,
            "Data de Pagamento": formatar_data_br(t.data_pagamento) if t.data_pagamento else "-"
        })
        
    df_v = pd.DataFrame(t_data)
    st.dataframe(
        df_v,
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("Nenhuma transação financeira registrada para esta competência ainda.")

st.markdown("<br>", unsafe_allow_html=True)

# --- SEÇÃO DE FECHAMENTO MENSAL E GERENCIAMENTO ---
st.subheader("⚙️ Ações e Encerramento Financeiro")

if not mes_fechado:
    st.write("Deseja fechar a contabilidade deste mês de forma estática? "
             "Isso congelará os balanços dos moradores para que as quitações não sofram perturbações "
             "caso transações passadas sejam editadas acidentalmente.")
    
    # Formulário para fechar mês
    with st.form("fechar_competencia_form"):
        col_form_1, col_form_2 = st.columns(2)
        with col_form_1:
            nome_fechador = st.text_input("💻 Quem está formalizando o encerramento?", value="João Silva", placeholder="Digite seu nome completo")
        with col_form_2:
            st.write("") # alinhamento vertical aproximado
            st.write("")
            confirmado = st.checkbox("Confirmo que as contas estão totalmente revisadas e acordadas.")
            
        submit_fechar = st.form_submit_button("🔒 Formalizar Fechamento Mensal", use_container_width=True)
        
        if submit_fechar:
            if not nome_fechador:
                st.error("Por favor, preencha o nome do responsável pelo encerramento.")
            elif not confirmado:
                st.error("Você precisa aceitar a declaração e marcar a caixa de confirmação para continuar.")
            else:
                if not transacoes_mes:
                    st.error("Não é possível fechar um mês que não possua nenhuma transação financeira.")
                else:
                    # Preparar os balanços individuais congelados
                    balancos_salvar = []
                    # Para cada morador calculamos seu balanco específico dentro DESTE MÊS selecionado
                    for m in moradores:
                        total_m_pagador = 0.0
                        total_m_devedor = 0.0
                        
                        for tx in transacoes_mes:
                            # Se participante dividiu
                            if m.id in tx.moradores_dividem:
                                split_count = len(tx.moradores_dividem)
                                if split_count > 0:
                                    fatia = tx.valor / split_count
                                    total_m_devedor += fatia
                                    
                            # Se participante pagou
                            if tx.status == "pago" and tx.pagador_id == m.id:
                                total_m_pagador += tx.valor
                                
                        balanco_liquido_mes = total_m_pagador - total_m_devedor
                        balancos_salvar.append({
                            "morador_id": m.id,
                            "valor": round(balanco_liquido_mes, 2)
                        })
                        
                    fechar_mes(
                        mes_ano=mes_selecionado,
                        fechado_por=nome_fechador,
                        total_entradas=resumo_mes["total_entradas"],
                        total_saidas=resumo_mes["total_saidas"],
                        saldo=resumo_mes["saldo"],
                        total_pendente=resumo_mes["total_pendente"],
                        balancos=balancos_salvar
                    )
                    st.success(f"Mês de {extrair_mes_ano_extenso(mes_selecionado)} encerrado de forma estática com sucesso!")
                    st.rerun()
else:
    # Exibe opção de reabrir
    st.write("Esta competência está devidamente travada. No entanto, se precisar efetuar correções em faturas passadas, você pode reabri-la:")
    with st.form("reaberta_form"):
        st.warning("⚠️ Atenção: Reabrir o mês fará com que os saldos de quitação acumulados voltem a flutuar dinamicamente.")
        botao_reabrir = st.form_submit_button("🔓 Reabrir Competência do Mês", use_container_width=True)
        if botao_reabrir:
            reabrir_mes(mes_selecionado)
            st.success(f"Competência de {extrair_mes_ano_extenso(mes_selecionado)} reaberta para edições. Saldos reajustados.")
            st.rerun()
