import os
import json
import re
import urllib.request
import urllib.error
from datetime import datetime, timedelta

CACHE_FILE = os.path.join(os.path.expanduser("~"), ".usd_hrn_monitor_cache.json")

def get_headers():
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7",
    }

def fetch_sense_bank_direct():
    """
    Tries to fetch rates directly from sensebank.ua/currency-exchange
    Extracts all 3 modes: 'online', 'department', 'card'.
    """
    url = "https://sensebank.ua/currency-exchange"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=8) as resp:
        html = resp.read().decode("utf-8")

    m_nuxt = re.search(r'window\.__NUXT__\s*=\s*(.*?);\s*</script>', html, re.DOTALL)
    if not m_nuxt:
        raise ValueError("window.__NUXT__ not found on Sense Bank page")

    js = m_nuxt.group(1)

    m_params = re.match(r'\(function\(([^)]+)\)\s*\{', js)
    if not m_params:
        raise ValueError("Could not parse Nuxt function parameters")

    params = [p.strip() for p in m_params.group(1).split(',')]

    end_idx = js.rfind('}(')
    if end_idx == -1:
        raise ValueError("Could not find Nuxt arguments end marker")

    args_raw = js[end_idx+2:].strip()
    while args_raw.endswith(')') or args_raw.endswith(';'):
        args_raw = args_raw[:-1]

    args_clean = args_raw.replace('undefined', 'null')
    args = json.loads('[' + args_clean + ']')
    val_map = dict(zip(params, args))

    idx_content = js.find('content:{online:[')
    if idx_content == -1:
        idx_content = js.find('online:[')

    chunk = js[idx_content:idx_content+1400]

    def resolve_val(token):
        token = token.strip().strip('"').strip("'")
        if not token:
            return 0.0
        if token in val_map:
            resolved = val_map[token]
            try:
                return float(str(resolved).replace(",", ".").replace(" ", ""))
            except (ValueError, TypeError):
                return 0.0
        try:
            return float(token.replace(",", ".").replace(" ", ""))
        except (ValueError, TypeError):
            return 0.0

    rates = {}
    for mode in ['online', 'department', 'card']:
        mode_idx = chunk.find(f'{mode}:[')
        if mode_idx == -1:
            continue
        sub = chunk[mode_idx:chunk.find(']', mode_idx) + 1]
        m_rate = re.search(r'buy:\{[^}]*value:(?:"([^"]+)"|([a-zA-Z0-9_$]+))\},\s*sell:\{[^}]*value:(?:"([^"]+)"|([a-zA-Z0-9_$]+))\}', sub)
        if m_rate:
            buy_token = m_rate.group(1) or m_rate.group(2)
            sell_token = m_rate.group(3) or m_rate.group(4)
            buy_val = resolve_val(buy_token)
            sell_val = resolve_val(sell_token)
            rates[mode] = {
                'buy': round(buy_val, 2),
                'sell': round(sell_val, 2)
            }

    if not rates or 'online' not in rates:
        raise ValueError("Could not extract USD rates from Sense Bank structure")

    if 'card' in rates and rates['card']['sell'] == 0.0 and 'department' in rates:
        rates['card']['sell'] = rates['department']['sell']

    return rates

def fetch_sense_bank_mirror():
    """
    Fetches real-time Sense Bank rates via finance gateway if direct site is blocked by WAF.
    """
    url = "https://finance.ua/ua/banks/sense-bank"
    req = urllib.request.Request(url, headers=get_headers())
    with urllib.request.urlopen(req, timeout=8) as resp:
        html = resp.read().decode("utf-8")

    m = re.search(r'"sense-bank"\s*:\s*\{"usd"\s*:\s*\{"sell"\s*:\s*\{"value"\s*:\s*([\d\.]+)[^}]*\},\s*"buy"\s*:\s*\{"value"\s*:\s*([\d\.]+)', html)
    if not m:
        m = re.search(r'"sense-bank"\s*:\s*\{"usd"\s*:\s*\{"buy"\s*:\s*\{"value"\s*:\s*([\d\.]+)[^}]*\},\s*"sell"\s*:\s*\{"value"\s*:\s*([\d\.]+)', html)
        if m:
            b = float(m.group(1))
            s = float(m.group(2))
        else:
            raise ValueError("Sense Bank rate not found in finance mirror")
    else:
        val1 = float(m.group(1))
        val2 = float(m.group(2))
        b = min(val1, val2)
        s = max(val1, val2)

    rates = {
        'online': {'buy': round(b, 2), 'sell': round(s, 2)},
        'department': {'buy': round(b - 0.05, 2), 'sell': round(s, 2)},
        'card': {'buy': round(b, 2), 'sell': round(s, 2)}
    }
    return rates

def fetch_sense_bank():
    """
    Tries direct sensebank.ua first, then mirror.
    """
    try:
        return fetch_sense_bank_direct()
    except Exception as e_direct:
        try:
            return fetch_sense_bank_mirror()
        except Exception:
            raise e_direct

