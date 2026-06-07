import streamlit as st
import datetime
from core.database import (
    listar_moradores, listar_categorias, inserir_transacao, verificar_mes_fechado
)
from core.models import Transacao
from core.chatbot import processar
from core.utils import formatar_dinheiro, formatar_data_br

# Configuração da página
st.set_page_config(
    page_title="Rover Chatbot - Finanças",
    page_icon="💬",
    layout="wide"
)

st.markdown("<h1 style='color: #1e293b; font-family: sans-serif;'>💬 Rover - Inteligência Co-Living</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #64748b; font-size: 14px;'>Converse com o Rover para lançar despesas de forma imediata ou tirar dúvidas inteligentes sobre as contas da residência.</p>", unsafe_allow_html=True)
st.markdown("---")

# Inicialização de Mensagens do Chat histórico
if "mensagens" not in st.session_state:
    st.session_state.mensagens = [
        {
            "role": "assistant",
            "content": "Olá! Eu sou o **Rover**, o assistente inteligente da República. 🤖☕\n\nEstou aqui para agilizar sua vida. Pode me enviar comandos de voz transcritos ou diálogos diretos para eu interpretar. Exemplos:\n"
                       "- *'Comprei botijão de gás por 130 reais'* \n"
                       "- *'Lança a conta de luz de 250 de junho para pagar'* \n"
                       "- *'Maria pagou o aluguel dela de 800'* \n"
                       "- *'Quanto cada um deve este mês?'*\n\n"
                       "Como posso te apoiar agora?"
        }
    ]

# Inicialização de draft ativo para transações via conversa
if "rascunho_ativo" not in st.session_state:
    st.session_state.rascunho_ativo = None

# Exibição do histórico de mensagens utilizando componentes de chat nativos
for msg in st.session_state.mensagens:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Tratamento do Lançamento de Rascunho se houver um ativo
if st.session_state.rascunho_ativo:
    st.markdown("<br>", unsafe_allow_html=True)
    st.info("⚡ **Rascunho de Transação Detectado!** Verifique as informações extraídas pelo Rover antes de gravar:")
    
    draft = st.session_state.rascunho_ativo
    
    # Mapeamentos amigáveis
    moradores = listar_moradores()
    moradores_map = {m.id: m.nome for m in moradores}
    nome_pagador = moradores_map.get(draft.get("pagador_id"), "Desconhecido")
    
    col_draft1, col_draft2, col_draft3 = st.columns(3)
    with col_draft1:
        st.write(f"📝 **Fato/Histórico:** {draft.get('descricao')}")
        st.write(f"🏷️ **Categoria:** {draft.get('categoria')}")
    with col_draft2:
        st.write(f"💰 **Valor sugerido:** {formatar_dinheiro(draft.get('valor'))}")
        st.write(f"👤 **Responsável pelo pagamento:** {nome_pagador}")
    with col_draft3:
        st.write(f"📅 **Vencimento do lançamento:** {formatar_data_br(draft.get('data_vencimento'))}")
        st.write(f"⚙️ **Status pós-registro:** {draft.get('status').upper()}")
        
    st.write("Participantes do rateio:", ", ".join([moradores_map.get(pid, "Desconhecido") for pid in draft.get("moradores_dividem", [])]))
    
    # Botões para salvar ou descartar
    col_btn1, col_btn2 = st.columns([1, 4])
    with col_btn1:
        confirmar_salvar = st.button("Sim, Salvar no Mês ✅", use_container_width=True, type="primary")
    with col_btn2:
        descartar_draft = st.button("Descartar rascunho ❌")
        
    if confirmar_salvar:
        # Verificar se o mês de vencimento está fechado antes de permitir
        mes_v = draft.get("data_vencimento")[:7]
        if verificar_mes_fechado(mes_v):
            st.error("Desculpe, o mês deste lançamento já está fechado e bloqueado para modificações!")
        else:
            nova_tx = Transacao(
                id=None,
                tipo=draft.get("tipo", "saida"),
                categoria=draft.get("categoria", "Outros"),
                valor=draft.get("valor", 0.0),
                descricao=draft.get("descricao", "Lançamento"),
                data_vencimento=draft.get("data_vencimento"),
                data_pagamento=draft.get("data_pagamento"),
                status=draft.get("status", "pendente"),
                pagador_id=draft.get("pagador_id"),
                moradores_dividem=draft.get("moradores_dividem", []),
                embedding=None
            )
            inserir_transacao(nova_tx)
            st.success("Transação gravada e rateada no banco SQLite com sucesso! Os balanços individuais foram recalibrados.")
            st.session_state.rascunho_ativo = None
            st.rerun()
            
    if descartar_draft:
        st.session_state.rascunho_ativo = None
        st.warning("O rascunho de lançamento foi descartado.")
        st.rerun()

# Espaço inferior para o input
prompt = st.chat_input("Digite sua mensagem para o Rover...")

if prompt:
    # Insere no histórico visual de forma instantânea
    st.session_state.mensagens.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
        
    # Processa via Rover / Gemini
    with st.spinner("Rover está processando e consultando os dados... 🤖"):
        # Chama módulo inteligente Python
        resposta_rover = processar(prompt, st.session_state.mensagens[:-1])
        
    # Exibe resposta no chat
    answer = resposta_rover.get("answer", "Infelizmente não entendi.")
    st.session_state.mensagens.append({"role": "assistant", "content": answer})
    
    with st.chat_message("assistant"):
        st.write(answer)
        
    # Se gerou um rascunho válido, salva na sessão para as ações e botões
    if resposta_rover.get("intent") == "create_transaction" and resposta_rover.get("transaction_draft"):
        st.session_state.rascunho_ativo = resposta_rover["transaction_draft"]
        
    st.rerun()
