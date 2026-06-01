import os
import json
from dotenv import load_dotenv
from groq import Groq
from bot.trader import (
    get_trading_client,
    get_data_client,
    get_open_positions,
    get_current_price,
    place_order,
)
from alpaca.trading.enums import OrderSide
from sf.snowflake_connection import get_conn
from bot.logger import setup_logger

load_dotenv()

logger = setup_logger()

# ── Client Groq ───────────────────────────────────────────────────────────────

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"

# ── Clients Alpaca ────────────────────────────────────────────────────────────

trading_client = get_trading_client()
data_client    = get_data_client()


# ── Outils disponibles ────────────────────────────────────────────────────────

def tool_place_order(symbol: str, side: str, qty: float) -> str:
    """Passe un ordre BUY ou SELL sur Alpaca."""
    order_side = OrderSide.BUY if side.upper() == "BUY" else OrderSide.SELL
    order = place_order(trading_client, symbol.upper(), order_side, qty)
    if order:
        return f"Ordre {side.upper()} passé avec succès : {qty} actions {symbol.upper()} | id={order.id}"
    return f"Erreur lors du passage de l'ordre {side.upper()} sur {symbol.upper()}"


def tool_get_positions() -> str:
    """Retourne les positions ouvertes sur Alpaca."""
    positions = get_open_positions(trading_client)
    if not positions:
        return "Aucune position ouverte actuellement."

    lines = []
    for symbol, pos in positions.items():
        qty        = float(pos.qty)
        avg_price  = float(pos.avg_entry_price)
        current    = float(pos.current_price)
        pnl        = float(pos.unrealized_pl)
        pnl_pct    = float(pos.unrealized_plpc) * 100
        lines.append(
            f"{symbol} : {qty} actions | Prix moyen={avg_price:.2f}$ | "
            f"Prix actuel={current:.2f}$ | PnL={pnl:.2f}$ ({pnl_pct:.2f}%)"
        )
    return "\n".join(lines)


def tool_get_portfolio() -> str:
    """Retourne la valeur du portefeuille et le cash disponible."""
    account      = trading_client.get_account()
    cash         = float(account.cash)
    portfolio    = float(account.portfolio_value)
    buying_power = float(account.buying_power)

    return (
        f"Valeur du portefeuille : {portfolio:,.2f}$\n"
        f"Cash disponible        : {cash:,.2f}$\n"
        f"Buying power           : {buying_power:,.2f}$"
    )


def tool_get_signal(symbol: str) -> str:
    """Retourne le dernier signal Gold pour un symbole donné."""
    conn = get_conn("GOLD")
    cur  = conn.cursor()

    query = """
        SELECT SYMBOL, SIGNAL, CONFIDENCE, TIMESTAMP
        FROM GOLD.TRADING_SIGNALS
        WHERE SYMBOL = %s
        ORDER BY TIMESTAMP DESC
        LIMIT 1
    """

    cur.execute(query, (symbol.upper(),))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return f"Aucun signal trouvé pour {symbol.upper()}"

    return (
        f"Signal pour {row[0]} : {row[1]} | "
        f"Confiance={row[2]:.1f}% | "
        f"Date={str(row[3])[:10]}"
    )


def tool_get_top_signals(signal_type: str = "BUY", limit: int = 10) -> str:
    """Retourne les meilleures opportunités du jour (BUY ou SELL)."""
    conn = get_conn("GOLD")
    cur  = conn.cursor()

    query = """
        WITH latest AS (
            SELECT
                SYMBOL,
                SIGNAL,
                CONFIDENCE,
                TIMESTAMP,
                ROW_NUMBER() OVER (PARTITION BY SYMBOL ORDER BY TIMESTAMP DESC) AS rn
            FROM GOLD.TRADING_SIGNALS
        )
        SELECT SYMBOL, SIGNAL, CONFIDENCE, TIMESTAMP
        FROM latest
        WHERE rn = 1
          AND SIGNAL = %s
        ORDER BY CONFIDENCE DESC, TIMESTAMP DESC
        LIMIT %s
    """

    cur.execute(query, (signal_type.upper(), limit))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        return f"Aucun signal {signal_type.upper()} trouvé."

    lines = [f"Top {limit} signaux {signal_type.upper()} :"]
    for row in rows:
        lines.append(
            f"  {row[0]} | Confiance={row[2]:.1f}% | Date={str(row[3])[:10]}"
        )
    return "\n".join(lines)