def fetch_privatbank_fallback():
    """
    Fallback to PrivatBank when Sense Bank is unavailable.
    """
    rates = {
        'online': {'buy': 0.0, 'sell': 0.0},
        'department': {'buy': 0.0, 'sell': 0.0},
        'card': {'buy': 0.0, 'sell': 0.0}
    }

    try:
        url5 = "https://api.privatbank.ua/p24api/pubinfo?exchange&json&coursid=5"
        req5 = urllib.request.Request(url5, headers=get_headers())
        with urllib.request.urlopen(req5, timeout=6) as resp:
            data5 = json.loads(resp.read().decode('utf-8'))
            for item in data5:
                if item.get('ccy') == 'USD':
                    rates['department']['buy'] = round(float(item['buy']), 2)
                    rates['department']['sell'] = round(float(item['sale']), 2)
    except Exception as e:
        print("PrivatBank coursid 5 error:", e)

    try:
        url11 = "https://api.privatbank.ua/p24api/pubinfo?exchange&json&coursid=11"
        req11 = urllib.request.Request(url11, headers=get_headers())
        with urllib.request.urlopen(req11, timeout=6) as resp:
            data11 = json.loads(resp.read().decode('utf-8'))
            for item in data11:
                if item.get('ccy') == 'USD':
                    b = round(float(item['buy']), 2)
                    s = round(float(item['sale']), 2)
                    rates['online']['buy'] = b
                    rates['online']['sell'] = s
                    rates['card']['buy'] = b
                    rates['card']['sell'] = s
    except Exception as e:
        print("PrivatBank coursid 11 error:", e)

    if rates['department']['buy'] == 0.0 and rates['online']['buy'] > 0.0:
        rates['department'] = dict(rates['online'])

    return rates

def fetch_nbu_data():
    """
    Fetches official NBU USD rate and 30-day history.
    """
    now = datetime.now()
    start_date = now - timedelta(days=35)
    start_str = start_date.strftime("%Y%m%d")
    end_str = now.strftime("%Y%m%d")

    url = f"https://bank.gov.ua/NBU_Exchange/exchange_site?start={start_str}&end={end_str}&valcode=usd&sort=exchangedate&order=asc&json"
    req = urllib.request.Request(url, headers=get_headers())
    with urllib.request.urlopen(req, timeout=8) as resp:
        data = json.loads(resp.read().decode('utf-8'))

    if not data:
        url_single = "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?valcode=USD&json"
        req_single = urllib.request.Request(url_single, headers=get_headers())
        with urllib.request.urlopen(req_single, timeout=8) as resp_single:
            single_data = json.loads(resp_single.read().decode('utf-8'))
            data = single_data

    history = []
    for item in data:
        ex_date = item.get('exchangedate', '')
        rate_val = float(item.get('rate', 0.0))
        parts = ex_date.split('.')
        short_d = f"{parts[0]}.{parts[1]}" if len(parts) >= 2 else ex_date
        history.append({
            'date': ex_date,
            'short_date': short_d,
            'rate': round(rate_val, 4)
        })

    if len(history) > 30:
        history = history[-30:]

    current_item = history[-1] if history else {'date': now.strftime("%d.%m.%Y"), 'rate': 0.0}
    prev_item = history[-2] if len(history) >= 2 else current_item

    cur_rate = current_item['rate']
    prev_rate = prev_item['rate']

    delta = round(cur_rate - prev_rate, 4)
    delta_percent = round((delta / prev_rate) * 100, 2) if prev_rate > 0 else 0.0

    return {
        'rate': cur_rate,
        'date': current_item['date'],
        'delta': delta,
        'delta_percent': delta_percent,
        'history': history
    }

def fetch_all_rates():
    """
    Main fetcher.
    """
    bank_rates = None
    is_fallback = False
    bank_source = "Sense Bank"
    bank_error = None

    try:
        bank_rates = fetch_sense_bank()
        bank_source = "Sense Bank"
    except Exception as e:
        bank_error = str(e)
        try:
            bank_rates = fetch_privatbank_fallback()
            is_fallback = True
            bank_source = "ПриватБанк (резервный)"
        except Exception:
            bank_rates = None

    nbu_data = None
    nbu_error = None
    try:
        nbu_data = fetch_nbu_data()
    except Exception as e:
        nbu_error = str(e)

    now_str = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

    if bank_rates is None or nbu_data is None:
        cached = load_cache()
        if cached:
            cached['is_offline'] = True
            cached['status_message'] = f"Офлайн (кеш от {cached.get('updated_at', 'ранее')})"
            return cached
        else:
            raise ConnectionError(f"Сетевая ошибка: банк ({bank_error}), НБУ ({nbu_error}) и нет кеша")

    result = {
        'bank_rates': bank_rates,
        'is_fallback': is_fallback,
        'bank_source': bank_source,
        'nbu': nbu_data,
        'updated_at': now_str,
        'is_offline': False,
        'status_message': "Данные актуальны"
    }

    save_cache(result)
    return result

def save_cache(data):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Cache save error:", e)

def load_cache():
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("Cache load error:", e)
        return None

if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    print("Testing data service...")
    data = fetch_all_rates()
    print("Source:", data['bank_source'])
    print("Is Fallback:", data['is_fallback'])
    print("Bank Rates:", json.dumps(data['bank_rates'], indent=2))
    print(f"NBU: {data['nbu']['rate']} (Delta: {data['nbu']['delta']} / {data['nbu']['delta_percent']}%)")
    print(f"History points: {len(data['nbu']['history'])}")
