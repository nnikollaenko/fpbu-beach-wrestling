import os
import re
import math
import html as _html
import time
import smtplib
from collections import defaultdict
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from flask import Flask, Blueprint, render_template, abort, request, send_from_directory, redirect, make_response, g, jsonify
import db
from translations import make_t
from icons import icon as _icon
import mail_config
from admin import admin_bp

# ── Simple in-memory rate limiter (per IP, resets on restart) ─────────────────
_rl_store: dict = defaultdict(list)
def _rate_ok(ip: str, limit: int = 3, window: int = 600) -> bool:
    now = time.time()
    hits = [t for t in _rl_store[ip] if now - t < window]
    _rl_store[ip] = hits
    if len(hits) >= limit:
        return False
    _rl_store[ip].append(now)
    return True

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-only-change-in-production')
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

app.register_blueprint(admin_bp)

# Init DB on first import (works both under gunicorn and dev server)
with app.app_context():
    db.init_db()
    db.migrate_db()

SUPPORTED_LANGS = ('uk', 'en')

# ── Public Blueprint — all visitor-facing pages live under /<lang>/ ───────────
pub = Blueprint('pub', __name__)

@pub.url_value_preprocessor
def _pull_lang(endpoint, values):
    lang = values.pop('lang', 'uk')
    if lang not in SUPPORTED_LANGS:
        abort(404)
    g.lang = lang
    g.t    = make_t(lang)

# ── Language ──────────────────────────────────────────────────────────────────

@app.before_request
def set_language():
    # Redirect bare root to /en/ for users with English preference
    if request.path == '/' and request.cookies.get('lang') == 'en':
        return redirect('/en/', 302)
    # url_value_preprocessor already set g.lang for pub routes; only fill in for admin/utility
    if not getattr(g, 'lang', None):
        lang = request.cookies.get('lang', 'uk')
        g.lang = lang if lang in SUPPORTED_LANGS else 'uk'
        g.t    = make_t(g.lang)


@app.route('/set-lang/<lang>')
def set_lang(lang):
    lang = lang if lang in SUPPORTED_LANGS else 'uk'
    ref = request.referrer or f'/{lang}/'
    from urllib.parse import urlparse
    parsed = urlparse(ref)
    path, qs = parsed.path, ('?' + parsed.query if parsed.query else '')
    new_path = f'/{lang}/'
    for other in SUPPORTED_LANGS:
        if path.startswith(f'/{other}/'):
            new_path = f'/{lang}/' + path[len(f'/{other}/'):]
            break
        elif path == f'/{other}':
            new_path = f'/{lang}/'
            break
    resp = make_response(redirect(new_path + qs))
    resp.set_cookie('lang', lang, max_age=365 * 24 * 3600, samesite='Lax')
    return resp


# ── Template filters ──────────────────────────────────────────────────────────

@app.template_filter('lf')
def lang_field(row, field):
    if g.lang == 'en':
        try:
            v = row[field + '_en']
            if v: return v
        except (KeyError, IndexError, TypeError):
            pass
    try:
        return row[field]
    except (KeyError, IndexError, TypeError):
        return ''


MONTHS_UK = ['','січня','лютого','березня','квітня','травня','червня',
             'липня','серпня','вересня','жовтня','листопада','грудня']
MONTHS_UK_SHORT = ['','Січ','Лют','Бер','Кві','Тра','Чер','Лип','Сер','Вер','Жов','Лис','Гру']
MONTHS_EN = ['','January','February','March','April','May','June',
             'July','August','September','October','November','December']
MONTHS_EN_SHORT = ['','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']


@app.template_filter('date_long')
def date_long(date_str):
    try:
        d = datetime.strptime(date_str[:10], '%Y-%m-%d')
        return f"{MONTHS_EN[d.month]} {d.day}, {d.year}" if g.lang == 'en' else f"{d.day} {MONTHS_UK[d.month]} {d.year}"
    except Exception:
        return date_str


@app.template_filter('date_short')
def date_short(date_str):
    try:
        d = datetime.strptime(date_str[:10], '%Y-%m-%d')
        return f"{d.day:02d} {MONTHS_EN_SHORT[d.month]}" if g.lang == 'en' else f"{d.day:02d} {MONTHS_UK_SHORT[d.month]}"
    except Exception:
        return date_str


