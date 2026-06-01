# Symboles connus comme inactifs sur Alpaca
INACTIVE_SYMBOLS = {"DFS", "DAY", "CTLT", "K", "MRO", "JNPR"}

input_file  = "data/sp500_symbols.csv"
output_file = "data/sp500_symbols.csv"

with open(input_file, "r") as f:
    lines = f.readlines()

header   = lines[0]
symbols  = [l.strip() for l in lines[1:] if l.strip()]
cleaned  = [s for s in symbols if s not in INACTIVE_SYMBOLS]

with open(output_file, "w") as f:
    f.write(header)
    for s in cleaned:
        f.write(s + "\n")

removed = set(symbols) - set(cleaned)
print(f"Symboles supprimés ({len(removed)}) : {removed}")
print(f"Symboles restants : {len(cleaned)}")