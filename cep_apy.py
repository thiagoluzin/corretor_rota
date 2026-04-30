import requests
import re
import urllib.parse

class CEPApi:
    def __init__(self):
        self.via_cep_url = "https://viacep.com.br/ws/{}/json/"
        # Endpoint de busca por endereço: viacep.com.br/ws/RS/Porto Alegre/Domingos/json/
        self.via_cep_address_url = "https://viacep.com.br/ws/{}/{}/{}/json/"
        self.brasil_api_url = "https://brasilapi.com.br/api/cep/v1/{}"

    def clean_string(self, text):
        if not text:
            return ""
        # Remove caracteres especiais mas mantém espaços para a busca
        return re.sub(r'[^\w\s]', '', str(text)).strip()

    def get_address_by_cep(self, cep):
        """Busca o endereço a partir de um CEP (Fallback)"""
        cep = re.sub(r'\D', '', str(cep))
        if len(cep) != 8:
            return None

        try:
            response = requests.get(self.brasil_api_url.format(cep), timeout=5)
            if response.status_code == 200:
                data = response.json()
                return {
                    "logradouro": data.get("street", ""),
                    "bairro": data.get("neighborhood", ""),
                    "cidade": data.get("city", ""),
                    "uf": data.get("state", ""),
                    "cep": cep
                }
        except Exception:
            pass

        try:
            response = requests.get(self.via_cep_url.format(cep), timeout=5)
            if response.status_code == 200:
                data = response.json()
                if "erro" not in data:
                    return {
                        "logradouro": data.get("logradouro", ""),
                        "bairro": data.get("bairro", ""),
                        "cidade": data.get("localidade", ""),
                        "uf": data.get("uf", ""),
                        "cep": cep
                    }
        except Exception:
            pass
        return None

    def find_cep_by_address(self, uf, city, street):
        """
        REGRA CRÍTICA: Busca o CEP real a partir do endereço lido pelo OCR ou digitado.
        """
        uf = self.clean_string(uf).upper()
        city = self.clean_string(city)
        street = self.clean_string(street)

        if not uf or not city or len(street) < 3:
            return None

        # Codifica para URL (trata espaços e acentos)
        city_encoded = urllib.parse.quote(city)
        street_encoded = urllib.parse.quote(street)
        
        url = self.via_cep_address_url.format(uf, city_encoded, street_encoded)
        
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    # Retorna o CEP do primeiro resultado encontrado
                    # Limpa o hífen
                    return data[0].get("cep", "").replace("-", "")
        except Exception as e:
            print(f"Erro na consulta de CEP por endereço: {e}")
        
        return None
