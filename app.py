import os
import math
from datetime import datetime
from flask import Flask, render_template, abort, request, send_from_directory, redirect, make_response, g
import db
from translations import make_t

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

SUPPORTED_LANGS = ('uk', 'en')

# ── Language ──────────────────────────────────────────────────────────────────

@app.before_request
def set_language():
    lang = request.cookies.get('lang', 'uk')
    g.lang = lang if lang in SUPPORTED_LANGS else 'uk'
    g.t    = make_t(g.lang)


@app.route('/set-lang/<lang>')
def set_lang(lang):
    lang = lang if lang in SUPPORTED_LANGS else 'uk'
    resp = make_response(redirect(request.referrer or '/'))
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
        return MONTHS_EN[d.month] if g.lang == 'en' else MONTHS_UK[d.month]
    except Exception:
        return ''


@app.template_filter('year')
def year_f(date_str):
    try:
        return datetime.strptime(date_str[:10], '%Y-%m-%d').year
    except Exception:
        return ''


@app.context_processor
def inject_globals():
    return {
        'current_year': datetime.today().year,
        'lang': g.lang,
        't': g.t,
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    news      = db.get_news(limit=3)
    events    = db.get_upcoming_events(limit=5)
    champions = db.get_champions()[:6]
    partners  = db.get_partners()
    # Gallery photos for homepage (pick first 6)
    import os as _os
    gallery_dir = _os.path.join(app.config['UPLOAD_FOLDER'], 'gallery')
    gallery_photos = sorted(_os.listdir(gallery_dir))[:8] if _os.path.exists(gallery_dir) else []
    return render_template('index.html',
                           news=news, events=events,
                           champions=champions, partners=partners,
                           gallery_photos=gallery_photos)


@app.route('/news')
def news_list():
    page     = request.args.get('page', 1, type=int)
    per_page = 12
    news, total = db.get_news_paginated(page=page, per_page=per_page)
    total_pages = math.ceil(total / per_page) if total else 1
    return render_template('news/list.html', news=news, page=page,
                           total=total, total_pages=total_pages)


@app.route('/news/<slug>')
def news_article(slug):
    article = db.get_news_by_slug(slug)
    if not article: abort(404)
    related = db.get_news(limit=3, exclude_id=article['id'])
    return render_template('news/article.html', article=article, related=related)


@app.route('/calendar')
def calendar():
    years = db.get_calendar_years()
    if not years:
        years = list(range(datetime.today().year, 2016, -1))
    sel_year     = request.args.get('year', years[0] if years else datetime.today().year, type=int)
    sel_category = request.args.get('category', '')
    all_events   = db.get_events_by_year(sel_year)
    # Collect distinct categories for filter bar
    categories   = sorted({ev['category'] for ev in all_events if ev['category']})
    events       = [e for e in all_events if not sel_category or e['category'] == sel_category]
    return render_template('calendar.html', events=events, years=years, selected_year=sel_year,
                           categories=categories, sel_category=sel_category,
                           now_date=datetime.today().strftime('%Y-%m-%d'))


@app.route('/athletes')
def athletes():
    import sqlite3 as _sq
    weight = request.args.get('weight')
    gender = request.args.get('gender')

    conn = _sq.connect(os.path.join(os.path.dirname(__file__), 'data', 'wrestling.db'))
    conn.row_factory = _sq.Row

    # Build medal map {name: {gold, silver, bronze, total}}
    medal_rows = conn.execute('''
        SELECT name,
          SUM(CASE WHEN medal="gold"   THEN 1 ELSE 0 END) gold,
          SUM(CASE WHEN medal="silver" THEN 1 ELSE 0 END) silver,
          SUM(CASE WHEN medal="bronze" THEN 1 ELSE 0 END) bronze,
          COUNT(*) total
        FROM champions GROUP BY name
    ''').fetchall()
    medal_map = {r['name']: dict(r) for r in medal_rows}

    # Filter athletes (gender filtered in Python from medals/achievements text since no gender column)
    q, params = "SELECT * FROM athletes WHERE is_active=1", []
    if weight: q += " AND weight_class=?"; params.append(weight)
    q += " ORDER BY sort_order, name"
    all_team = conn.execute(q, params).fetchall()
    # Gender filter: cross-reference with champions table gender
    if gender:
        gendered = {r['name'] for r in conn.execute(
            "SELECT DISTINCT name FROM champions WHERE gender=?", (gender,)).fetchall()}
        # Also include athletes not in champions if gender filter is applied (show all for now)
        if gendered:
            team = [a for a in all_team if a['name'] in gendered]
        else:
            team = list(all_team)
    else:
        team = list(all_team)

    # Weight classes for filter bar
    weights = [r[0] for r in conn.execute(
        "SELECT DISTINCT weight_class FROM athletes WHERE is_active=1 AND weight_class IS NOT NULL ORDER BY weight_class"
    ).fetchall()]
    conn.close()

    return render_template('athletes.html', athletes=team, champions=db.get_champions()[:4],
                           medal_map=medal_map, weights=weights,
                           sel_weight=weight, sel_gender=gender)


@app.route('/champions')
def champions():
    years      = db.get_champion_years()
    sel_year   = request.args.get('year', type=int)
    age_group  = request.args.get('age')
    champs     = db.get_champions(year=sel_year, age_group=age_group)
    return render_template('champions.html', champions=champs, years=years,
                           selected_year=sel_year, selected_age=age_group)


@app.route('/federation/about')
def fed_about():
    return render_template('federation/about.html')


@app.route('/federation/history')
def fed_history():
    history = db.get_history()
    return render_template('federation/history.html', history=history)


@app.route('/federation/leadership')
def fed_leadership():
    leaders = db.get_leadership()
    return render_template('federation/leadership.html', leaders=leaders)


@app.route('/federation/committees')
def fed_committees():
    committees = db.get_committees()
    return render_template('federation/committees.html', committees=committees)


@app.route('/federation/secretariat')
def fed_secretariat():
    secretariat = db.get_secretariat()
    return render_template('federation/secretariat.html', secretariat=secretariat)


@app.route('/federation/regions')
def fed_regions():
    regions = db.get_regions()
    return render_template('federation/regions.html', regions=regions)


@app.route('/documents')
def documents():
    docs = db.get_documents(category='Офіційні документи')
    return render_template('documents/index.html', docs=docs, category='official')


@app.route('/documents/antidoping')
def documents_antidoping():
    docs = db.get_documents(category='Анти-допінг')
    return render_template('documents/index.html', docs=docs, category='antidoping')


@app.route('/documents/download/<filename>')
def download_document(filename):
    docs_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'docs')
    return send_from_directory(docs_dir, filename, as_attachment=True)


