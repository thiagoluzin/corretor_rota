import pytesseract
from PIL import Image
import re
import os
import cv2
import numpy as np

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
        open_cv_image = np.array(pil_image)
        open_cv_image = open_cv_image[:, :, ::-1].copy()
        gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        denoised = cv2.fastNlMeansDenoising(thresh, None, 10, 7, 21)
        return Image.fromarray(denoised)

    def extract_address_data(self, pil_image):
        """
        REGRA CRÍTICA: Extrai Logradouro, Cidade e UF, ignorando CEPs.
        """
        try:
            processed_image = self.preprocess_image(pil_image)
            text = pytesseract.image_to_string(processed_image, lang='por', config='--psm 6')
            
            # 1. BLOQUEIO DE CEP: Remove qualquer sequência que pareça CEP (00000-000 ou 00000000)
            text_cleaned = re.sub(r'\d{5}-?\d{3}', '', text)
            
            # 2. Extração de padrões de endereço
            # Tenta encontrar Cidade/UF ou Cidade - UF
            address_info = {"cidade": "", "uf": "", "logradouro": "", "texto_bruto": text_cleaned}
            
            lines = [line.strip() for line in text_cleaned.split('\n') if line.strip()]
            
            for i, line in enumerate(lines):
                # Busca por UF (ex: SAO PAULO - SP ou RIBAO PRETO/SP)
                match_uf = re.search(r'([A-ZÀ-ÖØ-öø-ÿ\s]{3,})[/-]\s*([A-Z]{2})', line, re.IGNORECASE)
                if match_uf:
                    address_info["cidade"] = match_uf.group(1).strip()
                    address_info["uf"] = match_uf.group(2).strip().upper()
                    # Assume que o logradouro está na linha anterior
                    if i > 0:
                        address_info["logradouro"] = lines[i-1].strip()
                    break
            
            return address_info
        except Exception as e:
            return {"erro": str(e)}
