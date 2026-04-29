import pandas as pd
import os
import re

class Router:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.matrix1_path = os.path.join(data_dir, "SDX_E1_CTCE_SJO_EXP_PCT_44.csv")
        self.matrix2_path = os.path.join(data_dir, "CTCE_SJO_2_EXP_SAP_PCT_SDX_4_PCT_2025 (10).csv")
        
        self.df1 = self._load_csv(self.matrix1_path)
        self.df2 = self._load_csv(self.matrix2_path)

    def _load_csv(self, path):
        if not os.path.exists(path):
            print(f"Aviso: Arquivo {path} não encontrado.")
            return None
        
        try:
            # Tenta ler com separador vírgula ou ponto-e-vírgula (comum em CSVs brasileiros)
            try:
                df = pd.read_csv(path, sep=';', encoding='utf-8')
            except:
                df = pd.read_csv(path, sep=',', encoding='utf-8')
            
            # Limpeza básica de colunas
            df.columns = [col.strip().upper() for col in df.columns]
            
            # Limpeza de CEPs
            if 'CEP_INICIAL' in df.columns and 'CEP_FINAL' in df.columns:
                df['CEP_INICIAL'] = df['CEP_INICIAL'].apply(self.clean_cep_to_int)
                df['CEP_FINAL'] = df['CEP_FINAL'].apply(self.clean_cep_to_int)
            
            return df
        except Exception as e:
            print(f"Erro ao carregar {path}: {e}")
            return None

    def clean_cep_to_int(self, cep):
        if pd.isna(cep):
            return 0
        cep_str = re.sub(r'\D', '', str(cep))
        return int(cep_str) if cep_str else 0

    def route_cep(self, cep):
        """
        Busca o CEP nas matrizes e retorna (Bateria, Posição, Matriz_Origem)
        """
        cep_int = self.clean_cep_to_int(cep)
        if cep_int == 0:
            return None

        # Tenta na Matriz 1
        result = self._search_in_df(self.df1, cep_int)
        if result:
            return {**result, "matriz": "SDX_E1"}

        # Tenta na Matriz 2 (Fallback)
        result = self._search_in_df(self.df2, cep_int)
        if result:
            return {**result, "matriz": "CTCE_SJO_2"}

        return None

    def _search_in_df(self, df, cep_int):
        if df is None:
            return None
        
        # Boolean masking
        mask = (df['CEP_INICIAL'] <= cep_int) & (df['CEP_FINAL'] >= cep_int)
        match = df[mask]
        
        if not match.empty:
            row = match.iloc[0]
            return {
                "bateria": row.get("BATERIA", "N/A"),
                "posicao": row.get("POSICAO", "N/A"),
                "unidade": row.get("UNIDADE", "N/A")
            }
        return None
