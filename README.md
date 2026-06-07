# 🏠 Controle Financeiro Residencial

Aplicação em **Python + Streamlit** para gestão financeira compartilhada entre moradores de uma residência (república, casa, apartamento). Usa a **API do Google Gemini** para chatbot conversacional e busca semântica nas transações.

## ✨ Funcionalidades

- 📊 **Resumo Mensal** — Dashboard com KPIs, gráficos por categoria e histórico
- 💬 **Chatbot (Rover)** — Lance despesas em linguagem natural: *"comprei gás por 130, divide entre todos"*
- 📋 **Transações** — CRUD completo com filtros e busca semântica via embeddings
- 👥 **Moradores** — Cadastro e acerto de contas (quem deve para quem)
- 🔁 **Recorrências** — Contas fixas mensais (aluguel, internet, condomínio)
- 🔒 **Fechamento de mês** — Congela balanços e impede alterações retroativas

## 🛠 Stack

- **Python 3.10+**
- **Streamlit** (interface)
- **SQLite** (persistência local)
- **Google Gemini API** (`gemini-1.5-flash` para chat, `text-embedding-004` para busca semântica)
- **Plotly** (gráficos)

## 📦 Instalação

### 1. Clone o repositório

```bash
git clone https://github.com/SEU_USUARIO/controle-financeiro-residencial.git
cd controle-financeiro-residencial
```

### 2. Crie um ambiente virtual (recomendado)

```bash
python -m venv venv
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Configure a chave da API

Pegue uma chave grátis em https://aistudio.google.com/app/apikey, depois:

```bash
cp .env.example .env
```

Edite o `.env` e coloque sua chave:

```env
GEMINI_API_KEY=sua_chave_aqui
```

### 5. Execute

```bash
streamlit run app.py
```

Acesse no navegador: **http://localhost:8501**

Na primeira execução, o banco `financeiro.db` é criado automaticamente com 3 moradores e 10 categorias de exemplo.

## 📁 Estrutura

```
controle-financeiro-residencial/
├── app.py                      # Página inicial (Resumo Mensal)
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
│
├── pages/                      # Páginas adicionais do Streamlit
│   ├── 1_💬_Chat.py
│   ├── 2_📋_Transações.py
│   ├── 3_👥_Moradores.py
│   ├── 4_🔁_Recorrências.py
│   └── 5_⚙️_Configurações.py
│
└── core/                       # Lógica de negócio (sem dependência de Streamlit)
    ├── database.py             # SQLite: schemas e CRUD
    ├── models.py               # Dataclasses
    ├── gemini_client.py        # Wrapper da API Gemini
    ├── embeddings.py           # Busca semântica (similaridade do cosseno)
    ├── chatbot.py              # Parser de linguagem natural
    ├── rateio.py               # Divisão de despesas e acerto de contas
    ├── recorrencias.py         # Geração mensal automática
    └── utils.py                # Formatação BRL e datas
```

## 💡 Exemplos de uso do chatbot

- *"A conta de luz desse mês veio 287 reais, paguei hoje"*
- *"Maria pagou o aluguel dela de 800 reais"*
- *"Comprei gás por 130, divide entre todo mundo"*
- *"Quanto cada um deve esse mês?"*
- *"Quais contas estão pendentes?"*

## ⚠️ Observações

- O arquivo `financeiro.db` fica fora do Git (no `.gitignore`). Cada clone começa com dados de exemplo.
- A chave da API **nunca** é commitada — o `.env` está bloqueado pelo `.gitignore`.
- Para resetar o banco, basta deletar `financeiro.db` e reiniciar a aplicação.

## 📄 Licença

MIT
