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
        
        # Pré-processamento da Planilha 2 para lookup rápido
        if self.df2 is not None:
            # Garante que a coluna DIRECAO_TRIAGEM esteja limpa para o match
            if 'DIRECAO_TRIAGEM' in self.df2.columns:
                self.df2['DIRECAO_TRIAGEM'] = self.df2['DIRECAO_TRIAGEM'].astype(str).str.strip().str.upper()

    def _load_csv(self, path):
        if not os.path.exists(path):
            print(f"Aviso: Arquivo {path} não encontrado.")
            return None
        
        try:
            # Tenta ler com separador vírgula ou ponto-e-vírgula
            try:
                df = pd.read_csv(path, sep=';', encoding='utf-8')
            except:
                df = pd.read_csv(path, sep=',', encoding='utf-8')
            
            # Limpeza básica de colunas
            df.columns = [col.strip().upper() for col in df.columns]
            
            # Limpeza de CEPs na Planilha 1
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
        Lógica Relacional:
        1. Busca DIRECAO_TRIAGEM na Planilha 1 pelo range de CEP.
        2. Usa DIRECAO_TRIAGEM para buscar CELULA e POSICAO na Planilha 2.
        """
        cep_int = self.clean_cep_to_int(cep)
        if cep_int == 0 or self.df1 is None or self.df2 is None:
            return {"sucesso": False, "erro": "Dados ou CEP inválidos"}

        # Passo A: Busca na Planilha 1 (Range)
        mask1 = (self.df1['CEP_INICIAL'] <= cep_int) & (self.df1['CEP_FINAL'] >= cep_int)
        match1 = self.df1[mask1]
        
        if match1.empty:
            return {"sucesso": False, "erro": f"CEP {cep} não mapeado na matriz de faixas (PL1)"}
        
        # Passo B: Extrai DIRECAO_TRIAGEM
        # Tenta DIRECAO_TRIAGEM primeiro, senão MCMCU_CENTRALIZADOR_DESTINO
        direcao = ""
        row1 = match1.iloc[0]
        if 'DIRECAO_TRIAGEM' in row1:
            direcao = str(row1['DIRECAO_TRIAGEM']).strip().upper()
        elif 'MCMCU_CENTRALIZADOR_DESTINO' in row1:
            direcao = str(row1['MCMCU_CENTRALIZADOR_DESTINO']).strip().upper()
            
        if not direcao:
            return {"sucesso": False, "erro": "Coluna de ligação não encontrada na Planilha 1"}

        # Passo C: Busca na Planilha 2 (Exact Match na DIRECAO_TRIAGEM)
        # Usamos boolean masking para encontrar a linha correspondente
        mask2 = self.df2['DIRECAO_TRIAGEM'] == direcao
        match2 = self.df2[mask2]
        
        if match2.empty:
            return {
                "sucesso": True, # Encontrou o destino, mas não a posição física
                "destino": direcao,
                "celula": "N/A",
                "posicao": "N/A",
                "aviso": "Destino encontrado, mas sem mapeamento de célula/posição na PL2"
            }
        
        # Passo D: Extrai CELULA e POSICAO
        row2 = match2.iloc[0]
        return {
            "sucesso": True,
            "destino": direcao,
            "celula": row2.get("CELULA", "N/A"),
            "posicao": row2.get("POSICAO", "N/A")
        }