@app.template_filter('month_full')
def month_full(date_str):
    try:
        d = datetime.strptime(date_str[:10], '%Y-%m-%d')
        return MONTHS_EN_SHORT[d.month] if g.lang == 'en' else MONTHS_UK_SHORT[d.month]
    except Exception:
        return ''


@app.template_filter('year')
def year_f(date_str):
    try:
        return datetime.strptime(date_str[:10], '%Y-%m-%d').year
    except Exception:
        return ''


CAT_EN = {
    'Відкритий турнір':       'Open Tournament',
    'Міжнародний турнір':     'International Tournament',
    'Міжнародні змагання':    'International Competition',
    'Міжнародні':             'International',
    'Чемпіонат України':      'Ukrainian Championship',
    'Першість України':       'Ukrainian League',
    'Першість':               'League',
    'Кубок України':          'Ukrainian Cup',
    'Кубок':                  'Cup',
    'Чемпіонат Європи':       'European Championship',
    'Чемпіонат світу':        'World Championship',
    'Чемпіонат Світу':        'World Championship',
    'Чемпіонат':              'Championship',
}

@app.template_filter('tcat')
def translate_category(cat):
    if not cat:
        return cat
    if g.lang == 'en':
        return CAT_EN.get(cat, cat)
    return cat

_WT_UK = {'До': 'Up to', 'до': 'up to', 'Від': 'From', 'від': 'from', 'кг': 'kg'}
@app.template_filter('wt')
def translate_weight(wc):
    if not wc or g.lang != 'en':
        return wc or ''
    result = wc
    for uk, en in _WT_UK.items():
        result = result.replace(uk, en)
    return result

_MEDAL_UK = [
    ('золотих', 'gold'), ('золоті', 'gold'), ('золота', 'gold'), ('золото', 'gold'),
    ('срібних', 'silver'), ('срібні', 'silver'), ('срібло', 'silver'),
    ('бронзових', 'bronze'), ('бронзові', 'bronze'), ('бронза', 'bronze'),
    ('медалей', 'medals'), ('медалі', 'medals'), ('медаль', 'medal'),
    ('ЧС', 'WC'), ('ЧЄ', 'EC'), ('ЧУ', 'UA'),
]
@app.template_filter('tmedals')
def translate_medals(text):
    if not text or g.lang != 'en':
        return text or ''
    result = text
    for uk, en in _MEDAL_UK:
        result = result.replace(uk, en)
    return result

@app.context_processor
def inject_globals():
    lang = getattr(g, 'lang', 'uk')
    path = request.path
    qs = ('?' + request.query_string.decode('utf-8', 'replace')) if request.query_string else ''
    # EN: /en/news → suffix /news; UK: /news → suffix /news
    suffix = path[3:] if path.startswith('/en') else path
    if not suffix:
        suffix = '/'
    lp = '/en' if lang == 'en' else ''
    return {
        'current_year': datetime.today().year,
        'lang': lang,
        't': getattr(g, 't', make_t('uk')),
        'icon': _icon,
        'lp': lp,
        'lp_uk': suffix + qs,
        'lp_en': '/en' + suffix + qs,
    }


# ── Typography: non-breaking spaces after prepositions ───────────────────────

_PREP_RE = re.compile(
    r'\b(з|в|у|і|й|та|на|до|по|за|від|під|над|між|без|про|при|чи|не|де|як|бо|або|але)\s+',
    re.IGNORECASE | re.UNICODE,
)
_YEAR_RE = re.compile(r'(\d{4})\s+(року|рік)', re.UNICODE)

def _fix_text_node(text):
    text = _PREP_RE.sub(lambda m: m.group(1) + ' ', text)
    text = _YEAR_RE.sub(r'\1 \2', text)
    return text

@app.after_request
def fix_typography(response):
    if 'text/html' not in response.content_type:
        return response
    html = response.get_data(as_text=True)
    # Process only text nodes (content between > and <), skip scripts/styles
    in_script = False
    result = []
    pos = 0
    for m in re.finditer(r'(<(?:script|style)[^>]*>)|</(?:script|style)>|>([^<]+)<', html, re.IGNORECASE | re.DOTALL):
        if m.group(1):          # opening <script> or <style>
            in_script = True
            result.append(html[pos:m.end()])
            pos = m.end()
        elif in_script and m.group(0).startswith('</'):  # closing tag
            in_script = False
            result.append(html[pos:m.end()])
            pos = m.end()
        elif not in_script and m.group(2) is not None:  # text node
            result.append(html[pos:m.start(2)])
            result.append(_fix_text_node(m.group(2)))
            pos = m.end(2)
    result.append(html[pos:])
    response.set_data(''.join(result).encode('utf-8'))
    return response


