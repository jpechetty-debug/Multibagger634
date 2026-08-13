import csv
import re
import os

os.chdir(r"D:\Tradeidesa\Multibagger")

tickers = []
with open('unique_stocks_screener_final.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        name = row['Name'].strip()
        if name:
            if not name.endswith('.NS') and not name.endswith('.BO'):
                name += '.NS'
            tickers.append(f'"{name}"')

with open('ticker_list.py', 'r', encoding='utf-8') as f:
    content = f.read()

pattern = r"TICKERS\s*=\s*\[.*?\]"
new_tickers_str = "TICKERS = [\n    " + ",\n    ".join(tickers) + "\n]"
new_content = re.sub(pattern, new_tickers_str, content, flags=re.DOTALL)

with open('ticker_list.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"Successfully updated ticker_list.py with {len(tickers)} tickers.")
