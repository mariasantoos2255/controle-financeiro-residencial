import streamlit as st
import datetime
from core.database import (
    listar_moradores, inserir_morador, atualizar_morador, deletar_morador, recalcular_saldos_moradores
)
from core.models import Morador
from core.utils import formatar_dinheiro, formatar_data_br

# Configuração da página
st.set_page_config(
    page_title="Gestão de Moradores",
    page_icon="👥",
    layout="wide"
)

st.markdown("<h1 style='color: #1e293b; font-family: sans-serif;'>👥 Participantes & Moradores</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #64748b; font-size: 14px;'>Gerencie as pessoas que residem na república e acompanhe os seus respectivos saldos e cotas financeiras do mês.</p>", unsafe_allow_html=True)
st.markdown("---")

# Sempre recalcular saldos dinâmicos ao entrar na página para evitar drifts
recalcular_saldos_moradores()

# Obter moradores
moradores = listar_moradores()

tab_ver, tab_adicionar, tab_editar = st.tabs(["👥 Integrantes Ativos", "➕ Adicionar Novo Morador", "📝 Editar Cadastro"])

# TAB 1: INTEGRANTES ATIVOS
with tab_ver:
    st.subheader("🏠 Integrantes Atuais da República")
    st.write("Abaixo estão listados os participantes registrados. O saldo acumulado reflete as despesas pagas subtraídas das quotas-partes consumidas.")
    
    if moradores:
        # Renderização em formato Grid / Colunas
        # Criamos colunas responsivas para os cartões
        cols_m = st.columns(3 if len(moradores) >= 3 else len(moradores))
        
        for idx, m in enumerate(moradores):
            col_atual = cols_m[idx % len(cols_m)]
            
            with col_atual:
                # Estilização visual do Card de acordo com o saldo (positivo = verde, negativo = vermelho, zerado = cinza)
                saldo = float(m.saldo_atual)
                if saldo > 0.01:
                    border_color = "#10b981" # Emerald
                    bg_color = "#f0fdf4"
                    txt_color = "#15803d"
                    status_lbl = "Credor (A receber)"
                elif saldo < -0.01:
                    border_color = "#ef4444" # Red
                    bg_color = "#fef2f2"
                    txt_color = "#b91c1c"
                    status_lbl = "Devedor (A transferir)"
                else:
                    border_color = "#cbd5e1" # Slate
                    bg_color = "#f8fafc"
                    txt_color = "#475569"
                    status_lbl = "Saldo Quitado"
                
                finance_role = "👑 Responsável Principal" if m.responsavel else "👥 Participante"
                
                st.markdown(
                    f"""
                    <div style="background-color: {bg_color}; border: 1px solid {border_color}; padding: 18px; border-radius: 16px; margin-bottom: 20px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05);">
                        <p style="margin: 0; font-size: 11px; color: #64748b; font-weight: bold; text-transform: uppercase;">{finance_role}</p>
                        <h3 style="margin: 4px 0 2px 0; color: #1e293b; font-family: sans-serif;">{m.nome}</h3>
                        <p style="margin: 0 0 8px 0; font-size: 13px; color: #64748b;">🛏️ {m.quarto or "Sem quarto definido"}</p>
                        <p style="margin: 0 0 12px 0; font-size: 11px; color: #94a3b8;">📅 Entrada em: {formatar_data_br(m.data_entrada)}</p>
                        <div style="background-color: white; border: 1px solid #e2e8f0; padding: 10px; border-radius: 10px;">
                            <p style="margin: 0; font-size: 10px; color: #94a3b8; font-weight: bold; text-transform: uppercase;">Saldo de Ajuste Atual</p>
                            <h4 style="margin: 2px 0; color: {txt_color}; font-size: 18px; font-weight: 800;">{formatar_dinheiro(m.saldo_atual)}</h4>
                            <p style="margin: 0; font-size: 11px; color: {txt_color}; font-weight: bold;">{status_lbl}</p>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
                # Botão nativo para deletar participante
                deletar_morador_btn = st.button(f"Excluir {m.nome.split()[0]} 🗑️", key=f"excluir_morador_{m.id}")
                if deletar_morador_btn:
                    sucesso_del = deletar_morador(m.id)
                    if sucesso_del:
                        st.success(f"Morador '{m.nome}' excluído do registro residencial!")
                        st.rerun()
                    else:
                        st.error(f"Não é possível excluir '{m.nome}' porque ele já possui lançamentos ou transações vinculadas no sistema de contas.")
    else:
        st.info("Nenhum morador cadastrado no sistema residencial. Adicione integrantes na aba correspondente.")


# TAB 2: CADASTRAR NOVO INTEGRANTE
with tab_adicionar:
    st.subheader("➕ Adicionar Novo Integrante à República")
    st.write("Complete as informações cadastrais para que o morador possa figurar nos lançamentos de despesas e nos cálculos automatizados de rateio.")
    
    with st.form("add_morador_form", clear_on_submit=True):
        col_m1, col_m2 = st.columns(2)
        
        with col_m1:
            nome_add = st.text_input("👤 Nome Completo", placeholder="Ex: João Silva da Cunha")
            quarto_add = st.text_input("🛏️ Quarto ou Acomodação", placeholder="Ex: Suíte Master, Quarto 1, Sótão")
            
        with col_m2:
            data_ent_add = st.date_input("📅 Data de Entrada / Mudança", value=datetime.date.today())
            responsavel_add = st.checkbox("👑 Definir como administrador / Responsável Geral das contas")
            
        submit_add = st.form_submit_button("💾 Salvar Novo Morador", use_container_width=True)
        
        if submit_add:
            if not nome_add.strip():
                st.error("Erro: O nome completo do morador é um parâmetro obrigatório.")
            else:
                novo_m = Morador(
                    id=None,
                    nome=nome_add.strip(),
                    quarto=quarto_add.strip(),
                    data_entrada=data_ent_add.strftime("%Y-%m-%d"),
                    saldo_atual=0.0,
                    responsavel=responsavel_add
                )
                inserir_morador(novo_m)
                st.success(f"Excelente! '{nome_add}' foi cadastrado com sucesso na casa!")
                st.rerun()


# TAB 3: EDITAR CADASTRO
with tab_editar:
    st.subheader("📝 Atualizar Informações Cadastrais")
    st.write("Selecione um dos integrantes ativos para retificar dados, alterar quarto ou modificar cargos administrativos.")
    
    if moradores:
        morador_selecionado_nome = st.selectbox(
            "Selecione o morador para editar",
            options=[m.nome for m in moradores]
        )
        
        # Encontrar objeto selecionado
        m_editar = next(m for m in moradores if m.nome == morador_selecionado_nome)
        
        with st.form("edit_morador_form"):
            col_ed1, col_ed2 = st.columns(2)
            
            with col_ed1:
                nome_ed = st.text_input("👤 Nome Completo", value=m_editar.nome)
                quarto_ed = st.text_input("🛏️ Quarto ou Acomodação", value=m_editar.quarto)
                
            with col_ed2:
                # Converter string ISO para data do Python para preencher o formulário
                try:
                    data_dt = datetime.datetime.strptime(m_editar.data_entrada, "%Y-%m-%d").date()
                except Exception:
                    data_dt = datetime.date.today()
                    
                data_ent_ed = st.date_input("📅 Data de Entrada / Mudança", value=data_dt)
                responsavel_ed = st.checkbox("👑 Definir como administrador / Responsável Geral das contas", value=m_editar.responsavel)
                
            submit_ed = st.form_submit_button("📝 Gravar Alterações Cadastrais", use_container_width=True)
            
            if submit_ed:
                if not nome_ed.strip():
                    st.error("Erro: O nome do morador não pode ser deixado em branco.")
                else:
                    m_editar.nome = nome_ed.strip()
                    m_editar.quarto = quarto_ed.strip()
                    m_editar.data_entrada = data_ent_ed.strftime("%Y-%m-%d")
                    m_editar.responsavel = responsavel_ed
                    
                    atualizar_morador(m_editar)
                    st.success(f"As alterações no cadastro de '{m_editar.nome}' foram gravadas com sucesso!")
                    st.rerun()
    else:
        st.info("Nenhum integrante cadastrado.")
