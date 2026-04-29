import pytesseract
from PIL import Image, ImageOps, ImageFilter
import re
import os

class OCREngine:
    def __init__(self):
        # Tenta localizar o executável do Tesseract no Windows se não estiver no PATH
        tesseract_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Users\admin_remoto\AppData\Local\Tesseract-OCR\tesseract.exe',
            r'C:\Users\admin\AppData\Local\Tesseract-OCR\tesseract.exe'
        ]
        for path in tesseract_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                break

    def preprocess_image(self, image):
        """
        Pré-processamento para melhorar OCR: Escala de cinza e Threshold.
        """
        # Converte para escala de cinza
        gray = image.convert('L')
        
        # Aumenta contraste
        enhanced = ImageOps.autocontrast(gray)
        
        # Aplica threshold (limiarização)
        threshold = 150
        binary = enhanced.point(lambda p: 255 if p > threshold else 0)
        
        return binary

    def extract_text(self, image_bytes):
        """
        Lê a imagem e extrai o texto.
        """
        try:
            image = Image.open(image_bytes)
            processed_image = self.preprocess_image(image)
            
            # Extrai texto com configuração otimizada para português
            text = pytesseract.image_to_string(processed_image, lang='por')
            return text
        except Exception as e:
            return f"Erro no OCR: {str(e)}"

    def find_cep(self, text):
        """
        Tenta encontrar um padrão de CEP no texto (00000-000 ou 00000000).
        """
        # Ignora o CEP errado conhecido (15123002) se possível, ou prioriza outros
        ceps = re.findall(r'\b\d{5}-?\d{3}\b', text)
        
        # Filtra o CEP genérico errado
        filtered_ceps = [cep.replace("-", "") for cep in ceps if "15123002" not in cep.replace("-", "")]
        
        if filtered_ceps:
            return filtered_ceps[0]
        elif ceps:
            return ceps[0].replace("-", "")
            
        return None

    def find_address_block(self, text):
        """
        Tenta isolar o bloco de DESTINATÁRIO e extrair Cidade/UF.
        """
        # Procura por palavras chave
        lines = text.split('\n')
        address_info = {"cidade": "", "uf": "", "logradouro": ""}
        
        for i, line in enumerate(lines):
            # Procura por UF (Padrão: Cidade/UF ou Cidade - UF)
            match_uf = re.search(r'([A-Za-zÀ-ÖØ-öø-ÿ\s]+)[/-]\s*([A-Z]{2})', line)
            if match_uf:
                address_info["cidade"] = match_uf.group(1).strip()
                address_info["uf"] = match_uf.group(2).strip()
                # O logradouro geralmente está na linha anterior ou na mesma
                if i > 0:
                    address_info["logradouro"] = lines[i-1].strip()
                break
                
        return address_info