# ── Routes ────────────────────────────────────────────────────────────────────

@pub.route('/')
def index():
    news      = db.get_news(limit=3)
    events    = db.get_upcoming_events(limit=5)
    champions = db.get_champions()[:6]
    partners  = db.get_partners()
    import os as _os
    gallery_dir = _os.path.join(app.config['UPLOAD_FOLDER'], 'gallery')
    gallery_photos = sorted(_os.listdir(gallery_dir))[:8] if _os.path.exists(gallery_dir) else []
    return render_template('index.html',
                           news=news, events=events,
                           champions=champions, partners=partners,
                           gallery_photos=gallery_photos,
                           now_date=datetime.today().strftime('%Y-%m-%d'))


@pub.route('/news')
def news_list():
    page     = request.args.get('page', 1, type=int)
    per_page = 9
    news, total = db.get_news_paginated(page=page, per_page=per_page)
    total_pages = math.ceil(total / per_page) if total else 1
    return render_template('news/list.html', news=news, page=page,
                           total=total, total_pages=total_pages)


@pub.route('/news/<slug>')
def news_article(slug):
    article = db.get_news_by_slug(slug)
    if not article: abort(404)
    related = db.get_news(limit=3, exclude_id=article['id'])
    return render_template('news/article.html', article=article, related=related)


@pub.route('/calendar')
def calendar():
    years = db.get_calendar_years()
    if not years:
        years = list(range(datetime.today().year, 2016, -1))
    sel_year     = request.args.get('year', years[0] if years else datetime.today().year, type=int)
    sel_category = request.args.get('category', '')
    page         = request.args.get('page', 1, type=int)
    per_page     = 10
    all_events   = db.get_events_by_year(sel_year)
    categories   = sorted({ev['category'] for ev in all_events if ev['category']})
    categories_en = {}
    for ev in all_events:
        cat = ev['category']
        if cat and cat not in categories_en:
            en = (ev['category_en'] or '').strip()
            if not en or en == cat:
                en = CAT_EN.get(cat, cat)
            categories_en[cat] = en
    events, total = db.get_events_by_year_paginated(sel_year, page=page, per_page=per_page, category=sel_category or None)
    total_pages  = math.ceil(total / per_page) if total else 1
    extra_docs   = db.get_extra_docs_for_events([ev['id'] for ev in events])
    return render_template('calendar.html', events=events, years=years, selected_year=sel_year,
                           categories=categories, categories_en=categories_en,
                           sel_category=sel_category,
                           page=page, total_pages=total_pages, total=total,
                           extra_docs=extra_docs,
                           now_date=datetime.today().strftime('%Y-%m-%d'))


