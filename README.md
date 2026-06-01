# Bot de Trading Algorithmique — S&P500

Bot de trading algorithmique basé sur une architecture data en médaillon (Bronze/Silver/Gold) avec Snowflake, utilisant un système de vote entre 3 stratégies pour générer des signaux de trading sur le S&P500.

## Architecture

Alpaca API
↓
Bronze (données brutes OHLCV + ordres)
↓
Silver (indicateurs techniques)
↓
Gold (signaux BUY/SELL/HOLD)
↓
Bot de trading (paper trading Alpaca)
↓
Agent LLM (interaction en langage naturel)

## Stratégies

Le bot utilise un système de vote — **2 stratégies sur 3 doivent être d'accord** pour valider un signal :

| Stratégie | Indicateurs | Signal BUY |
|---|---|---|
| TrendFollowing | MA20, MA50 | MA20 > MA50 |
| MeanReversion | RSI14, Bollinger Bands | Prix < BB_lower ET RSI < 35 |
| Momentum | MACD, ROC | MACD > Signal ET ROC > 0 |

- **Stop-loss** : -15% par position
- **Take-profit** : +50% par position
- **Taille de position** : 1 000$ par trade

## Résultats du Backtest (5 ans)

| Métrique | Valeur |
|---|---|
| Rendement total | +83.6% |
| S&P500 sur la même période | ~+75% |
| Max Drawdown | -69.56% |
| Ratio Sortino | 0.16 |
| Win rate | 41.25% |
| Nombre de trades | 3 341 |

## Structure du projet

bot_trading/
├── ingestion/          # Récupération données Alpaca
├── transformations/    # Calcul indicateurs + signaux
├── sf/                 # Connexion et chargement Snowflake
├── backtesting/        # Simulation et métriques
├── bot/
│   ├── trader.py       # Logique du bot automatique
│   ├── agent.py        # Agent LLM (Groq)
│   └── logger.py       # Logging journalier
├── data/               # Liste des symboles S&P500
├── logs/               # Logs journaliers du bot
├── main.py             # Pipeline complet
├── run_bot.py          # Lancement du bot automatique
└── run_agent.py        # Lancement de l'agent LLM

## Installation

```bash
git clone https://github.com/Alban140120/bot_trading.git
cd bot_trading
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

Créer un fichier `.env` à la racine :

```env
SNOWFLAKE_USER=xxx
SNOWFLAKE_PASSWORD=xxx
SNOWFLAKE_ACCOUNT=xxx
SNOWFLAKE_WAREHOUSE=xxx
SNOWFLAKE_DATABASE=xxx
SNOWFLAKE_SCHEMA=xxx
ALPACA_API_KEY=xxx
ALPACA_SECRET_KEY=xxx
GROQ_API_KEY=xxx
```

## Utilisation

```bash
# Initialiser les tables Snowflake (une seule fois)
python -m sf.setup_tables

# Lancer le pipeline complet (ingestion + signaux)
python main.py

# Lancer le bot de trading
python run_bot.py

# Lancer l'agent LLM interactif
python run_agent.py

# Lancer le backtest
python -m backtesting.run_backtest

# Générer la courbe de performance
python -m backtesting.plot_performance
```

## Automatisation

Le pipeline tourne automatiquement via **GitHub Actions** chaque jour ouvré à 16h30 UTC (après la clôture du marché US) :
- Ingestion des nouvelles données
- Mise à jour des signaux
- Passage des ordres sur Alpaca paper trading

## Stack technique

- **Python 3.11**
- **Snowflake** — stockage des données (architecture médaillon)
- **Alpaca API** — données de marché et passage d'ordres
- **Pandas** — transformation des données
- **Plotly** — visualisation des performances
- **GitHub Actions** — automatisation du pipeline

## Agent LLM

L'agent permet d'interagir avec le portefeuille en langage naturel via le terminal :

"Quel est mon portefeuille ?"
"Quelles sont mes positions actuelles ?"
"Quel est le signal pour NVIDIA ?"
"Quels sont les 5 meilleurs signaux BUY du moment ?"
"Achète 2 actions AAPL"
"Vends mes actions TSLA"
"Y a-t-il des signaux SELL intéressants ?"

L'agent demande toujours confirmation avant de passer un ordre.

## Automatisation

Le pipeline tourne automatiquement via **GitHub Actions** chaque jour ouvré à 16h30 UTC (après la clôture du marché US) :
- Ingestion des nouvelles données
- Mise à jour des signaux
- Passage des ordres sur Alpaca paper trading

## Stack technique

- **Python 3.11**
- **Snowflake** — stockage des données (architecture médaillon)
- **Alpaca API** — données de marché et passage d'ordres
- **Groq (Llama 3.3 70B)** — agent LLM en langage naturel
- **Pandas** — transformation des données
- **Plotly** — visualisation des performances
- **GitHub Actions** — automatisation du pipeline
