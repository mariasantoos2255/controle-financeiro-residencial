import streamlit as st
import datetime
from core.database import (
    listar_recorrencias, listar_moradores, listar_categorias, 
    inserir_recorrencia, atualizar_recorrencia, deletar_recorrencia,
    verificar_mes_fechado, inserir_transacao, listar_transacoes
)
from core.models import Recorrencia, Transacao
from core.utils import formatar_dinheiro

# Configuração da página
st.set_page_config(
    page_title="Contas Recorrentes",
    page_icon="🔁",
    layout="wide"
)

st.markdown("<h1 style='color: #1e293b; font-family: sans-serif;'>🔁 Contas Fixas e Recorrências</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #64748b; font-size: 14px;'>Gerencie contratos, faturas fixas ou assinaturas mensais da república que se repetem de maneira periódica.</p>", unsafe_allow_html=True)
st.markdown("---")

moradores = listar_moradores()
categorias = listar_categorias()
moradores_map = {m.id: m.nome for m in moradores}
categorias_nomes = [c.nome for c in categorias]

tab_listar, tab_criar = st.tabs(["🔁 Recorrências Configuradas", "➕ Configurar Nova Recorrência"])

# ABA 1: LISTAR RECORRÊNCIAS
with tab_listar:
    st.subheader("📋 Modelos de Custos Recorrentes")
    st.write("Estes lançamentos automáticos podem ser disparados para qualquer competência mensal desejada com apenas 1 clique.")
    
    recorrencias = listar_recorrencias()
    
    if recorrencias:
        # Oferecer seletor rápido para qual mês disparar as contas
        st.markdown("<div style='background-color: #f8fafc; border: 1px solid #e2e8f0; padding: 15px; border-radius: 12px; margin-bottom: 25px;'>", unsafe_allow_html=True)
        col_trigger_1, col_trigger_2 = st.columns([1, 2])
        with col_trigger_1:
            mes_disparo_lan = st.selectbox(
                "📅 Mês de Destino dos Lançamentos:",
                options=[f"2026-{str(m).zfill(2)}" for m in range(1, 13)],
                index=datetime.date.today().month - 1
            )
        with col_trigger_2:
            st.write("") # alinhamento
            st.write("")
            st.caption("ℹ️ Selecione o mês acima e dispare qualquer uma das despesas fixas abaixo de forma autônoma para aquela competência.")
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Grid/Lista de Recorrências
        for r in recorrencias:
            c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
            
            with c1:
                col_role = "🟢 Ativa" if r.ativa else "🔴 Suspensa/Pausada"
                st.markdown(f"**🔁 {r.descricao}** ({r.categoria})")
                st.caption(f"Fatura padrão: **{formatar_dinheiro(r.valor)}** | Vencimento todo dia **{r.dia_vencimento}**")
                
            with c2:
                # Mostrar quem pagará e dividirá
                p_nome = moradores_map.get(r.pagador_id, "Desconhecido")
                divisores = [moradores_map.get(pid, "Desconhecido") for pid in r.moradores_dividem]
                st.caption(f"Devedor pagador padrão: **{p_nome}**")
                st.caption(f"Rateado entre: *{', '.join(divisores)}*")
                
            with c3:
                # Botão interativo para Ativar/Desativar
                slug_status_text = "Pausar Recorrência ⏸️" if r.ativa else "Ativar Recorrência ▶️"
                toggle_btn = st.button(slug_status_text, key=f"toggle_rec_{r.id}")
                if toggle_btn:
                    r.ativa = not r.ativa
                    atualizar_recorrencia(r)
                    st.success(f"Recorrência '{r.descricao}' foi atualizada!")
                    st.rerun()
                    
            with c4:
                # Botão para disparar lançamento real
                if r.ativa:
                    trigger_btn = st.button("🚀 Gerar Lançamento no Mês", key=f"trigger_rec_{r.id}", type="primary")
                    if trigger_btn:
                        # Verificar se o mês de destino está fechado
                        if verificar_mes_fechado(mes_disparo_lan):
                            st.error(f"Erro: O mês {mes_disparo_lan} está FECHADO e selado para novos registros!")
                        else:
                            # Evitar duplicados no mesmo mês (com mesma descrição e valor)
                            transacoes_existentes = listar_transacoes(mes_ano=mes_disparo_lan)
                            duplicada = any(
                                tx.descricao.lower() == r.descricao.lower() and 
                                abs(tx.valor - r.valor) < 0.01 
                                for tx in transacoes_existentes
                            )
                            
                            if duplicada:
                                st.warning(f"Atenção: Um lançamento para '{r.descricao}' de valor equivalente já existe registrado em {mes_disparo_lan}!")
                            else:
                                # Montar data completa
                                dia_str = str(r.dia_vencimento).zfill(2)
                                data_completa = f"{mes_disparo_lan}-{dia_str}"
                                
                                # Gerar embedding para busca
                                from core.gemini_client import gerar_embedding
                                emb_v = gerar_embedding(f"{r.descricao} {r.categoria}")
                                
                                nova_tx = Transacao(
                                    id=None,
                                    tipo="saida",
                                    categoria=r.categoria,
                                    valor=r.valor,
                                    descricao=r.descricao,
                                    data_vencimento=data_completa,
                                    data_pagamento=None,
                                    status="pendente",
                                    pagador_id=r.pagador_id,
                                    moradores_dividem=r.moradores_dividem,
                                    embedding=emb_v
                                )
                                
                                inserir_transacao(nova_tx)
                                st.success(f"Sucesso! Lançamento de despesa '{r.descricao}' criado para {mes_disparo_lan} com status pendente.")
                                st.rerun()
                
                # Expor exclusão de modelo
                delete_rec_btn = st.button("Excluir Modelo 🗑️", key=f"del_rec_{r.id}")
                if delete_rec_btn:
                    deletar_recorrencia(r.id)
                    st.warning(f"Recorrência '{r.descricao}' removida!")
                    st.rerun()
                    
            st.markdown("<hr style='margin: 10px 0; border: none; border-top: 1px solid #e2e8f0;'>", unsafe_allow_html=True)
    else:
        st.info("Nenhuma recorrência de conta cadastrada nesta república ainda.")


