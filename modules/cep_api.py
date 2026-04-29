import requests
import re

class CEPApi:
    def __init__(self):
        self.via_cep_url = "https://viacep.com.br/ws/{}/json/"
        self.brasil_api_url = "https://brasilapi.com.br/api/cep/v1/{}"

    def clean_cep(self, cep):
        if not cep:
            return ""
        return re.sub(r'\D', '', str(cep))

    def get_address_by_cep(self, cep):
        """
        Busca o endereço a partir de um CEP.
        """
        cep = self.clean_cep(cep)
        if len(cep) != 8:
            return None

        # Tenta BrasilAPI primeiro
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

        # Fallback para ViaCEP
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

    def search_cep_by_address(self, uf, city, street):
        """
        Busca o CEP a partir de UF, Cidade e Logradouro.
        """
        # ViaCEP suporta busca por endereço: viacep.com.br/ws/RS/Porto Alegre/Domingos/json/
        url = f"https://viacep.com.br/ws/{uf}/{city}/{street}/json/"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    # Retorna o primeiro resultado
                    return data[0].get("cep", "").replace("-", "")
        except Exception:
            pass
        return None
