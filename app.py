import streamlit as st
import importlib
import modules.ocr_engine
importlib.reload(modules.ocr_engine)
from modules.ocr_engine import OCREngine
from modules.cep_api import CEPApi
from modules.router import Router
from streamlit_cropper import st_cropper
from PIL import Image
import time

# Configuração da página para Mobile-First
st.set_page_config(
    page_title="AutoLabel Corrector",
    page_icon="🏷️",
    layout="centered"
)

# CSS Customizado
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stButton>button {
        width: 100%; height: 80px; font-size: 24px !important; font-weight: bold;
        border-radius: 15px; background-color: #FF5500; color: white;
    }
    .result-card {
        background-color: #1a1c23; border: 3px solid #00ff41; border-radius: 20px;
        padding: 25px; text-align: center; margin-top: 20px;
    }
    .neon-text { color: #00ff41; text-shadow: 0 0 10px #00ff41; font-family: monospace; }
    .label-huge { font-size: 50px; font-weight: 900; margin: 0; }
    .label-pos { font-size: 80px; font-weight: 900; margin: 0; line-height: 1; }
    .warning-box {
        background-color: #ff0000; color: white; padding: 15px;
        border-radius: 10px; font-weight: bold; text-align: center; margin-bottom: 20px;
        border: 2px solid white;
    }
    .footer {
        text-align: center; color: #4a4a4a; font-size: 14px; margin-top: 50px;
        border-top: 1px solid #1a1c23; padding-top: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# Removido o cache temporariamente para garantir que as atualizações dos módulos sejam lidas
# @st.cache_resource
def init_modules():
    return OCREngine(), CEPApi(), Router()

ocr, api, router = init_modules()

# Diagnóstico das planilhas no Sidebar
with st.sidebar:
    st.markdown("### 📊 Status das Planilhas")
    diag = router.diagnostico()
    for nome, info in [("PL1 (SDX_E1)", diag["planilha1"]), ("PL2 (CTCE_SJO_2)", diag["planilha2"])]:
        linhas = info["linhas"]
        cols   = info["colunas"]
        if linhas > 0:
            st.success(f"✅ {nome}: {linhas} linhas")
        else:
            st.error(f"❌ {nome}: não carregada")
        with st.expander(f"Colunas — {nome}"):
            st.json(cols)
    st.markdown("---")
    st.info("AutoLabel v1.3")

st.title("🚀 AutoLabel Corrector")
st.subheader("CTCE São José do Rio Preto")

tab1, tab2 = st.tabs(["📸 Scanner de Endereço", "⌨️ Entrada Manual"])

with tab1:
    input_method = st.radio("Como enviar a foto?", ["Câmera", "Galeria"], horizontal=True)
    img_file = st.camera_input("Foto da Etiqueta") if input_method == "Câmera" else st.file_uploader("Upload da Etiqueta", type=['jpg', 'jpeg', 'png'])

    if img_file:
        img = Image.open(img_file)
        
        # AVISO CRÍTICO NO CROPPER
        st.markdown('<div class="warning-box">⚠️ ATENÇÃO: RECORTE APENAS O NOME DA RUA E CIDADE DO DESTINATÁRIO.<br>NÃO INCLUA CEPs, CÓDIGOS DE BARRAS NEM O REMETENTE.</div>', unsafe_allow_html=True)
        
        cropped_img = st_cropper(img, realtime_update=True, box_color='#FF5500', aspect_ratio=None)
        
        if st.button("🔍 DESCOBRIR CEP E ROTEAR"):
            with st.spinner("Analisando endereço..."):
                addr_data = ocr.extract_address_data(cropped_img)

                cidade = addr_data.get("cidade", "")
                uf = addr_data.get("uf", "")
                rua = addr_data.get("logradouro", "")

                # Mostra o que foi extraído para o operador validar
                col1, col2, col3 = st.columns(3)
                col1.metric("Rua Extraída", rua or "—")
                col2.metric("Cidade", cidade or "—")
                col3.metric("UF", uf or "—")

                if cidade and uf:
                    cep_real = api.find_cep_by_address(uf, cidade, rua)

                    if cep_real:
                        st.session_state.cep = cep_real
                        st.success(f"✅ CEP Identificado: **{cep_real}**")
                    else:
                        st.error("❌ Não encontrado no ViaCEP. Corrija os campos na aba Manual.")
                        # Pré-preenche a aba manual com os dados extraídos
                        st.session_state.manual_uf = uf
                        st.session_state.manual_cidade = cidade
                        st.session_state.manual_rua = rua
                else:
                    st.error("❌ Não identificou Cidade/UF. Ajuste o recorte.")

                with st.expander("🔍 Ver texto bruto do OCR"):
                    st.text(addr_data.get("texto_bruto", ""))

with tab2:
    st.write("Insira os dados do destinatário conforme a etiqueta:")
    col1, col2 = st.columns([1, 3])
    with col1:
        uf_manual = st.text_input("UF", value=st.session_state.get("manual_uf", ""), placeholder="SP", max_chars=2)
    with col2:
        cidade_manual = st.text_input("Cidade", value=st.session_state.get("manual_cidade", ""), placeholder="Ex: Tiete")
    rua_manual = st.text_input("Logradouro (Rua/Av)", value=st.session_state.get("manual_rua", ""), placeholder="Ex: Santa Cruz")

    if st.button("🚀 ROTEAR POR ENDEREÇO"):
        if uf_manual and cidade_manual and rua_manual:
            with st.spinner("Consultando CEP oficial..."):
                cep_real = api.find_cep_by_address(uf_manual, cidade_manual, rua_manual)
                if cep_real:
                    st.session_state.cep = cep_real
                    # Limpa os dados pré-preenchidos após sucesso
                    for k in ["manual_uf", "manual_cidade", "manual_rua"]:
                        st.session_state.pop(k, None)
                else:
                    st.error("CEP não encontrado. Verifique a ortografia da cidade e rua.")
        else:
            st.warning("Preencha todos os campos.")


# Lógica de Roteamento
if "cep" in st.session_state:
    route = router.route_cep(st.session_state.cep)
    if route.get("sucesso"):
        st.markdown(f"""
            <div class="result-card">
                <div class="info-text">CÉLULA</div>
                <div class="neon-text label-huge">{route['celula']}</div>
                <hr style="border-color: #333;">
                <div class="info-text">UNIDADE</div>
                <div class="neon-text" style="font-size: 28px; font-weight: bold;">{route['destino']}</div>
                <hr style="border-color: #333;">
                <div class="info-text">POSIÇÃO</div>
                <div class="neon-text label-pos">{route['posicao']}</div>
                <div style="font-size: 14px; color: #555; margin-top: 10px;">CEP Real: {st.session_state.cep}</div>
            </div>
            """, unsafe_allow_html=True)
        if st.button("🔄 PRÓXIMO PACOTE"):
            del st.session_state.cep
            st.rerun()
    else:
        st.error(f"Erro: {route.get('erro')}")
        if st.button("Tentar Novamente"):
            del st.session_state.cep
            st.rerun()

st.markdown('<div class="footer">Desenvolvido por Thiago Luzin<br><b>CTCE São José do Rio Preto</b></div>', unsafe_allow_html=True)
