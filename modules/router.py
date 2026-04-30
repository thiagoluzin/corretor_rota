import pytesseract
from PIL import Image
import re
import os
import cv2
import numpy as np

# Mapeamento de nomes de estado por extenso para sigla
ESTADOS_BR = {
    "ACRE": "AC", "ALAGOAS": "AL", "AMAPA": "AP", "AMAZONAS": "AM",
    "BAHIA": "BA", "CEARA": "CE", "DISTRITO FEDERAL": "DF", "ESPIRITO SANTO": "ES",
    "GOIAS": "GO", "MARANHAO": "MA", "MATO GROSSO DO SUL": "MS", "MATO GROSSO": "MT",
    "MINAS GERAIS": "MG", "PARA": "PA", "PARAIBA": "PB", "PARANA": "PR",
    "PERNAMBUCO": "PE", "PIAUI": "PI", "RIO DE JANEIRO": "RJ",
    "RIO GRANDE DO NORTE": "RN", "RIO GRANDE DO SUL": "RS", "RONDONIA": "RO",
    "RORAIMA": "RR", "SANTA CATARINA": "SC", "SAO PAULO": "SP",
    "SAOPAULO": "SP", "S.PAULO": "SP", "S PAULO": "SP",
    "SERGIPE": "SE", "TOCANTINS": "TO"
}


class OCREngine:
    def __init__(self):
        tesseract_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Users\admin_remoto\AppData\Local\Tesseract-OCR\tesseract.exe',
            r'C:\Users\admin\AppData\Local\Tesseract-OCR\tesseract.exe'
        ]
        for path in tesseract_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                break

    def preprocess_image(self, pil_image):
        """Pré-processamento OpenCV para melhorar leitura de endereços."""
        try:
            open_cv_image = np.array(pil_image.convert('RGB'))
            open_cv_image = open_cv_image[:, :, ::-1].copy()
            gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
            gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            denoised = cv2.fastNlMeansDenoising(thresh, None, 10, 7, 21)
            return Image.fromarray(denoised)
        except Exception:
            return pil_image

    def _normalizar(self, texto):
        """Remove acentos e converte para maiúsculas para comparação."""
        replacements = {
            'Á':'A','À':'A','Ã':'A','Â':'A','á':'a','à':'a','ã':'a','â':'a',
            'É':'E','Ê':'E','é':'e','ê':'e','Í':'I','í':'i',
            'Ó':'O','Ô':'O','Õ':'O','ó':'o','ô':'o','õ':'o',
            'Ú':'U','ú':'u','Ç':'C','ç':'c'
        }
        for k, v in replacements.items():
            texto = texto.replace(k, v)
        return texto.upper().strip()

    def _resolver_uf(self, texto_bruto):
        """
        Tenta extrair a sigla de UF de um texto como:
        'Tiete/Sao Paulo/Brazil', 'Sao Paulo - SP', 'SP', 'Tiete/SP'
        """
        # Primeiro: Tenta encontrar sigla 2 letras após / ou - ou espaço
        match_sigla = re.search(r'[/\-,\s]([A-Z]{2})(?:[/\-,\s]|$)', texto_bruto.upper())
        if match_sigla:
            sigla = match_sigla.group(1)
            # Valida que é UF real (ignora "BR" de Brazil)
            if sigla in ESTADOS_BR.values():
                return sigla

        # Segundo: Procura nome por extenso no texto
        norm = self._normalizar(texto_bruto)
        for nome, sigla in sorted(ESTADOS_BR.items(), key=lambda x: -len(x[0])):
            if nome in norm:
                return sigla

        return None

    def _limpar_logradouro(self, texto):
        """
        Remove prefixos, números, complementos e ruído do logradouro.
        Ex: 'Santa Cruz: rua Santa Cruz: 789 casa' → 'Santa Cruz'
        """
        # Remove prefixos de tipo de logradouro
        texto = re.sub(r'^(rua|r\.|av\.?|avenida|travessa|tv\.?|alameda|al\.?|estrada|est\.?|rodovia|rod\.?)\s+', '', texto, flags=re.IGNORECASE)
        # Remove números, complementos e lixo
        texto = re.sub(r'\b(n\.?|nº|casa|apto?|apartamento|bloco|andar|loja|sala|condo|condominio|s/n)\b.*', '', texto, flags=re.IGNORECASE)
        texto = re.sub(r'\d+', '', texto)
        # Remove pontuação duplicada e espaços extras
        texto = re.sub(r'[:\-,;!?]+', ' ', texto)
        texto = re.sub(r'\s+', ' ', texto).strip()
        return texto

    def _extrair_cidade(self, fragmento_cidade):
        """
        De 'Tiete/Sao Paulo/Brazil' extrai 'Tiete'.
        """
        # Pega o primeiro fragmento antes de / ou -
        partes = re.split(r'[/\-,]', fragmento_cidade)
        cidade = partes[0].strip()
        # Remove caracteres não-letra
        cidade = re.sub(r'[^A-Za-zÀ-ÖØ-öø-ÿ\s]', '', cidade).strip()
        return cidade if len(cidade) > 2 else ""

    def extract_address_data(self, pil_image):
        """
        Extrai Logradouro, Cidade e UF da imagem. Ignora CEPs impressos.
        """
        try:
            processed_image = self.preprocess_image(pil_image)
            text = pytesseract.image_to_string(processed_image, lang='por', config='--psm 6')

            # 1. Remove CEPs para não poluir a busca
            text_cleaned = re.sub(r'\b\d{5}-?\d{3}\b', '', text)
            # Remove "Brazil" / "Brasil" e símbolos de telefone
            text_cleaned = re.sub(r'\b(brazil|brasil)\b', '', text_cleaned, flags=re.IGNORECASE)
            text_cleaned = re.sub(r'[\+\#\*\(\)]', '', text_cleaned)

            address_info = {
                "cidade": "", "uf": "", "logradouro": "",
                "texto_bruto": text_cleaned
            }

            lines = [l.strip() for l in text_cleaned.split('\n') if l.strip()]

            for i, line in enumerate(lines):
                # Padrão: qualquer coisa que contenha uma barra ou hífen seguido de texto
                # Busca linha com padrão Cidade/Estado (ex: Tiete/Sao Paulo, Bauru - SP)
                match = re.search(
                    r'([A-Za-zÀ-ÖØ-öø-ÿ\s\.]+)[/\-,]\s*([A-Za-zÀ-ÖØ-öø-ÿ\s\.\/]+)',
                    line
                )
                if match:
                    cidade_raw = match.group(1)
                    restante = match.group(0)  # linha completa com separadores

                    cidade = self._extrair_cidade(cidade_raw)
                    uf = self._resolver_uf(restante)

                    if cidade and uf:
                        address_info["cidade"] = cidade
                        address_info["uf"] = uf

                        # Logradouro: linha anterior
                        if i > 0:
                            address_info["logradouro"] = self._limpar_logradouro(lines[i - 1])
                        # Fallback: mesma linha
                        if not address_info["logradouro"]:
                            address_info["logradouro"] = self._limpar_logradouro(line)
                        break

            return address_info

        except Exception as e:
            return {"cidade": "", "uf": "", "logradouro": "", "erro": str(e), "texto_bruto": ""}
