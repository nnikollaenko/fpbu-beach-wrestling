import json
import re
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


def _translate_html(html: str) -> str:
    """Translate HTML with <p>/<br> tags paragraph-by-paragraph."""
    if not html or not html.strip():
        return ''
    result = []
    last_end = 0
    for m in re.finditer(r'<p>(.*?)</p>', html, re.I | re.S):
        before = html[last_end:m.start()].strip()
        if before:
            result.append(_translate(re.sub(r'<[^>]+>', '', before)))
        inner_plain = re.sub(r'<br\s*/?>', ' ', m.group(1), flags=re.I).strip()
        inner_plain = re.sub(r'<[^>]+>', '', inner_plain)
        translated = _translate(inner_plain) if inner_plain else ''
        result.append(f'<p>{translated}</p>')
        last_end = m.end()
    remaining = html[last_end:].strip()
    if remaining:
        result.append(_translate(re.sub(r'<[^>]+>', '', remaining)))
    return '\n'.join(result) if result else _translate(html)


def auto_fill_en(uk: dict, en: dict, html_fields: set = None) -> dict:
    """
    uk:  {field: ukrainian_text_or_html}
    en:  {field: admin_override}  — keeps admin value if non-empty, otherwise auto-translates
    html_fields: set of field names whose values are HTML (translated paragraph-by-paragraph)
    """
    result = {}
    for field, en_val in en.items():
        if en_val and en_val.strip():
            result[field] = en_val
        elif field == 'category':
            result[field] = _CATEGORY_MAP.get(uk.get(field, ''), uk.get(field, ''))
        else:
            uk_val = uk.get(field, '')
            if not uk_val or not uk_val.strip():
                result[field] = ''
            elif html_fields and field in html_fields:
                result[field] = _translate_html(uk_val)
            else:
                result[field] = _translate(uk_val)
    return result
