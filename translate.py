import json
import urllib.request
import urllib.parse

_CATEGORY_MAP = {
    'Змагання': 'Tournament',
    'Чемпіонат': 'Championship',
    'Першість': 'Championships',
    'Кубок': 'Cup',
    'Міжнародні': 'International',
    'Інше': 'Other',
}


def _translate(text: str) -> str:
    if not text or not text.strip():
        return ''
    try:
        params = urllib.parse.urlencode({'q': text.strip(), 'langpair': 'uk|en'})
        url = f'https://api.mymemory.translated.net/get?{params}'
        req = urllib.request.Request(url, headers={'User-Agent': 'beach-wrestling/1.0'})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode())
        if data.get('responseStatus') == 200:
            result = data['responseData']['translatedText']
            # MyMemory sometimes returns QUERY LENGTH LIMIT warnings
            if 'MYMEMORY WARNING' in result.upper():
                return text
            return result
    except Exception:
        pass
    return text


def auto_fill_en(uk: dict, en: dict) -> dict:
    """
    uk:  {field: ukrainian_text}
    en:  {field: admin_override}  — keeps admin value if non-empty, otherwise auto-translates
    """
    result = {}
    for field, en_val in en.items():
        if en_val and en_val.strip():
            result[field] = en_val
        elif field == 'category':
            result[field] = _CATEGORY_MAP.get(uk.get(field, ''), uk.get(field, ''))
        else:
            uk_val = uk.get(field, '')
            result[field] = _translate(uk_val) if uk_val and uk_val.strip() else ''
    return result
