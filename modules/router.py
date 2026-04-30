import pandas as pd
import os
import re

class Router:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir

        # Tenta xlsx primeiro, depois csv
        self.df1 = self._load("SDX_E1_CTCE_SJO_EXP_PCT_44")
        self.df2 = self._load("CTCE_SJO_2_EXP_SAP_PCT_SDX_4_PCT_2025 (10)")

        if self.df1 is not None:
            self.df1['CEP_INICIAL'] = self.df1['CEP_INICIAL'].apply(self._cep_int)
            self.df1['CEP_FINAL']   = self.df1['CEP_FINAL'].apply(self._cep_int)
            self.df1 = self.df1[self.df1['CEP_INICIAL'] > 0]
            # Normaliza nomes para lookup
            self.df1['DIRECAO_TRIAGEM'] = self.df1['DIRECAO_TRIAGEM'].astype(str).str.strip()
            self.df1['MCMCU_CENTRALIZADOR_DESTINO'] = self.df1['MCMCU_CENTRALIZADOR_DESTINO'].astype(str).str.strip()

        if self.df2 is not None:
            self.df2['DIRECAO_TRIAGEM'] = self.df2['DIRECAO_TRIAGEM'].astype(str).str.strip()
            self.df2['MCMCU_CENTRALIZADOR_DESTINO'] = self.df2['MCMCU_CENTRALIZADOR_DESTINO'].astype(str).str.strip()

    def _load(self, nome_base):
        """Carrega o arquivo xlsx ou csv da pasta data/."""
        for ext in ['.xlsx', '.csv']:
            path = os.path.join(self.data_dir, nome_base + ext)
            if not os.path.exists(path):
                continue
            try:
                if ext == '.xlsx':
                    df = pd.read_excel(path)
                else:
                    for sep in [';', ',', '\t']:
                        try:
                            df = pd.read_csv(path, sep=sep, encoding='utf-8')
                            if len(df.columns) > 2:
                                break
                        except Exception:
                            continue
                df.columns = [str(c).strip().upper() for c in df.columns]
                print(f"[Router] Carregado: {path} ({len(df)} linhas)")
                return df
            except Exception as e:
                print(f"[Router] Erro ao carregar {path}: {e}")
        print(f"[Router] Arquivo não encontrado: {nome_base}")
        return None

    def _cep_int(self, valor):
        """
        Converte CEP para inteiro.
        Regra: aceita apenas CEPs com exatamente 8 dígitos após limpeza.
        CEPs com menos dígitos são descartados (retorna 0) para evitar
        matches errados causados por OCR truncado.
        Ex: '95678-871' -> 95678871 OK
            '9500-34'   -> 6 digitos -> 0 (invalido, cai no fallback de endereço)
            '01310100'  -> 01310100 OK
        """
        try:
            apenas_digitos = re.sub(r'\D', '', str(valor))
            if len(apenas_digitos) != 8:
                return 0
            return int(apenas_digitos)
        except (ValueError, TypeError):
            return 0

    def diagnostico(self):
        """Retorna status das planilhas carregadas para exibição no sidebar."""
        def info(df):
            if df is None:
                return {"linhas": 0, "colunas": []}
            return {"linhas": len(df), "colunas": list(df.columns)}

        return {
            "planilha1": info(self.df1),
            "planilha2": info(self.df2)
        }

    def route_cep(self, cep):
        """
        Roteamento Relacional em 2 passos:
        A) CEP (range) → MCMCU_CENTRALIZADOR_DESTINO + DIRECAO_TRIAGEM (PL1)
        B) MCMCU_CENTRALIZADOR_DESTINO + DIRECAO_TRIAGEM → CELULA + POSICAO (PL2)
        """
        cep_int = self._cep_int(cep)
        if cep_int == 0:
            return {"sucesso": False, "erro": "CEP inválido"}

        if self.df1 is None:
            return {"sucesso": False, "erro": "Planilha 1 (SDX_E1) não carregada"}

        # Passo A: Range na PL1
        mask1 = (self.df1['CEP_INICIAL'] <= cep_int) & (self.df1['CEP_FINAL'] >= cep_int)
        match1 = self.df1[mask1]

        if match1.empty:
            return {"sucesso": False, "erro": f"CEP {cep} não encontrado na faixa da PL1"}

        row1 = match1.iloc[0]
        mcmcu      = str(row1.get('MCMCU_CENTRALIZADOR_DESTINO', '')).strip()
        direcao_pl1 = str(row1.get('DIRECAO_TRIAGEM', '')).strip()

        if self.df2 is None:
            return {
                "sucesso": True,
                "destino": direcao_pl1,
                "celula": "—",
                "posicao": "—",
                "aviso": "Planilha 2 não carregada"
            }

        # Passo B: Join pela coluna MCMCU_CENTRALIZADOR_DESTINO na PL2
        # Se houver múltiplas linhas para o mesmo MCMCU (ex: INDAIATUBA PL1/PL2/PL3),
        # usamos também DIRECAO_TRIAGEM para afinar o match
        mask2_mcmcu = self.df2['MCMCU_CENTRALIZADOR_DESTINO'] == mcmcu
        match2 = self.df2[mask2_mcmcu]

        if match2.empty:
            return {
                "sucesso": True,
                "destino": direcao_pl1,
                "celula": "—",
                "posicao": "—",
                "aviso": f"MCMCU {mcmcu} não encontrado na PL2"
            }

        # Se houver mais de 1 linha, tenta refinar pelo DIRECAO_TRIAGEM
        if len(match2) > 1:
            match_refinado = match2[match2['DIRECAO_TRIAGEM'].str.upper() == direcao_pl1.upper()]
            if not match_refinado.empty:
                match2 = match_refinado

        row2 = match2.iloc[0]
        destino_final = str(row2.get('DIRECAO_TRIAGEM', direcao_pl1)).strip()
        celula  = str(row2.get('CELULA',  '—')).strip()
        posicao = str(row2.get('POSICAO', '—')).strip()

        return {
            "sucesso": True,
            "destino": destino_final,
            "celula":  celula,
            "posicao": posicao
        }
