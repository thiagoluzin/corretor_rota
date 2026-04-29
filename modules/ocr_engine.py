import pytesseract
from PIL import Image, ImageOps, ImageFilter
import re
import os
import cv2
import numpy as np

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

    def preprocess_image(self, pil_image):
        """
        Pré-processamento avançado com OpenCV para melhorar OCR.
        """
        # Converte PIL para OpenCV (numpy array)
        open_cv_image = np.array(pil_image)
        # Converte RGB para BGR
        open_cv_image = open_cv_image[:, :, ::-1].copy()
        
        # Converte para escala de cinza
        gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
        
        # Redimensiona para melhorar leitura de texto pequeno
        gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        
        # Aplica threshold adaptativo ou Otsu
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Denoising
        denoised = cv2.fastNlMeansDenoising(thresh, None, 10, 7, 21)
        
        # Retorna de volta para PIL
        return Image.fromarray(denoised)

    def extract_text(self, pil_image):
        """
        Lê a imagem e extrai o texto.
        """
        try:
            processed_image = self.preprocess_image(pil_image)
            
            # Extrai texto com configuração otimizada para português
            # --psm 6: Assume a single uniform block of text.
            custom_config = r'--oem 3 --psm 6 -l por'
            text = pytesseract.image_to_string(processed_image, config=custom_config)
            return text
        except Exception as e:
            return f"Erro no OCR: {str(e)}"

    def find_cep(self, text):
        """
        Tenta encontrar um padrão de CEP no texto (00000-000 ou 00000000).
        """
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
        lines = text.split('\n')
        address_info = {"cidade": "", "uf": "", "logradouro": ""}
        
        for i, line in enumerate(lines):
            # Procura por UF (Padrão: Cidade/UF ou Cidade - UF)
            match_uf = re.search(r'([A-Za-zÀ-ÖØ-öø-ÿ\s]+)[/-]\s*([A-Z]{2})', line)
            if match_uf:
                address_info["cidade"] = match_uf.group(1).strip()
                address_info["uf"] = match_uf.group(2).strip()
                if i > 0:
                    address_info["logradouro"] = lines[i-1].strip()
                break
                
        return address_info
