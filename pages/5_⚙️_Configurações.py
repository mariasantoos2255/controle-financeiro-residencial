import streamlit as st
import os
from core.database import listar_categorias, inserir_categoria, init_db, DB_NAME
from core.models import Categoria
from core.gemini_client import get_gemini_api_key, testar_api_key, gerar_embedding

# Configuração da página
st.set_page_config(
    page_title="Preferências & Configurações",
    page_icon="⚙️",
    layout="wide"
)

st.markdown("<h1 style='color: #1e293b; font-family: sans-serif;'>⚙️ Preferências & Configurações</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #64748b; font-size: 14px;'>Ajuste as configurações do sistema, crie novas nomenclaturas de categoria e faça o diagnóstico de integridade da IA.</p>", unsafe_allow_html=True)
st.markdown("---")

tab_conexoes, tab_categorias, tab_diagnostico = st.tabs(["🔑 Chaves e Conexões", "🏷️ Gestão de Categorias", "🔬 Diagnóstico de Banco"])

# TAB 1: CHAVES E CONEXÕES
with tab_conexoes:
    st.subheader("🔑 Conexão com a Inteligência Artificial (Gemini)")
    st.write("A plataforma de AI Studio já fornece a chave do Gemini de forma automática. No entanto, se estiver executando remotamente, você pode calibrar a chave aqui.")
    
    # Conferir integridade da chave do Gemini
    chave_detectada = get_gemini_api_key()
    
    if chave_detectada:
        # Mascarar chave para segurança
        chave_mascarada = chave_detectada[:6] + "..." + chave_detectada[-4:] if len(chave_detectada) > 10 else "Ativa"
        st.success(f"🤖 **Status da IA:** Conectada! Chave de API detectada: `{chave_mascarada}`")
        
        # Oferecer botão de testes
        if st.button("🔬 Executar Teste de Conexão Vetorial"):
            with st.spinner("Sincronizando vetor dimensional..."):
                emb_teste = gerar_embedding("teste de conexao")
                if emb_teste:
                    st.success("✅ Teste bem-sucedido! O modelo 'text-embedding-004' retornou as dimensões de forma esperada.")
                else:
                    st.error("❌ O teste falhou. Embora a chave existisse, o serviço de embeddings não funcionou ou restou bloqueado.")
    else:
        st.warning("⚠️ **Status da IA:** Chave de API do Gemini não detectada nas variáveis globais.")
        st.write("Para habilitar o assistente virtual Rover, a indexação de buscas semânticas e a interpretação inteligente de diálogos em linguagem natural, acesse o menu de Segredos/Configurações do **AI Studio** e insira seu segredo `GEMINI_API_KEY`.")
        
        # Campo para entrada de bypass local temporário se desejarem
        over_key = st.text_input("🔑 Chave Temporária do Gemini (Gravar no Session State)", type="password")
        if st.button("💾 Aplicar Chave Local"):
            if over_key.strip():
                os.environ["GEMINI_API_KEY"] = over_key.strip()
                st.success("Chave local aplicada no ambiente do servidor!")
                st.rerun()


# TAB 2: GESTÃO DE CATEGORIAS
with tab_categorias:
    st.subheader("🏷️ Categorias de Despesas e Receitas")
    st.write("Crie categorias personalizadas para melhor classificar as faturas de consumo de sua república.")
    
    # Listar categorias existentes
    categorias = listar_categorias()
    
    col_cat_1, col_cat_2 = st.columns([1, 1])
    
    with col_cat_1:
        st.markdown("**Lista de Categorias Cadastradas:**")
        # Mostrar em um dataframe nativo elegante
        df_cats = [{"Nome": c.nome, "Fluxo/Tipo": "Receita (Entrada)" if c.tipo == "entrada" else "Despesa (Saída)"} for c in categorias]
        st.dataframe(df_cats, use_container_width=True, hide_index=True)
        
    with col_cat_2:
        st.markdown("**➕ Criar Nova Categoria Personalizada:**")
        with st.form("custom_category_form", clear_on_submit=True):
            nome_cat = st.text_input("Nome da Categoria", placeholder="Ex: Diarista, Gás, Academia")
            tipo_cat = st.selectbox("Tipo de Lançamento", options=["Despesa (Saída/Custo)", "Receita (Entrada/Cota)"])
            
            submit_cat = st.form_submit_button("💾 Salvar Categoria", use_container_width=True)
            
            if submit_cat:
                if not nome_cat.strip():
                    st.error("Erro: O nome da categoria não pode ser deixado em branco.")
                else:
                    tipo_slug = "entrada" if "Entrada" in tipo_cat else "saida"
                    cat_nova = Categoria(id=None, nome=nome_cat.strip(), tipo=tipo_slug)
                    
                    sub_id = inserir_categoria(cat_nova)
                    if sub_id:
                        st.success(f"Categoria '{nome_cat.strip()}' criada com sucesso!")
                        st.rerun()
                    else:
                        st.error(f"Erro: Uma categoria com o nome '{nome_cat.strip()}' já está cadastrada no sistema.")


# TAB 3: DIAGNÓSTICO DO BANCO
with tab_diagnostico:
    st.subheader("🔬 Estrutura de Armazenamento Local")
    st.write("A base de dados atual é persistida em uma base SQLite relacional segura e leve dentro do container de execução.")
    
    col_diag_1, col_diag_2 = st.columns(2)
    with col_diag_1:
        st.metric(label="📁 Nome do Banco de Dados", value=DB_NAME)
        st.write(f"Caminho absoluto: `{os.path.abspath(DB_NAME)}`")
        
    with col_diag_2:
        # Se houver banco, tamanho aproximado do arquivo em KB
        if os.path.exists(DB_NAME):
            tamanho_kb = os.path.getsize(DB_NAME) / 1024
            st.metric(label="🔋 Espaço em Disco Ocupado", value=f"{tamanho_kb:.2f} KB")
        else:
            st.metric(label="🔋 Espaço em Disco Ocupado", value="0 KB", delta="Inexistente - Gerar")
            
    # Botão para reinicializar banco de dados do zero se quiserem brincar
    st.markdown("<hr>", unsafe_allow_html=True)
    st.warning("⚠️ **CUIDADO - ZONA DE PERIGO:** Reinicializar o banco de dados apagará todas as transações, moradores e fechamentos estáticos existentes, retornando o sistema aos dados de exemplo originais.")
    
    with st.form("reset_database_safeguard"):
        confirmou = st.checkbox("Eu entendo que essa ação é irreversível e apagará todos os dados financeiros registrados.")
        botao_reset = st.form_submit_button("🔥 EXCLUIR E REINICIALIZAR BANCO DE DADOS", use_container_width=True)
        
        if botao_reset:
            if confirmou:
                if os.path.exists(DB_NAME):
                    os.remove(DB_NAME)
                init_db()
                st.success("O banco de dados SQLite foi deletado e reinicializado com sucesso! Os moradores e categorias modelo originais foram recriados.")
                st.rerun()
            else:
                st.error("Erro: Você deve marcar a caixa de confirmação para poder prosseguir com a exclusão total.")
