import streamlit as st
import datetime
from core.database import (
    listar_transacoes, listar_moradores, listar_categorias, 
    inserir_transacao, atualizar_transacao, deletar_transacao, verificar_mes_fechado
)
from core.models import Transacao
from core.utils import formatar_dinheiro, formatar_data_br
from core.embeddings import buscar_semantica

# Configuração da página
st.set_page_config(
    page_title="Lançamentos Financeiros",
    page_icon="📋",
    layout="wide"
)

st.markdown("<h1 style='color: #1e293b; font-family: sans-serif;'>📋 Livro de lançamentos e Contas</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #64748b; font-size: 14px;'>Consulte contas registradas, filtre transações por buscas normais e vetoriais ou adicione faturas manualmente de forma autônoma.</p>", unsafe_allow_html=True)
st.markdown("---")

# Abas funcionais estruturadas
tab_listar, tab_novo = st.tabs(["🔍 Filtrar & Listar Saldos", "➕ Registrar Lançamento Manual"])

moradores = listar_moradores()
categorias = listar_categorias()
moradores_map = {m.id: m.nome for m in moradores}
categorias_nomes = [c.nome for c in categorias]

# ABA 1: LISTAR E FILTRAR TRANSAÇÕES
with tab_listar:
    # Seção de Filtros
    col_filt1, col_filt2, col_filt3, col_filt4 = st.columns([2, 1, 1, 1])
    
    with col_filt1:
        termo_busca = st.text_input("📝 Busca textual / Pesquisa Semântica (Rover AI)", placeholder="Ex: conta de luz, mercado, joão pagou")
        
    with col_filt2:
        filtro_status = st.selectbox("🚦 Status", options=["Todos", "Pago", "Pendente"])
        
    with col_filt3:
        filtro_cat = st.selectbox("🏷️ Categoria", options=["Todas"] + categorias_nomes)
        
    with col_filt4:
        filtro_tipo = st.selectbox("🧭 Direção", options=["Todos", "Entrada (Receita)", "Saída (Despesa)"])

    # Obter transações gerais
    transacoes = listar_transacoes()
    
    # Se termo de busca foi digitado, processamos via algoritmo de busca semântica em /core/embeddings.py
    if termo_busca.strip():
        # Retorna lista de tuplas (Transacao, similaridade)
        resultados_busca = buscar_semantica(termo_busca, transacoes, top_k=50)
        # Filtra as transações com similaridade satisfatória (> 0.2 ou se for busca por texto simples)
        transacoes_filtradas = [t for t, score in resultados_busca if score > 0.15]
    else:
        transacoes_filtradas = transacoes

    # Aplicar filtros secundários na lista final
    if filtro_status != "Todos":
        status_slug = "pago" if filtro_status == "Pago" else "pendente"
        transacoes_filtradas = [t for t in transacoes_filtradas if t.status == status_slug]
        
    if filtro_cat != "Todas":
        transacoes_filtradas = [t for t in transacoes_filtradas if t.categoria == filtro_cat]
        
    if filtro_tipo != "Todos":
        tipo_slug = "entrada" if "Entrada" in filtro_tipo else "saida"
        transacoes_filtradas = [t for t in transacoes_filtradas if t.tipo == tipo_slug]

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader(f"📑 Transações Encontradas ({len(transacoes_filtradas)})")
    
    if transacoes_filtradas:
        # Tabela interativa com ações detalhadas (exibe cada transação individualmente para controle granular)
        for t in transacoes_filtradas:
            # Layout em colunas para simular uma linha de tabela robusta com botões clicáveis
            c1, c2, c3, c4, c5 = st.columns([2, 3, 2, 2, 1])
            
            # Dados da conta
            with c1:
                st.markdown(f"**📅 {formatar_data_br(t.data_vencimento)}** ({t.categoria})")
                st.caption(f"Inserido por ID pagador {t.pagador_id}: *{moradores_map.get(t.pagador_id, 'Membro Excluído')}*")
                
            with c2:
                st.markdown(f"💬 **{t.descricao}**")
                # Exibe quem divide de forma curta
                quem_divide = [moradores_map.get(pid, f"ID {pid}") for pid in t.moradores_dividem]
                st.caption(f"Fatiará por: {', '.join(quem_divide)}")
                
            with c3:
                # Cor para entradas vs saídas
                is_entrada = t.tipo == "entrada"
                pref = "+" if is_entrada else "-"
                cor_fin = "green" if is_entrada else "red"
                val_formatado = formatar_dinheiro(t.valor)
                st.markdown(f"<span style='color:{cor_fin}; font-weight:800; font-size:15px;'>{pref} {val_formatado}</span>", unsafe_allow_html=True)
                if t.data_pagamento:
                    st.caption(f"Quitado em: {formatar_data_br(t.data_pagamento)}")
                else:
                    st.caption("Aguardando quitação")
                    
            with c4:
                # Botão interativo para alternar o status diretamente da lista
                status_atual_pago = t.status == "pago"
                emoji_status = "✅ PAGO" if status_atual_pago else "⏳ PENDENTE"
                cor_btn = "success" if status_atual_pago else "warning"
                
                # Desativa ação caso a competência já esteja trancada
                mes_v = t.data_vencimento[:7]
                locked_month = verificar_mes_fechado(mes_v)
                
                if locked_month:
                    st.markdown(f"<p style='color:#64748b; font-size:11px; font-weight:bold; margin-top:10px;'>🔒 CONGELADO</p>", unsafe_allow_html=True)
                else:
                    # Botão para alternar status
                    alt_status = st.button(
                        f"{emoji_status}", 
                        key=f"status_btn_{t.id}", 
                        help="Clique para alternar quitação de forma instantânea"
                    )
                    if alt_status:
                        t.status = "pendente" if status_atual_pago else "pago"
                        # Se mudou para pago, bota data de pagamento como hoje, senão limpa
                        t.data_pagamento = datetime.date.today().strftime("%Y-%m-%d") if t.status == "pago" else None
                        atualizar_transacao(t)
                        st.success(f"Status do lançamento '{t.descricao}' alterado!")
                        st.rerun()
                        
            with c5:
                # Botão para deletar conta
                if not locked_month:
                    del_btn = st.button("🗑️", key=f"del_btn_{t.id}", help="Deletar este registro financeiro definitivamente")
                    if del_btn:
                        deletar_transacao(t.id)
                        st.warning(f"Lançamento financeiro '{t.descricao}' excluído!")
                        st.rerun()
                else:
                    st.write("")
                    
            st.markdown("<hr style='margin: 8px 0; border: none; border-top: 1px solid #cbd5e1/40;'>", unsafe_allow_html=True)
    else:
        st.info("Nenhuma conta financeira corresponde aos filtros selecionados.")