# ABA 2: CRIAR NOVA RECORRÊNCIA
with tab_criar:
    st.subheader("➕ Configurar Contrato ou Custo Recorrente")
    st.write("Cumpra os parâmetros do modelo para que faturas periódicas possam ser clonadas de maneira rápida todo mês.")
    
    with st.form("add_recorr_form", clear_on_submit=True):
        col_rec1, col_rec2 = st.columns(2)
        
        with col_rec1:
            desc_rec = st.text_input("📝 Descrição do Custo Fixo", placeholder="Ex: Mensalidade Copasa Água, Mensalidade Fibra Óptica")
            cat_rec = st.selectbox("🏷️ Categoria", options=categorias_nomes)
            valor_rec = st.number_input("💰 Valor Estimado Padrão (R$)", min_value=0.01, step=10.00, format="%.2f")
            
        with col_rec2:
            dia_venc_rec = st.number_input("📅 Dia Estimado de Vencimento (1 a 28)", min_value=1, max_value=28, value=10, step=1)
            pagador_rec = st.selectbox(
                "👤 Devedor principal responsável pelo pagamento",
                options=[m.id for m in moradores],
                format_func=lambda pid: moradores_map.get(pid, f"ID {pid}")
            )
            divisores_rec = st.multiselect(
                "👥 Integrantes participantes da divisão (Rateio)",
                options=[m.id for m in moradores],
                default=[m.id for m in moradores],
                format_func=lambda pid: moradores_map.get(pid, f"ID {pid}")
            )
            
        submit_rec = st.form_submit_button("🔁 Gravar Modelo de Recorrência", use_container_width=True)
        
        if submit_rec:
            if not desc_rec.strip():
                st.error("Erro: A descrição curta da conta fixa/recorrente é obrigatória.")
            elif not divisores_rec:
                st.error("Erro: Selecione pelo menos 1 morador para figurar no rateio.")
            else:
                nova_r = Recorrencia(
                    id=None,
                    categoria=cat_rec,
                    valor=valor_rec,
                    descricao=desc_rec.strip(),
                    dia_vencimento=int(dia_venc_rec),
                    pagador_id=pagador_rec,
                    moradores_dividem=divisores_rec,
                    ativa=True
                )
                inserir_recorrencia(nova_r)
                st.success(f"Excelente! O modelo recorrente de '{desc_rec}' de {formatar_dinheiro(valor_rec)} foi registrado com sucesso.")
                st.rerun()
