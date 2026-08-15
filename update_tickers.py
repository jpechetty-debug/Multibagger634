import csv
import re
import os

os.chdir(r"D:\Tradeidesa\Multibagger")

tickers = []
with open('unique_stocks_with_nse_symbols.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        sym = row.get('NSE Symbol', '').strip()
        name = row.get('Name', '').strip()
        
        target = sym if sym else name
        if target:
            clean = re.sub(r'[\.\s\(\)\-\&]', '', target).upper()
            if not clean.endswith('NS') and not clean.endswith('BO'):
                clean_sym = f"{clean}.NS"
            elif clean.endswith('NS'):
                clean_sym = f"{clean[:-2]}.NS"
            else:
                clean_sym = f"{clean}"
            if sym:
                # If explicit NSE symbol was given, use it cleanly
                clean_sym = f"{sym.strip().upper()}.NS" if not sym.strip().upper().endswith('.NS') else sym.strip().upper()
            tickers.append(f'"{clean_sym}"')

with open('ticker_list.py', 'r', encoding='utf-8') as f:
    content = f.read()

pattern = r"TICKERS\s*=\s*\[.*?\]"
new_tickers_str = "TICKERS = [\n    " + ",\n    ".join(tickers) + "\n]"
new_content = re.sub(pattern, new_tickers_str, content, flags=re.DOTALL)

with open('ticker_list.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"Successfully updated ticker_list.py with {len(tickers)} tickers from unique_stocks_with_nse_symbols.csv.")
