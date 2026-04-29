import streamlit as st
from modules.ocr_engine import OCREngine
from modules.cep_api import CEPApi
from modules.router import Router
import time

# Configuração da página para Mobile-First
st.set_page_config(
    page_title="AutoLabel Corrector",
    page_icon="🏷️",
    layout="centered"
)

# CSS Customizado para Visual Premium e Mobile-First
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    .stButton>button {
        width: 100%;
        height: 80px;
        font-size: 24px !important;
        font-weight: bold;
        border-radius: 15px;
        background-color: #FF5500;
        color: white;
        border: none;
        box-shadow: 0 4px 15px rgba(255, 85, 0, 0.3);
    }
    .result-card {
        background-color: #1a1c23;
        border: 3px solid #00ff41;
        border-radius: 20px;
        padding: 25px;
        text-align: center;
        margin-top: 20px;
        box-shadow: 0 0 20px rgba(0, 255, 65, 0.2);
    }
    .neon-text {
        color: #00ff41;
        text-shadow: 0 0 10px #00ff41;
        font-family: 'Courier New', Courier, monospace;
    }
    .label-huge {
        font-size: 50px;
        font-weight: 900;
        margin: 0;
    }
    .label-pos {
        font-size: 80px;
        font-weight: 900;
        margin: 0;
        line-height: 1;
    }
    .info-text {
        font-size: 20px;
        color: #888;
    }
    </style>
    """, unsafe_allow_html=True)

# Inicialização de Módulos (com cache para performance)
@st.cache_resource
def init_modules():
    return OCREngine(), CEPApi(), Router()

ocr, api, router = init_modules()

st.title("🚀 AutoLabel Corrector")
st.subheader("CTCE São José do Rio Preto")

# Layout de Abas para facilitar navegação mobile
tab1, tab2 = st.tabs(["📸 Scanner", "⌨️ Manual"])

with tab1:
    img_file = st.camera_input("Bipar Etiqueta")
    
    if img_file:
        with st.spinner("Processando Imagem..."):
            # 1. OCR
            text = ocr.extract_text(img_file)
            cep_detected = ocr.find_cep(text)
            
            # Se não detectou CEP, tenta buscar por endereço
            if not cep_detected:
                addr = ocr.find_address_block(text)
                if addr["cidade"] and addr["uf"]:
                    cep_detected = api.search_cep_by_address(addr["uf"], addr["cidade"], addr["logradouro"])
            
            if cep_detected:
                st.session_state.cep = cep_detected
                st.success(f"CEP Detectado: {cep_detected}")
            else:
                st.warning("Não foi possível ler o CEP automaticamente. Use a aba Manual.")

with tab2:
    cep_input = st.text_input("Digite o CEP Real", placeholder="00000000")
    if st.button("Buscar Roteamento"):
        if cep_input:
            st.session_state.cep = cep_input

# Lógica de Exibição do Resultado
if "cep" in st.session_state:
    cep_to_route = st.session_state.cep
    
    # Busca dados do CEP (Endereço)
    address_data = api.get_address_by_cep(cep_to_route)
    
    # Busca Roteamento (Bateria/Posição)
    route = router.route_cep(cep_to_route)
    
    if route:
        st.markdown(f"""
            <div class="result-card">
                <div class="info-text">DESTINO</div>
                <div class="neon-text" style="font-size: 24px; font-weight: bold;">
                    {address_data['cidade'] if address_data else 'DESCONHECIDO'} - {address_data['uf'] if address_data else ''}
                </div>
                <hr style="border-color: #333;">
                <div class="info-text">BATERIA</div>
                <div class="neon-text label-huge">{route['bateria']}</div>
                <div class="info-text">POSIÇÃO</div>
                <div class="neon-text label-pos">{route['posicao']}</div>
                <hr style="border-color: #333;">
                <div style="font-size: 14px; color: #555;">Fonte: {route['matriz']}</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Botão para Limpar e Próximo
        if st.button("🔄 PRÓXIMO PACOTE"):
            del st.session_state.cep
            st.rerun()
    else:
        st.error(f"CEP {cep_to_route} não encontrado nas matrizes logísticas!")
        if address_data:
            st.info(f"Cidade: {address_data['cidade']} - {address_data['uf']}")
        
        if st.button("Tentar Outro"):
            del st.session_state.cep
            st.rerun()

st.sidebar.markdown("---")
st.sidebar.info("AutoLabel v1.0 - Correção de CEP 15123002")