@app.route('/gallery')
def gallery():
    album      = request.args.get('album')
    album_info = db.get_album_info()
    if album:
        photos = db.get_gallery(album=album)
    else:
        photos = []
    return render_template('gallery.html', photos=photos, album_info=album_info,
                           current_album=album)


@app.route('/gallery/download/<album>')
def gallery_download(album):
    import zipfile, io as _io
    photos = db.get_gallery(album=album)
    gallery_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'gallery')
    buf = _io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for p in photos:
            filepath = os.path.join(gallery_dir, p['filename'])
            if os.path.exists(filepath):
                zf.write(filepath, os.path.basename(p['filename']))
    buf.seek(0)
    safe_name = album.replace(' ', '_').replace('/', '-')
    return send_from_directory(
        os.path.dirname(buf.name) if hasattr(buf, 'name') else '/',
        safe_name,
        as_attachment=True
    ) if False else (buf.getvalue(), 200, {
        'Content-Type': 'application/zip',
        'Content-Disposition': f'attachment; filename="{safe_name}.zip"'
    })


@app.route('/contacts')
def contacts():
    return render_template('contacts.html')


@app.route('/health')
def health():
    from flask import jsonify
    return jsonify({"status": "ok", "app": "UBWF / ФПБУ"})


@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('404.html'), 500


if __name__ == '__main__':
    db.init_db()
    db.migrate_db()
    app.run(debug=True, host='0.0.0.0', port=5001)