@pub.route('/athletes')
def athletes():
    import sqlite3 as _sq
    weight   = request.args.get('weight')
    gender   = request.args.get('gender', 'M')
    if gender not in ('M', 'F'):
        gender = 'M'
    sort     = request.args.get('sort', 'alpha')
    page     = request.args.get('page', 1, type=int)
    PER_PAGE = 12

    conn = _sq.connect(os.path.join(os.path.dirname(__file__), 'data', 'wrestling.db'))
    conn.row_factory = _sq.Row

    medal_rows = conn.execute('''
        SELECT name,
          SUM(CASE WHEN medal="gold"   THEN 1 ELSE 0 END) gold,
          SUM(CASE WHEN medal="silver" THEN 1 ELSE 0 END) silver,
          SUM(CASE WHEN medal="bronze" THEN 1 ELSE 0 END) bronze,
          COUNT(*) total
        FROM champions GROUP BY name
    ''').fetchall()
    medal_map = {r['name']: dict(r) for r in medal_rows}

    all_athletes = list(conn.execute("SELECT * FROM athletes WHERE is_active=1 ORDER BY name").fetchall())

    gendered_names = {r['name'] for r in conn.execute(
        "SELECT DISTINCT name FROM champions WHERE gender=?", (gender,)).fetchall()}
    gender_team = [a for a in all_athletes if a['name'] in gendered_names]
    if not gender_team:
        gender_team = all_athletes

    weights = sorted({a['weight_class'] for a in gender_team if a['weight_class']})

    if weight and weight in weights:
        team = [a for a in gender_team if a['weight_class'] == weight]
    else:
        weight = None
        team = gender_team

    now_year = datetime.today().year
    if sort == 'medals':
        def medal_key(a):
            m = medal_map.get(a['name'], {})
            return (-m.get('total', 0), -m.get('gold', 0), -m.get('silver', 0), a['name'])
        team.sort(key=medal_key)
    elif sort in ('age_young', 'age'):
        team.sort(key=lambda a: (-(a['birth_year'] or 0), a['name']))
    elif sort == 'age_old':
        team.sort(key=lambda a: ((a['birth_year'] or 9999), a['name']))
    elif sort in ('cat_senior', 'category'):
        def cat_key_s(a):
            if not a['birth_year']:
                return (3, a['name'])
            age = now_year - a['birth_year']
            rank = 0 if age >= 23 else (1 if age >= 20 else 2)
            return (rank, a['name'])
        team.sort(key=cat_key_s)
    elif sort == 'cat_junior':
        def cat_key_j(a):
            if not a['birth_year']:
                return (3, a['name'])
            age = now_year - a['birth_year']
            rank = 2 if age >= 23 else (1 if age >= 20 else 0)
            return (rank, a['name'])
        team.sort(key=cat_key_j)

    total       = len(team)
    total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    page        = max(1, min(page, total_pages))
    start       = (page - 1) * PER_PAGE
    team_page   = team[start:start + PER_PAGE]

    conn.close()

    return render_template('athletes.html',
                           athletes=team_page,
                           medal_map=medal_map, weights=weights,
                           sel_weight=weight, sel_gender=gender, sel_sort=sort,
                           page=page, total_pages=total_pages, total=total,
                           per_page=PER_PAGE)


@pub.route('/champions')
def champions():
    years      = db.get_champion_years()
    sel_year   = request.args.get('year', type=int)
    age_group  = request.args.get('age')
    champs     = db.get_champions(year=sel_year, age_group=age_group)
    return render_template('champions.html', champions=champs, years=years,
                           selected_year=sel_year, selected_age=age_group)


@pub.route('/about')
def fed_about():
    history = db.get_history()
    return render_template('federation/about.html', history=history)


@pub.route('/leadership')
def fed_leadership():
    leaders = db.get_leadership()
    return render_template('federation/leadership.html', leaders=leaders)


@pub.route('/committees')
def fed_committees():
    committees = db.get_committees()
    return render_template('federation/committees.html', committees=committees)


@pub.route('/secretariat')
def fed_secretariat():
    secretariat = db.get_secretariat()
    return render_template('federation/secretariat.html', secretariat=secretariat)


@pub.route('/regions')
def fed_regions():
    regions = db.get_regions()
    return render_template('federation/regions.html', regions=regions)


@pub.route('/documents')
def documents():
    docs = db.get_documents(category='Офіційні документи')
    return render_template('documents/index.html', docs=docs, category='official')


@pub.route('/documents/antidoping')
def documents_antidoping():
    docs = db.get_documents(category='Анти-допінг')
    return render_template('documents/index.html', docs=docs, category='antidoping')


@app.route('/documents/download/<filename>')
def download_document(filename):
    docs_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'docs')
    return send_from_directory(docs_dir, filename, as_attachment=True)


@pub.route('/gallery')
def gallery():
    album      = request.args.get('album')
    sel_sort   = request.args.get('sort', 'date')
    album_info = db.get_album_info(sort=sel_sort)
    if album:
        photos = db.get_gallery(album=album)
    else:
        photos = []
    return render_template('gallery.html', photos=photos, album_info=album_info,
                           current_album=album, sel_sort=sel_sort)


