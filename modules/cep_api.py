import requests
import re
import urllib.parse

class CEPApi:
    def __init__(self):
        self.via_cep_url = "https://viacep.com.br/ws/{}/json/"
        self.via_cep_address_url = "https://viacep.com.br/ws/{}/{}/{}/json/"

    def get_address_by_cep(self, cep):
        """Busca o endereço a partir de um CEP."""
        cep = re.sub(r'\D', '', str(cep))
        if len(cep) != 8:
            return None
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

    def _limpar_str(self, texto):
        """Remove acentos e caracteres especiais para busca na API."""
        if not texto:
            return ""
        replacements = {
            'Á':'A','À':'A','Ã':'A','Â':'A','á':'a','à':'a','ã':'a','â':'a',
            'É':'E','Ê':'E','é':'e','ê':'e','Í':'I','í':'i',
            'Ó':'O','Ô':'O','Õ':'O','ó':'o','ô':'o','õ':'o',
            'Ú':'U','ú':'u','Ç':'C','ç':'c'
        }
        for k, v in replacements.items():
            texto = texto.replace(k, v)
        # Remove pontuação e caracteres indesejados
        texto = re.sub(r'[^\w\s]', ' ', texto)
        return re.sub(r'\s+', ' ', texto).strip()

    def _consultar_viacep(self, uf, city, street):
        """Faz a consulta ao ViaCEP e retorna o primeiro CEP encontrado."""
        uf_clean = self._limpar_str(uf).upper()
        city_clean = self._limpar_str(city)
        street_clean = self._limpar_str(street)

        if not uf_clean or not city_clean or len(street_clean) < 3:
            return None

        url = self.via_cep_address_url.format(
            uf_clean,
            urllib.parse.quote(city_clean),
            urllib.parse.quote(street_clean)
        )
        try:
            response = requests.get(url, timeout=6)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    return data[0].get("cep", "").replace("-", "")
        except Exception as e:
            print(f"ViaCEP erro: {e}")
        return None

    def find_cep_by_address(self, uf, city, street):
        """
        Busca o CEP real com múltiplas tentativas progressivas.
        """
        # Tentativa 1: Nome completo da rua
        cep = self._consultar_viacep(uf, city, street)
        if cep:
            return cep

        # Tentativa 2: Remove a primeira palavra (pode ser "Rua", "Av", etc.)
        palavras = street.split()
        if len(palavras) > 1:
            street_sem_prefixo = " ".join(palavras[1:])
            cep = self._consultar_viacep(uf, city, street_sem_prefixo)
            if cep:
                return cep

        # Tentativa 3: Usa apenas a última palavra significativa do nome da rua
        # (Ex: "Santa Cruz" → tenta só "Cruz")
        if len(palavras) > 1:
            ultima_palavra = palavras[-1]
            if len(ultima_palavra) > 3:
                cep = self._consultar_viacep(uf, city, ultima_palavra)
                if cep:
                    return cep

        # Tentativa 4: Sem o nome da rua — retorna CEP geral da cidade
        # (útil para roteamento mesmo sem endereço preciso)
        cep = self._consultar_viacep(uf, city, city)
        if cep:
            return cep

        return None
