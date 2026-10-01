
from pathlib import Path
import time
import logging

import pandas as pd
import yfinance as yf


TICKERS = {
    "ITUB4.SA": "Itaú Unibanco",
    "BBDC4.SA": "Bradesco",
    "BBAS3.SA": "Banco do Brasil",
    "SANB11.SA": "Santander Brasil",
    "BPAC11.SA": "BTG Pactual",
    "ITSA4.SA": "Itaúsa",
    "BPAN4.SA": "Banco Pan",
    "BMGB4.SA": "Banco BMG",
    "BRSR6.SA": "Banrisul",
    "ABCB4.SA": "Banco ABC Brasil",
}

PASTA_SAIDA = Path("data")

CAMPOS_FUNDAMENTOS = [
    "marketCap",
    "trailingPE",
    "priceToBook",
    "dividendYield",
    "returnOnEquity",
]


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


def coletar_historico(
    periodo: str = "2y",
    intervalo: str = "1d",
    tentativas: int = 3,
) -> pd.DataFrame:

    frames = []

    for ticker, nome in TICKERS.items():

        for tentativa in range(1, tentativas + 1):

            try:

                logger.info(
                    "Coletando histórico de %s (%s)",
                    ticker,
                    nome,
                )

                df = yf.download(
                    ticker,
                    period=periodo,
                    interval=intervalo,
                    auto_adjust=True,
                    progress=False,
                    threads=False,
                    timeout=30,
                )

                if df.empty:
                    raise ValueError("Nenhum dado retornado.")

                # Trata possíveis colunas MultiIndex
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)

                df = df.reset_index()

                df.columns = [
                    str(col).lower()
                    for col in df.columns
                ]

                # Remove apenas registros sem fechamento
                df = df.dropna(subset=["close"])

                if df.empty:
                    raise ValueError(
                        "Nenhum registro válido após validação."
                    )

                df["ticker"] = ticker
                df["empresa"] = nome

                frames.append(df)

                logger.info(
                    "%s: %s registros coletados",
                    ticker,
                    len(df),
                )

                break

            except Exception as erro:

                logger.warning(
                    "Falha em %s | Tentativa %s/%s | %s",
                    ticker,
                    tentativa,
                    tentativas,
                    erro,
                )

                if tentativa < tentativas:
                    time.sleep(2 ** tentativa)

        else:
            logger.error(
                "Não foi possível coletar %s",
                ticker,
            )

    if not frames:
        raise ValueError(
            "Nenhum dado histórico foi coletado."
        )

    return pd.concat(
        frames,
        ignore_index=True,
    )


def coletar_fundamentos(
    tentativas: int = 3,
) -> pd.DataFrame:

    linhas = []

    for ticker, nome in TICKERS.items():

        for tentativa in range(1, tentativas + 1):

            try:

                logger.info(
                    "Coletando fundamentos de %s",
                    ticker,
                )

                info = yf.Ticker(ticker).info

                linha = {
                    "ticker": ticker,
                    "empresa": nome,
                }

                linha.update({
                    campo: info.get(campo)
                    for campo in CAMPOS_FUNDAMENTOS
                })

                linhas.append(linha)

                logger.info(
                    "Fundamentos coletados: %s",
                    ticker,
                )

                break

            except Exception as erro:

                logger.warning(
                    "Falha nos fundamentos de %s | "
                    "Tentativa %s/%s | %s",
                    ticker,
                    tentativa,
                    tentativas,
                    erro,
                )

                if tentativa < tentativas:
                    time.sleep(2 ** tentativa)

        else:

            logger.error(
                "Não foi possível coletar fundamentos de %s",
                ticker,
            )

            # Preserva o registro da empresa
            linhas.append({
                "ticker": ticker,
                "empresa": nome,
                **{
                    campo: None
                    for campo in CAMPOS_FUNDAMENTOS
                },
            })
            
            info = yf.Ticker(ticker).info

    if not info or not info.get("symbol"):
        raise ValueError(
        f"Dados fundamentalistas indisponíveis para {ticker}"
    )

    return pd.DataFrame(linhas)


def main() -> None:

    PASTA_SAIDA.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Histórico
    historico = coletar_historico()

    historico.to_parquet(
        PASTA_SAIDA / "historico_bancos.parquet",
        index=False,
    )

    logger.info(
        "Histórico salvo: %s registros",
        len(historico),
    )

    # Fundamentos
    fundamentos = coletar_fundamentos()

    fundamentos.to_parquet(
        PASTA_SAIDA / "fundamentos_bancos.parquet",
        index=False,
    )

    logger.info(
        "Fundamentos salvos: %s empresas",
        len(fundamentos),
    )

    # Resumo da coleta
    logger.info(
        "Ativos com histórico: %s de %s",
        historico["ticker"].nunique(),
        len(TICKERS),
    )

    logger.info(
        "Ativos sem histórico: %s",
        set(TICKERS) - set(historico["ticker"].unique()),
    )

    print("\nÚltimos registros coletados:")
    print(historico.tail())


if __name__ == "__main__":
    main()
    
    
    
#%%
import pandas as pd

df = pd.read_parquet("../../data/fundamentos_bancos.parquet")
df.head()

# %%
import pandas as pd

df = pd.read_parquet("../../data/fundamentos_bancos.parquet")

print(f"Total de registros: {len(df)}")
print(f"Empresas distintas: {df['ticker'].nunique()}")


# %%