@app.route('/gallery/download/<album>')
def gallery_download(album):
    import zipfile, io as _io
    from urllib.parse import quote as _quote
    photos = db.get_gallery(album=album)
    buf = _io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_STORED) as zf:
        for p in photos:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], p['filename'])
            if os.path.exists(filepath):
                zf.write(filepath, os.path.basename(p['filename']))
    buf.seek(0)
    safe_name = album.replace(' ', '_').replace('/', '-') + '.zip'
    encoded_name = _quote(safe_name, safe='')
    return buf.getvalue(), 200, {
        'Content-Type': 'application/zip',
        'Content-Disposition': f"attachment; filename*=UTF-8''{encoded_name}",
    }


def _send_contact_email(name, phone, message):
    now = datetime.now().strftime('%d.%m.%Y %H:%M')
    esc_name    = _html.escape(name)
    esc_phone   = _html.escape(phone)
    esc_message = _html.escape(message)
    html = f"""<!DOCTYPE html>
<html lang="uk">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f0ede8;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="padding:40px 20px;">
  <tr><td align="center">
    <table width="560" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:14px;overflow:hidden;box-shadow:0 2px 16px rgba(0,0,0,0.08);">

      <!-- Header -->
      <tr><td style="background:#FF3B00;padding:30px 36px 26px;">
        <div style="color:#fff;font-size:26px;font-weight:900;letter-spacing:-0.03em;line-height:1;">ФПБУ</div>
        <div style="color:rgba(255,255,255,0.72);font-size:12px;margin-top:5px;letter-spacing:0.03em;text-transform:uppercase;">Федерація пляжної боротьби України</div>
      </td></tr>

      <!-- Title row -->
      <tr><td style="padding:32px 36px 0;">
        <div style="font-size:11px;font-weight:700;color:#FF3B00;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;">Нова заявка з сайту</div>
        <h1 style="margin:0;font-size:22px;font-weight:800;color:#111;letter-spacing:-0.02em;">Запит від відвідувача</h1>
      </td></tr>

      <!-- Info cards -->
      <tr><td style="padding:24px 36px 0;">
        <table width="100%" cellpadding="0" cellspacing="0">
          <tr>
            <td style="padding-bottom:14px;">
              <div style="font-size:11px;font-weight:700;color:#999;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">Ім'я</div>
              <div style="font-size:16px;font-weight:600;color:#111;">{esc_name}</div>
            </td>
          </tr>
          <tr>
            <td style="padding-bottom:14px;border-top:1px solid #f0ede8;padding-top:14px;">
              <div style="font-size:11px;font-weight:700;color:#999;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">Телефон</div>
              <div style="font-size:16px;font-weight:600;color:#111;">{esc_phone}</div>
            </td>
          </tr>
          <tr>
            <td style="border-top:1px solid #f0ede8;padding-top:14px;">
              <div style="font-size:11px;font-weight:700;color:#999;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:8px;">Повідомлення</div>
              <div style="font-size:15px;color:#333;line-height:1.65;white-space:pre-wrap;background:#f8f6f3;border-radius:8px;padding:14px 16px;">{esc_message}</div>
            </td>
          </tr>
        </table>
      </td></tr>

      <!-- CTA -->
      <tr><td style="padding:28px 36px;">
        <a href="tel:{phone.replace(' ','').replace('-','')}" style="display:inline-block;background:#FF3B00;color:#fff;text-decoration:none;font-weight:700;font-size:14px;padding:12px 24px;border-radius:50px;letter-spacing:0.01em;">
          Зателефонувати
        </a>
      </td></tr>

      <!-- Footer -->
      <tr><td style="background:#f8f6f3;padding:18px 36px;border-top:1px solid #ede9e3;">
        <div style="font-size:11px;color:#aaa;">Отримано: {now} &nbsp;·&nbsp; fpbu.com.ua</div>
      </td></tr>

    </table>
  </td></tr>
</table>
</body>
</html>"""

    msg = MIMEMultipart('alternative')
    msg['Subject'] = f'Заявка з сайту ФПБУ — {name}'
    msg['From']    = mail_config.MAIL_SENDER
    msg['To']      = mail_config.MAIL_RECIPIENT
    msg.attach(MIMEText(f"Ім'я: {name}\nТелефон: {phone}\n\nПовідомлення:\n{message}\n\nОтримано: {now}", 'plain', 'utf-8'))
    msg.attach(MIMEText(html, 'html', 'utf-8'))

    with smtplib.SMTP(mail_config.MAIL_SMTP_HOST, mail_config.MAIL_SMTP_PORT) as server:
        server.starttls()
        server.login(mail_config.MAIL_SENDER, mail_config.MAIL_PASSWORD)
        server.sendmail(mail_config.MAIL_SENDER, mail_config.MAIL_RECIPIENT, msg.as_string())