# ── Définition des outils pour Groq ──────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "place_order",
            "description": "Passe un ordre d'achat (BUY) ou de vente (SELL) sur Alpaca pour un symbole donné.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Le symbole de l'action (ex: AAPL, NVDA)"},
                    "side":   {"type": "string", "enum": ["BUY", "SELL"], "description": "Sens de l'ordre"},
                    "qty":    {"type": "number", "description": "Nombre d'actions"},
                },
                "required": ["symbol", "side", "qty"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_positions",
            "description": "Retourne la liste des positions ouvertes avec leur PnL.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_portfolio",
            "description": "Retourne la valeur totale du portefeuille, le cash et le buying power.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_signal",
            "description": "Retourne le dernier signal de trading (BUY/SELL/HOLD) pour un symbole donné.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Le symbole de l'action (ex: AAPL, NVDA)"},
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_signals",
            "description": "Retourne les meilleures opportunités de trading du jour.",
            "parameters": {
                "type": "object",
                "properties": {
                    "signal_type": {"type": "string", "enum": ["BUY", "SELL"], "description": "Type de signal"},
                    "limit":       {"type": "integer", "description": "Nombre de résultats (défaut: 10)"},
                },
            },
        },
    },
]

# ── Dispatcher — appelle le bon outil ─────────────────────────────────────────

def call_tool(name: str, args: dict) -> str:
    if name == "place_order":
        return tool_place_order(**args)
    elif name == "get_positions":
        return tool_get_positions()
    elif name == "get_portfolio":
        return tool_get_portfolio()
    elif name == "get_signal":
        return tool_get_signal(**args)
    elif name == "get_top_signals":
        return tool_get_top_signals(**args)
    else:
        return f"Outil inconnu : {name}"


# ── Boucle principale de l'agent ──────────────────────────────────────────────

def run_agent():
    print("\n🤖 Agent de trading — tape 'exit' pour quitter\n")

    messages = [
        {
            "role": "system",
            "content": (
                "Tu es un assistant de trading algorithmique. "
                "Tu aides l'utilisateur à gérer son portefeuille paper trading sur Alpaca. "
                "Tu peux passer des ordres, consulter les positions, la valeur du portefeuille "
                "et les signaux de trading générés par le bot. "
                "Réponds toujours en français. "
                "Avant de passer un ordre, confirme toujours avec l'utilisateur."
            ),
        }
    ]

    while True:
        user_input = input("Vous : ").strip()

        if user_input.lower() in ("exit", "quit", "q"):
            print("Au revoir !")
            break

        if not user_input:
            continue

        messages.append({"role": "user", "content": user_input})

        # ── Appel Groq ────────────────────────────────────────────────────────
        response = groq_client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            max_tokens=1024,
        )

        message = response.choices[0].message

        # ── Si l'agent veut appeler un outil ─────────────────────────────────
        while message.tool_calls:
            messages.append({
                "role":       "assistant",
                "content":    message.content or "",
                "tool_calls": [
                    {
                        "id":       tc.id,
                        "type":     "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in message.tool_calls
                ],
            })

            for tc in message.tool_calls:
                args   = json.loads(tc.function.arguments)
                result = call_tool(tc.function.name, args)
                print(f"\n⚙️  [{tc.function.name}] → {result}\n")

                messages.append({
                    "role":         "tool",
                    "tool_call_id": tc.id,
                    "content":      result,
                })

            # Relancer Groq avec le résultat de l'outil
            response = groq_client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                max_tokens=1024,
            )
            message = response.choices[0].message

        # ── Réponse finale ────────────────────────────────────────────────────
        reply = message.content or ""
        print(f"\n🤖 Agent : {reply}\n")
        messages.append({"role": "assistant", "content": reply})


if __name__ == "__main__":
    run_agent()