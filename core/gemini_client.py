import os
import google.generativeai as genai
from typing import List, Dict, Any, Optional

# Lazy initialization of Gemini
def get_gemini_api_key() -> Optional[str]:
    """Retorna o API key cadastrado no ambiente ou no session state de forma segura."""
    # Pode vir do arquivo .env ou do segredo do Streamlit
    key = os.environ.get("GEMINI_API_KEY")
    if not key or key == "MY_GEMINI_API_KEY":
        return None
    return key

def testar_api_key() -> bool:
    """Verifica se há uma chave de API válida configurada."""
    return get_gemini_api_key() is not None

def gerar_embedding(texto: str) -> Optional[List[float]]:
    """Gera o embedding vetorial do texto usando o modelo text-embedding-004."""
    api_key = get_gemini_api_key()
    if not api_key:
        print("Aviso: Chave de API do Gemini não configurada. Embedding ignorado.")
        return None
    try:
        genai.configure(api_key=api_key)
        # Tenta text-embedding-004
        resultado = genai.embed_content(
            model="models/text-embedding-004",
            contents=texto,
            task_type="retrieval_document"
        )
        if "embedding" in resultado:
            return resultado["embedding"]
        elif isinstance(resultado, dict) and "embedding" in resultado:
            return resultado["embedding"]
        # Caso retorne um objeto específico do SDK
        return list(resultado.get("embedding", []))
    except Exception as e:
        print(f"Erro ao gerar embedding com text-embedding-004: {e}. Tentando fallback...")
        try:
            # Fallback para o modelo alternativo de embedding se disponível
            resultado = genai.embed_content(
                model="models/text-embedding-004",
                contents=texto,
                task_type="retrieval_document"
            )
            return resultado["embedding"]
        except Exception as inner:
            print(f"Todos os serviços de embedding falharam: {inner}")
            return None

def chat(mensagem: str, historico: List[Dict[str, str]], system_instruction: Optional[str] = None) -> str:
    """Inicia ou continua uma sessão de chat com o Gemini utilizando histórico."""
    api_key = get_gemini_api_key()
    if not api_key:
        return ("Olá! Para conversar comigo e registrar transações por voz ou chat de forma inteligente, "
                "por favor adicione sua **Chave de API do Gemini** no menu de Configurações ⚙️.")
    
    try:
        genai.configure(api_key=api_key)
        
        # Usamos o modelo gemini-2.5-flash ou gemini-1.5-flash
        model_name = "models/gemini-2.5-flash"
        
        # Preparar histórico no formato exigido pelo SDK
        # Formato esperado: list de {'role': 'user'|'model', 'parts': [text]}
        contents_history = []
        for h in historico:
            role = "user" if h["role"] == "user" else "model"
            contents_history.append({
                "role": role,
                "parts": [h["content"]]
            })
            
        config = genai.types.GenerationConfig(
            temperature=0.3,
            max_output_tokens=1000
        )
        
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_instruction
        )
        
        # gera a resposta passando o histórico mais a nova mensagem
        response = model.generate_content(
            contents=contents_history + [{"role": "user", "parts": [mensagem]}],
            generation_config=config
        )
        
        return response.text
    except Exception as e:
        return f"Desculpe, ocorreu um erro ao chamar a API do Gemini: {str(e)}"