@pub.route('/contacts', methods=['GET', 'POST'])
def contacts():
    if request.method == 'POST':
        # Honeypot — bots fill hidden fields, humans don't
        if request.form.get('website', ''):
            return jsonify({'ok': True})

        ip = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip()
        if not _rate_ok(ip):
            return jsonify({'ok': False, 'error': 'rate_limit'}), 429

        name    = (request.form.get('name', '') or '').strip()[:120]
        code    = (request.form.get('phone_code', '+380') or '+380').strip()
        number  = re.sub(r'[^\d\s\-\(\)\+]', '', (request.form.get('phone_number', '') or '')).strip()[:30]
        message = (request.form.get('message', '') or '').strip()[:2000]
        phone   = f'{code} {number}'.strip()

        if len(name) < 2 or not number:
            return jsonify({'ok': False, 'error': 'required'}), 400

        try:
            _send_contact_email(name, phone, message)
            return jsonify({'ok': True})
        except Exception as exc:
            app.logger.error('Mail error: %s', exc)
            return jsonify({'ok': False, 'error': 'smtp'}), 500
    return render_template('contacts.html')


@pub.route('/privacy')
def privacy():
    return render_template('privacy.html')


@app.route('/health')
def health():
    return jsonify({"status": "ok", "app": "UBWF / ФПБУ"})


# ── Legacy redirects — old /federation/... URLs ───────────────────────────────
@app.route('/federation/about')
def _redir_fed_about():       return redirect('/about', 301)
@app.route('/federation/leadership')
def _redir_fed_leadership():  return redirect('/leadership', 301)
@app.route('/federation/committees')
def _redir_fed_committees():  return redirect('/committees', 301)
@app.route('/federation/secretariat')
def _redir_fed_secretariat(): return redirect('/secretariat', 301)
@app.route('/federation/regions')
def _redir_fed_regions():     return redirect('/regions', 301)
@app.route('/federation/history')
def _redir_fed_history():     return redirect('/about#history', 301)

# ── Legacy redirects — old /uk/... URLs → bare paths ─────────────────────────
@app.route('/uk/')
@app.route('/uk')
def _redir_uk_root():         return redirect('/', 301)
@app.route('/uk/news')
def _redir_uk_news():         return redirect('/news', 301)
@app.route('/uk/news/<slug>')
def _redir_uk_news_slug(slug): return redirect(f'/news/{slug}', 301)
@app.route('/uk/calendar')
def _redir_uk_calendar():     return redirect('/calendar', 301)
@app.route('/uk/athletes')
def _redir_uk_athletes():     return redirect('/athletes', 301)
@app.route('/uk/champions')
def _redir_uk_champions():    return redirect('/champions', 301)
@app.route('/uk/about')
def _redir_uk_about():        return redirect('/about', 301)
@app.route('/uk/leadership')
def _redir_uk_leadership():   return redirect('/leadership', 301)
@app.route('/uk/committees')
def _redir_uk_committees():   return redirect('/committees', 301)
@app.route('/uk/secretariat')
def _redir_uk_secretariat():  return redirect('/secretariat', 301)
@app.route('/uk/regions')
def _redir_uk_regions():      return redirect('/regions', 301)
@app.route('/uk/documents')
def _redir_uk_documents():    return redirect('/documents', 301)
@app.route('/uk/documents/antidoping')
def _redir_uk_docs_anti():    return redirect('/documents/antidoping', 301)
@app.route('/uk/gallery')
def _redir_uk_gallery():      return redirect('/gallery', 301)
@app.route('/uk/contacts')
def _redir_uk_contacts():     return redirect('/contacts', 301)
@app.route('/uk/privacy')
def _redir_uk_privacy():      return redirect('/privacy', 301)


@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('404.html'), 500


app.register_blueprint(pub, url_defaults={'lang': 'uk'})
app.register_blueprint(pub, url_prefix='/en', url_defaults={'lang': 'en'}, name='pub_en')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