# ABA 2: REGISTRAR LANÇAMENTO MANUAL
with tab_novo:
    st.subheader("📝 Cadastrar Nova Despesa ou Receita Manual")
    st.write("Insira as informações básicas para que as contas fluam para o fechamento mensal e o saldo dos moradores seja atualizado automaticamente.")
    
    with st.form("manual_transaction_form", clear_on_submit=True):
        col_form1, col_form2 = st.columns(2)
        
        with col_form1:
            tipo_lan = st.selectbox("🧭 Tipo de Lançamento", options=["Despesa (Saída da república)", "Receita (Entrada em caixa)"])
            
            cat_lan = st.selectbox("🏷️ Selecionar Categoria", options=categorias_nomes)
            
            valor_lan = st.number_input("💰 Valor Total (R$)", min_value=0.01, step=5.00, format="%.2f")
            
            desc_lan = st.text_input("📸 Descrição Curta (Histórico)", placeholder="Ex: Fatura Internet Vivo, Faxina Quatorzenal")
            
        with col_form2:
            data_venc = st.date_input("📅 Data de Vencimento", value=datetime.date.today())
            
            status_lan = st.selectbox("🚦 Status Inicial", options=["Pendente (Não pago ainda)", "Pago (Disparado no caixa)"])
            
            # Se status for pago, exibe input de data de pagamento
            data_pago = None
            if "Pago" in status_lan:
                data_pago = st.date_input("🗓️ Data Efetiva de Pagamento", value=datetime.date.today())
                
            pagador_lan = st.selectbox(
                "👤 Quem efetuou / pagará essa conta?", 
                options=[m.id for m in moradores],
                format_func=lambda pid: moradores_map.get(pid, f"ID {pid}")
            )
            
            divisores_lan = st.multiselect(
                "👥 Quem dividirá o valor desta conta? (Rateio)",
                options=[m.id for m in moradores],
                default=[m.id for m in moradores],
                format_func=lambda pid: moradores_map.get(pid, f"ID {pid}"),
                help="Selecione quais moradores farão parte da divisão desta despesa."
            )
            
        submit_form = st.form_submit_button("💾 Salvar Lançamento Financeiro", use_container_width=True)
        
        if submit_form:
            # Validações primárias
            if not desc_lan.strip():
                st.error("Erro: A descrição curta/Histórico da transação é obrigatória.")
            elif not divisores_lan:
                st.error("Erro: Você deve selecionar pelo menos 1 morador para fazer parte do rateio desta conta.")
            else:
                tipo_slug = "entrada" if "Receita" in tipo_lan else "saida"
                status_slug = "pago" if "Pago" in status_lan else "pendente"
                data_venc_str = data_venc.strftime("%Y-%m-%d")
                data_pag_str = data_pago.strftime("%Y-%m-%d") if ("Pago" in status_lan and data_pago) else None
                
                # Verificar se o mês de vencimento está fechado
                mes_venc = data_venc_str[:7]
                if verificar_mes_fechado(mes_venc):
                    st.error(f"Erro: O mês de lançamento ({mes_venc}) está FECHADO e bloqueado para edições!")
                else:
                    # Chamar geração automática de embedding em background para busca semântica em /core/chatbot.py
                    from core.gemini_client import gerar_embedding
                    emb_vetor = gerar_embedding(f"{desc_lan} {cat_lan}")
                    
                    nova_tx = Transacao(
                        id=None,
                        tipo=tipo_slug,
                        categoria=cat_lan,
                        valor=valor_lan,
                        descricao=desc_lan,
                        data_vencimento=data_venc_str,
                        data_pagamento=data_pag_str,
                        status=status_slug,
                        pagador_id=pagador_lan,
                        moradores_dividem=divisores_lan,
                        embedding=emb_vetor
                    )
                    
                    inserir_transacao(nova_tx)
                    st.success(f"Excelente! O lançamento '{desc_lan}' de {formatar_dinheiro(valor_lan)} foi adicionado e fatiado entre os moradores selecionados.")
                    st.rerun()
