import os
import re
import uuid
import functools
from datetime import datetime
from flask import (Blueprint, render_template, request, redirect, url_for,
                   session, flash, current_app)
from werkzeug.utils import secure_filename
import db
from translate import auto_fill_en

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

ALLOWED_IMG = {'jpg', 'jpeg', 'png', 'webp', 'gif'}
ALLOWED_DOC = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'zip', 'rar'}


# ── i18n ──────────────────────────────────────────────────────────────────────

_L = {
    'uk': {
        'admin_panel': 'Адмін-панель',
        'dashboard': 'Дашборд',
        'news': 'Новини',
        'events': 'Заходи / Календар',
        'athletes': 'Спортсмени',
        'champions': 'Чемпіони',
        'documents': 'Документи',
        'gallery': 'Галерея',
        'leadership': 'Керівництво',
        'committees': 'Комітети',
        'secretariat': 'Секретаріат',
        'regions': 'Регіони',
        'view_site': 'На сайт',
        'logout': 'Вийти',
        'add': 'Додати',
        'edit': 'Редагувати',
        'delete': 'Видалити',
        'save': 'Зберегти',
        'cancel': 'Скасувати',
        'back': '← Назад',
        'id': 'ID',
        'actions': 'Дії',
        'title_uk': 'Заголовок (УКР)',
        'title_en': 'Заголовок (EN)',
        'content_uk': 'Контент (УКР) — HTML',
        'content_en': 'Контент (EN) — HTML',
        'name_uk': "Ім'я / Назва (УКР)",
        'name_en': "Ім'я / Назва (EN)",
        'role_uk': 'Посада (УКР)',
        'role_en': 'Посада (EN)',
        'bio_uk': 'Біографія (УКР)',
        'bio_en': 'Біографія (EN)',
        'description_uk': 'Опис (УКР)',
        'description_en': 'Опис (EN)',
        'email': 'Email',
        'phone': 'Телефон',
        'photo': 'Фото',
        'current_photo': 'Поточне фото',
        'sort_order': 'Порядок сортування',
        'date': 'Дата',
        'status': 'Статус',
        'category': 'Категорія',
        'region': 'Регіон',
        'featured': 'На головній',
        'active': 'Активний',
        'yes': 'Так',
        'no': 'Ні',
        'login_title': 'Вхід до адмін-панелі',
        'username': 'Логін',
        'password': 'Пароль',
        'sign_in': 'Увійти',
        'wrong_credentials': 'Невірний логін або пароль',
        'total_news': 'Новин',
        'total_events': 'Заходів',
        'total_athletes': 'Спортсменів',
        'total_champions': 'Рекордів чемпіонів',
        'total_documents': 'Документів',
        'total_gallery': 'Фото в галереї',
        'slug': 'Slug (URL-адреса)',
        'published_at': 'Дата публікації',
        'cover': 'Обкладинка',
        'location': 'Місце проведення',
        'start_date': 'Дата початку',
        'end_date': 'Дата кінця',
        'weight_class': 'Вагова категорія',
        'birth_year': 'Рік народження',
        'achievements_uk': 'Досягнення (УКР)',
        'achievements_en': 'Досягнення (EN)',
        'competition_uk': 'Змагання (УКР)',
        'competition_en': 'Змагання (EN)',
        'medal': 'Медаль',
        'age_group': 'Вікова категорія',
        'gender': 'Стать',
        'year': 'Рік',
        'total_medals': 'Загальний рахунок медалей',
        'album': 'Альбом',
        'caption': 'Підпис до фото',
        'taken_at': 'Дата зйомки',
        'upload_photos': 'Завантажити фото',
        'filename': 'Файл',
        'file_size': 'Розмір файлу',
        'uploaded_at': 'Дата завантаження',
        'city': 'Місто',
        'president': 'Президент федерації',
        'athletes_count': 'Кількість спортсменів',
        'contact_email': 'Контактний email',
        'head_name': 'Голова',
        'new_news': 'Нова новина',
        'edit_news': 'Редагувати новину',
        'new_event': 'Новий захід',
        'edit_event': 'Редагувати захід',
        'new_athlete': 'Новий спортсмен',
        'edit_athlete': 'Редагувати спортсмена',
        'new_champion': 'Новий запис чемпіона',
        'edit_champion': 'Редагувати запис чемпіона',
        'new_document': 'Новий документ',
        'edit_document': 'Редагувати документ',
        'new_leader': 'Новий член керівництва',
        'edit_leader': 'Редагувати',
        'new_committee': 'Новий комітет',
        'edit_committee': 'Редагувати',
        'new_secretariat': 'Новий член секретаріату',
        'edit_secretariat': 'Редагувати',
        'new_region': 'Новий регіон',
        'edit_region': 'Редагувати',
        'pdf_regulations': 'PDF — Положення',
        'pdf_program': 'PDF — Програма',
        'pdf_protocols': 'PDF — Протоколи',
        'confirm_delete': 'Видалити цей запис? Дія незворотня.',
        'saved': 'Збережено',
        'deleted': 'Видалено',
        'error': 'Помилка',
        'keep_current_file': 'залишити поточний',
    },
    'en': {
        'admin_panel': 'Admin Panel',
        'dashboard': 'Dashboard',
        'news': 'News',
        'events': 'Events / Calendar',
        'athletes': 'Athletes',
        'champions': 'Champions',
        'documents': 'Documents',
        'gallery': 'Gallery',
        'leadership': 'Leadership',
        'committees': 'Committees',
        'secretariat': 'Secretariat',
        'regions': 'Regions',
        'view_site': 'View Site',
        'logout': 'Logout',
        'add': 'Add',
        'edit': 'Edit',
        'delete': 'Delete',
        'save': 'Save',
        'cancel': 'Cancel',
        'back': '← Back',
        'id': 'ID',
        'actions': 'Actions',
        'title_uk': 'Title (UK)',
        'title_en': 'Title (EN)',
        'content_uk': 'Content (UK) — HTML',
        'content_en': 'Content (EN) — HTML',
        'name_uk': 'Name (UK)',
        'name_en': 'Name (EN)',
        'role_uk': 'Role (UK)',
        'role_en': 'Role (EN)',
        'bio_uk': 'Bio (UK)',
        'bio_en': 'Bio (EN)',
        'description_uk': 'Description (UK)',
        'description_en': 'Description (EN)',
        'email': 'Email',
        'phone': 'Phone',
        'photo': 'Photo',
        'current_photo': 'Current photo',
        'sort_order': 'Sort order',
        'date': 'Date',
        'status': 'Status',
        'category': 'Category',
        'region': 'Region',
        'featured': 'Featured',
        'active': 'Active',
        'yes': 'Yes',
        'no': 'No',
        'login_title': 'Admin Panel Login',
        'username': 'Username',
        'password': 'Password',
        'sign_in': 'Sign In',
        'wrong_credentials': 'Wrong username or password',
        'total_news': 'News',
        'total_events': 'Events',
        'total_athletes': 'Athletes',
        'total_champions': 'Champion records',
        'total_documents': 'Documents',
        'total_gallery': 'Gallery photos',
        'slug': 'Slug (URL)',
        'published_at': 'Published at',
        'cover': 'Cover image',
        'location': 'Location',
        'start_date': 'Start date',
        'end_date': 'End date',
        'weight_class': 'Weight class',
        'birth_year': 'Birth year',
        'achievements_uk': 'Achievements (UK)',
        'achievements_en': 'Achievements (EN)',
        'competition_uk': 'Competition (UK)',
        'competition_en': 'Competition (EN)',
        'medal': 'Medal',
        'age_group': 'Age group',
        'gender': 'Gender',
        'year': 'Year',
        'total_medals': 'Total medals summary',
        'album': 'Album',
        'caption': 'Caption',
        'taken_at': 'Date taken',
        'upload_photos': 'Upload photos',
        'filename': 'File',
        'file_size': 'File size',
        'uploaded_at': 'Uploaded at',
        'city': 'City',
        'president': 'Federation president',
        'athletes_count': 'Athletes count',
        'contact_email': 'Contact email',
        'head_name': 'Head',
        'new_news': 'New article',
        'edit_news': 'Edit article',
        'new_event': 'New event',
        'edit_event': 'Edit event',
        'new_athlete': 'New athlete',
        'edit_athlete': 'Edit athlete',
        'new_champion': 'New champion record',
        'edit_champion': 'Edit champion record',
        'new_document': 'New document',
        'edit_document': 'Edit document',
        'new_leader': 'New leader',
        'edit_leader': 'Edit',
        'new_committee': 'New committee',
        'edit_committee': 'Edit',
        'new_secretariat': 'New member',
        'edit_secretariat': 'Edit',
        'new_region': 'New region',
        'edit_region': 'Edit',
        'pdf_regulations': 'PDF — Regulations',
        'pdf_program': 'PDF — Program',
        'pdf_protocols': 'PDF — Protocols',
        'confirm_delete': 'Delete this record? This cannot be undone.',
        'saved': 'Saved',
        'deleted': 'Deleted',
        'error': 'Error',
        'keep_current_file': 'keep current file',
    },
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _lang():
    return session.get('admin_lang', 'uk')


def _ext(filename):
    return filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''


def _save_upload(file, subfolder, allowed):
    """Save uploaded file; return subfolder/uuid.ext or None."""
    if not file or not file.filename:
        return None
    ext = _ext(file.filename)
    if ext not in allowed:
        return None
    folder = os.path.join(current_app.config['UPLOAD_FOLDER'], subfolder)
    os.makedirs(folder, exist_ok=True)
    name = uuid.uuid4().hex[:16] + '.' + ext
    file.save(os.path.join(folder, name))
    return subfolder + '/' + name


def _slugify(text):
    """Transliterate Ukrainian → Latin for URL slugs."""
    TR = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'h', 'ґ': 'g', 'д': 'd',
        'е': 'e', 'є': 'ie', 'ж': 'zh', 'з': 'z', 'и': 'y', 'і': 'i',
        'ї': 'i', 'й': 'i', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n',
        'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
        'ь': '', 'ю': 'iu', 'я': 'ia',
        'ё': 'io', 'э': 'e', 'ъ': '', 'ы': 'y',
    }
    s = text.lower()
    result = ''.join(TR.get(c, c) for c in s)
    result = re.sub(r'[^a-z0-9]+', '-', result)
    return result.strip('-')[:80]


def _file_size_str(path):
    try:
        b = os.path.getsize(path)
        if b < 1024:
            return f'{b} Б'
        elif b < 1024 * 1024:
            return f'{b // 1024} КБ'
        else:
            return f'{b / 1024 / 1024:.1f} МБ'
    except Exception:
        return ''


def require_admin(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated


@admin_bp.context_processor
def _ctx():
    lang = _lang()
    return {
        'admin_lang': lang,
        'L': _L[lang],
        'admin_user': session.get('admin_username', ''),
        'req_endpoint': request.endpoint or '',
    }


# ── Auth ──────────────────────────────────────────────────────────────────────

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin.dashboard'))
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if db.verify_admin(username, password):
            session.permanent = True
            session['admin_logged_in'] = True
            session['admin_username'] = username
            return redirect(url_for('admin.dashboard'))
        error = _L[_lang()]['wrong_credentials']
    return render_template('admin/login.html', error=error)


@admin_bp.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    return redirect(url_for('admin.login'))


@admin_bp.route('/set-lang/<lang>')
@require_admin
def set_lang(lang):
    if lang in ('uk', 'en'):
        session['admin_lang'] = lang
    return redirect(request.referrer or url_for('admin.dashboard'))


# ── Dashboard ─────────────────────────────────────────────────────────────────

@admin_bp.route('/')
@require_admin
def dashboard():
    conn = db.get_db()
    stats = {
        'news':      conn.execute("SELECT COUNT(*) FROM news").fetchone()[0],
        'events':    conn.execute("SELECT COUNT(*) FROM events").fetchone()[0],
        'athletes':  conn.execute("SELECT COUNT(*) FROM athletes WHERE is_active=1").fetchone()[0],
        'champions': conn.execute("SELECT COUNT(*) FROM champions").fetchone()[0],
        'documents': conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0],
        'gallery':   conn.execute("SELECT COUNT(*) FROM gallery").fetchone()[0],
    }
    conn.close()
    return render_template('admin/dashboard.html', stats=stats)


# ── News ──────────────────────────────────────────────────────────────────────

@admin_bp.route('/news')
@require_admin
def news_list():
    conn = db.get_db()
    items = conn.execute("SELECT * FROM news ORDER BY published_at DESC").fetchall()
    conn.close()
    return render_template('admin/news_list.html', items=items)


@admin_bp.route('/news/new', methods=['GET', 'POST'])
@require_admin
def news_new():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        slug  = request.form.get('slug', '').strip() or _slugify(title)
        conn  = db.get_db()
        # Make slug unique
        base, i = slug, 1
        while conn.execute("SELECT id FROM news WHERE slug=?", (slug,)).fetchone():
            slug = f'{base}-{i}'; i += 1
        cover = _save_upload(request.files.get('cover'), 'news', ALLOWED_IMG)
        en = auto_fill_en({'title': title}, {'title': request.form.get('title_en', '')})
        conn.execute(
            "INSERT INTO news (slug,title,content,cover,published_at,is_featured,title_en,content_en) VALUES (?,?,?,?,?,?,?,?)",
            (slug, title,
             request.form.get('content', ''),
             cover,
             request.form.get('published_at') or datetime.today().strftime('%Y-%m-%d'),
             1 if request.form.get('is_featured') else 0,
             en.get('title', ''),
             request.form.get('content_en', ''))
        )
        conn.commit(); conn.close()
        flash(_L[_lang()]['saved'])
        return redirect(url_for('admin.news_list'))
    return render_template('admin/news_form.html', item=None)


@admin_bp.route('/news/<int:nid>/edit', methods=['GET', 'POST'])
@require_admin
def news_edit(nid):
    conn = db.get_db()
    item = conn.execute("SELECT * FROM news WHERE id=?", (nid,)).fetchone()
    if not item:
        conn.close(); return redirect(url_for('admin.news_list'))
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        slug  = request.form.get('slug', '').strip() or _slugify(title)
        # Allow same slug for this record, but not for others
        existing = conn.execute("SELECT id FROM news WHERE slug=? AND id!=?", (slug, nid)).fetchone()
        if existing:
            slug = slug + '-' + str(nid)
        cover = _save_upload(request.files.get('cover'), 'news', ALLOWED_IMG) or item['cover']
        en = auto_fill_en({'title': title}, {'title': request.form.get('title_en', '')})
        conn.execute(
            "UPDATE news SET title=?,slug=?,content=?,cover=?,published_at=?,is_featured=?,title_en=?,content_en=? WHERE id=?",
            (title, slug,
             request.form.get('content', ''),
             cover,
             request.form.get('published_at') or item['published_at'],
             1 if request.form.get('is_featured') else 0,
             en.get('title', ''),
             request.form.get('content_en', ''),
             nid)
        )
        conn.commit(); conn.close()
        flash(_L[_lang()]['saved'])
        return redirect(url_for('admin.news_list'))
    conn.close()
    return render_template('admin/news_form.html', item=item)


@admin_bp.route('/news/<int:nid>/delete', methods=['POST'])
@require_admin
def news_delete(nid):
    conn = db.get_db()
    conn.execute("DELETE FROM news WHERE id=?", (nid,))
    conn.commit(); conn.close()
    flash(_L[_lang()]['deleted'])
    return redirect(url_for('admin.news_list'))


# ── Events ────────────────────────────────────────────────────────────────────

@admin_bp.route('/events')
@require_admin
def events_list():
    conn = db.get_db()
    items = conn.execute("SELECT * FROM events ORDER BY start_date DESC").fetchall()
    conn.close()
    return render_template('admin/events_list.html', items=items)


@admin_bp.route('/events/new', methods=['GET', 'POST'])
@require_admin
def event_new():
    if request.method == 'POST':
        conn = db.get_db()
        pdf_reg  = _save_upload(request.files.get('pdf_regulations'), 'docs', ALLOWED_DOC)
        pdf_prog = _save_upload(request.files.get('pdf_program'), 'docs', ALLOWED_DOC)
        pdf_prot = _save_upload(request.files.get('pdf_protocols'), 'docs', ALLOWED_DOC)
        start    = request.form.get('start_date', '')
        year     = int(start[:4]) if start and len(start) >= 4 else datetime.today().year
        title    = request.form.get('title', '')
        location = request.form.get('location', '')
        category = request.form.get('category', 'Змагання')
        desc     = request.form.get('description', '')
        en = auto_fill_en(
            {'title': title, 'location': location, 'category': category, 'description': desc},
            {'title': request.form.get('title_en', ''),
             'location': request.form.get('location_en', ''),
             'category': request.form.get('category_en', ''),
             'description': request.form.get('description_en', '')}
        )
        conn.execute(
            "INSERT INTO events (title,location,start_date,end_date,category,status,description,"
            "title_en,location_en,category_en,description_en,year,pdf_regulations,pdf_program,pdf_protocols)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (title, location, start,
             request.form.get('end_date', '') or None,
             category, request.form.get('status', 'upcoming'), desc,
             en.get('title', ''), en.get('location', ''), en.get('category', ''), en.get('description', ''),
             request.form.get('year', year, type=int) or year,
             pdf_reg, pdf_prog, pdf_prot)
        )
        conn.commit(); conn.close()
        flash(_L[_lang()]['saved'])
        return redirect(url_for('admin.events_list'))
    return render_template('admin/event_form.html', item=None)


@admin_bp.route('/events/<int:eid>/edit', methods=['GET', 'POST'])
@require_admin
def event_edit(eid):
    conn = db.get_db()
    item = conn.execute("SELECT * FROM events WHERE id=?", (eid,)).fetchone()
    if not item:
        conn.close(); return redirect(url_for('admin.events_list'))
    if request.method == 'POST':
        start    = request.form.get('start_date', item['start_date'])
        year     = int(start[:4]) if start and len(start) >= 4 else (item['year'] or datetime.today().year)
        pdf_reg  = _save_upload(request.files.get('pdf_regulations'), 'docs', ALLOWED_DOC) or item['pdf_regulations']
        pdf_prog = _save_upload(request.files.get('pdf_program'), 'docs', ALLOWED_DOC) or item['pdf_program']
        pdf_prot = _save_upload(request.files.get('pdf_protocols'), 'docs', ALLOWED_DOC) or item['pdf_protocols']
        title    = request.form.get('title', '')
        location = request.form.get('location', '')
        category = request.form.get('category', 'Змагання')
        desc     = request.form.get('description', '')
        en = auto_fill_en(
            {'title': title, 'location': location, 'category': category, 'description': desc},
            {'title': request.form.get('title_en', ''),
             'location': request.form.get('location_en', ''),
             'category': request.form.get('category_en', ''),
             'description': request.form.get('description_en', '')}
        )
        conn.execute(
            "UPDATE events SET title=?,location=?,start_date=?,end_date=?,category=?,status=?,description=?,"
            "title_en=?,location_en=?,category_en=?,description_en=?,year=?,pdf_regulations=?,pdf_program=?,pdf_protocols=?"
            " WHERE id=?",
            (title, location, start,
             request.form.get('end_date', '') or None,
             category, request.form.get('status', 'upcoming'), desc,
             en.get('title', ''), en.get('location', ''), en.get('category', ''), en.get('description', ''),
             request.form.get('year', year, type=int) or year,
             pdf_reg, pdf_prog, pdf_prot,
             eid)
        )
        conn.commit(); conn.close()
        flash(_L[_lang()]['saved'])
        return redirect(url_for('admin.events_list'))
    conn.close()
    return render_template('admin/event_form.html', item=item)


@admin_bp.route('/events/<int:eid>/delete', methods=['POST'])
@require_admin
def event_delete(eid):
    conn = db.get_db()
    conn.execute("DELETE FROM events WHERE id=?", (eid,))
    conn.commit(); conn.close()
    flash(_L[_lang()]['deleted'])
    return redirect(url_for('admin.events_list'))


# ── Athletes ──────────────────────────────────────────────────────────────────

@admin_bp.route('/athletes')
@require_admin
def athletes_list():
    conn = db.get_db()
    items = conn.execute("SELECT * FROM athletes ORDER BY sort_order, name").fetchall()
    conn.close()
    return render_template('admin/athletes_list.html', items=items)


@admin_bp.route('/athletes/new', methods=['GET', 'POST'])
@require_admin
def athlete_new():
    if request.method == 'POST':
        photo  = _save_upload(request.files.get('photo'), 'athletes', ALLOWED_IMG)
        conn   = db.get_db()
        name   = request.form.get('name', '')
        wc     = request.form.get('weight_class', '')
        region = request.form.get('region', '')
        ach    = request.form.get('achievements', '')
        en = auto_fill_en(
            {'name': name, 'weight_class': wc, 'region': region, 'achievements': ach},
            {'name': request.form.get('name_en', ''),
             'weight_class': request.form.get('weight_class_en', ''),
             'region': request.form.get('region_en', ''),
             'achievements': request.form.get('achievements_en', '')}
        )
        conn.execute(
            "INSERT INTO athletes (name,name_en,weight_class,weight_class_en,birth_year,region,region_en,"
            "achievements,achievements_en,photo,is_active,sort_order) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (name, en.get('name', ''), wc, en.get('weight_class', ''),
             request.form.get('birth_year', None, type=int),
             region, en.get('region', ''), ach, en.get('achievements', ''),
             photo, 1 if request.form.get('is_active') else 0,
             request.form.get('sort_order', 0, type=int))
        )
        conn.commit(); conn.close()
        flash(_L[_lang()]['saved'])
        return redirect(url_for('admin.athletes_list'))
    return render_template('admin/athlete_form.html', item=None)


@admin_bp.route('/athletes/<int:aid>/edit', methods=['GET', 'POST'])
@require_admin
def athlete_edit(aid):
    conn = db.get_db()
    item = conn.execute("SELECT * FROM athletes WHERE id=?", (aid,)).fetchone()
    if not item:
        conn.close(); return redirect(url_for('admin.athletes_list'))
    if request.method == 'POST':
        photo  = _save_upload(request.files.get('photo'), 'athletes', ALLOWED_IMG) or item['photo']
        name   = request.form.get('name', '')
        wc     = request.form.get('weight_class', '')
        region = request.form.get('region', '')
        ach    = request.form.get('achievements', '')
        en = auto_fill_en(
            {'name': name, 'weight_class': wc, 'region': region, 'achievements': ach},
            {'name': request.form.get('name_en', ''),
             'weight_class': request.form.get('weight_class_en', ''),
             'region': request.form.get('region_en', ''),
             'achievements': request.form.get('achievements_en', '')}
        )
        conn.execute(
            "UPDATE athletes SET name=?,name_en=?,weight_class=?,weight_class_en=?,birth_year=?,"
            "region=?,region_en=?,achievements=?,achievements_en=?,photo=?,is_active=?,sort_order=? WHERE id=?",
            (name, en.get('name', ''), wc, en.get('weight_class', ''),
             request.form.get('birth_year', None, type=int),
             region, en.get('region', ''), ach, en.get('achievements', ''),
             photo, 1 if request.form.get('is_active') else 0,
             request.form.get('sort_order', 0, type=int),
             aid)
        )
        conn.commit(); conn.close()
        flash(_L[_lang()]['saved'])
        return redirect(url_for('admin.athletes_list'))
    conn.close()
    return render_template('admin/athlete_form.html', item=item)


@admin_bp.route('/athletes/<int:aid>/delete', methods=['POST'])
@require_admin
def athlete_delete(aid):
    conn = db.get_db()
    conn.execute("DELETE FROM athletes WHERE id=?", (aid,))
    conn.commit(); conn.close()
    flash(_L[_lang()]['deleted'])
    return redirect(url_for('admin.athletes_list'))


# ── Champions ─────────────────────────────────────────────────────────────────

@admin_bp.route('/champions')
@require_admin
def champions_list():
    conn = db.get_db()
    items = conn.execute("SELECT * FROM champions ORDER BY year DESC, sort_order").fetchall()
    conn.close()
    return render_template('admin/champions_list.html', items=items)


@admin_bp.route('/champions/new', methods=['GET', 'POST'])
@require_admin
def champion_new():
    if request.method == 'POST':
        photo = _save_upload(request.files.get('photo'), 'athletes', ALLOWED_IMG)
        conn  = db.get_db()
        name  = request.form.get('name', '')
        comp  = request.form.get('competition', '')
        en = auto_fill_en(
            {'name': name, 'competition': comp},
            {'name': request.form.get('name_en', ''),
             'competition': request.form.get('competition_en', '')}
        )
        conn.execute(
            "INSERT INTO champions (name,name_en,year,competition,competition_en,medal,age_group,weight_class,gender,photo,total_medals,sort_order) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (name, en.get('name', ''),
             request.form.get('year', datetime.today().year, type=int),
             comp, en.get('competition', ''),
             request.form.get('medal', 'gold'),
             request.form.get('age_group', 'Senior'),
             request.form.get('weight_class', ''),
             request.form.get('gender', 'M'),
             photo,
             request.form.get('total_medals', ''),
             request.form.get('sort_order', 0, type=int))
        )
        conn.commit(); conn.close()
        flash(_L[_lang()]['saved'])
        return redirect(url_for('admin.champions_list'))
    return render_template('admin/champion_form.html', item=None)


@admin_bp.route('/champions/<int:cid>/edit', methods=['GET', 'POST'])
@require_admin
def champion_edit(cid):
    conn = db.get_db()
    item = conn.execute("SELECT * FROM champions WHERE id=?", (cid,)).fetchone()
    if not item:
        conn.close(); return redirect(url_for('admin.champions_list'))
    if request.method == 'POST':
        photo = _save_upload(request.files.get('photo'), 'athletes', ALLOWED_IMG) or item['photo']
        name  = request.form.get('name', '')
        comp  = request.form.get('competition', '')
        en = auto_fill_en(
            {'name': name, 'competition': comp},
            {'name': request.form.get('name_en', ''),
             'competition': request.form.get('competition_en', '')}
        )
        conn.execute(
            "UPDATE champions SET name=?,name_en=?,year=?,competition=?,competition_en=?,medal=?,age_group=?,weight_class=?,gender=?,photo=?,total_medals=?,sort_order=? WHERE id=?",
            (name, en.get('name', ''),
             request.form.get('year', datetime.today().year, type=int),
             comp, en.get('competition', ''),
             request.form.get('medal', 'gold'),
             request.form.get('age_group', 'Senior'),
             request.form.get('weight_class', ''),
             request.form.get('gender', 'M'),
             photo,
             request.form.get('total_medals', ''),
             request.form.get('sort_order', 0, type=int),
             cid)
        )
        conn.commit(); conn.close()
        flash(_L[_lang()]['saved'])
        return redirect(url_for('admin.champions_list'))
    conn.close()
    return render_template('admin/champion_form.html', item=item)


@admin_bp.route('/champions/<int:cid>/delete', methods=['POST'])
@require_admin
def champion_delete(cid):
    conn = db.get_db()
    conn.execute("DELETE FROM champions WHERE id=?", (cid,))
    conn.commit(); conn.close()
    flash(_L[_lang()]['deleted'])
    return redirect(url_for('admin.champions_list'))


# ── Documents ─────────────────────────────────────────────────────────────────

@admin_bp.route('/documents')
@require_admin
def documents_list():
    conn = db.get_db()
    items = conn.execute("SELECT * FROM documents ORDER BY category, uploaded_at DESC").fetchall()
    conn.close()
    return render_template('admin/documents_list.html', items=items)


@admin_bp.route('/documents/new', methods=['GET', 'POST'])
@require_admin
def document_new():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or not file.filename:
            flash(_L[_lang()]['error'])
            return render_template('admin/document_form.html', item=None)
        ext = _ext(file.filename)
        if ext not in ALLOWED_DOC:
            flash(_L[_lang()]['error'])
            return render_template('admin/document_form.html', item=None)
        folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'docs')
        os.makedirs(folder, exist_ok=True)
        safe = secure_filename(file.filename)
        # Use original name if not already taken, else prefix with uuid
        dest = os.path.join(folder, safe)
        if os.path.exists(dest):
            safe = uuid.uuid4().hex[:8] + '-' + safe
            dest = os.path.join(folder, safe)
        file.save(dest)
        size_str = _file_size_str(dest)
        conn = db.get_db()
        title = request.form.get('title', '')
        en = auto_fill_en({'title': title}, {'title': request.form.get('title_en', '')})
        conn.execute(
            "INSERT INTO documents (title,title_en,filename,category,uploaded_at,file_size) VALUES (?,?,?,?,?,?)",
            (title, en.get('title', ''),
             safe,
             request.form.get('category', 'Офіційні документи'),
             datetime.today().strftime('%Y-%m-%d'),
             size_str)
        )
        conn.commit(); conn.close()
        flash(_L[_lang()]['saved'])
        return redirect(url_for('admin.documents_list'))
    return render_template('admin/document_form.html', item=None)


@admin_bp.route('/documents/<int:did>/edit', methods=['GET', 'POST'])
@require_admin
def document_edit(did):
    conn = db.get_db()
    item = conn.execute("SELECT * FROM documents WHERE id=?", (did,)).fetchone()
    if not item:
        conn.close(); return redirect(url_for('admin.documents_list'))
    if request.method == 'POST':
        filename = item['filename']
        file = request.files.get('file')
        if file and file.filename:
            ext = _ext(file.filename)
            if ext in ALLOWED_DOC:
                folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'docs')
                os.makedirs(folder, exist_ok=True)
                safe = secure_filename(file.filename)
                dest = os.path.join(folder, safe)
                if os.path.exists(dest) and safe != filename:
                    safe = uuid.uuid4().hex[:8] + '-' + safe
                    dest = os.path.join(folder, safe)
                file.save(dest)
                filename = safe
        size_str = _file_size_str(os.path.join(current_app.config['UPLOAD_FOLDER'], 'docs', filename))
        title = request.form.get('title', '')
        en = auto_fill_en({'title': title}, {'title': request.form.get('title_en', '')})
        conn.execute(
            "UPDATE documents SET title=?,title_en=?,filename=?,category=?,file_size=? WHERE id=?",
            (title, en.get('title', ''),
             filename,
             request.form.get('category', item['category']),
             size_str or item['file_size'],
             did)
        )
        conn.commit(); conn.close()
        flash(_L[_lang()]['saved'])
        return redirect(url_for('admin.documents_list'))
    conn.close()
    return render_template('admin/document_form.html', item=item)


@admin_bp.route('/documents/<int:did>/delete', methods=['POST'])
@require_admin
def document_delete(did):
    conn = db.get_db()
    conn.execute("DELETE FROM documents WHERE id=?", (did,))
    conn.commit(); conn.close()
    flash(_L[_lang()]['deleted'])
    return redirect(url_for('admin.documents_list'))


# ── Gallery ───────────────────────────────────────────────────────────────────

@admin_bp.route('/gallery')
@require_admin
def gallery_list():
    conn = db.get_db()
    albums = conn.execute(
        "SELECT album, COUNT(*) cnt, MIN(filename) cover FROM gallery GROUP BY album ORDER BY album"
    ).fetchall()
    album_filter = request.args.get('album', '')
    if album_filter:
        photos = conn.execute(
            "SELECT * FROM gallery WHERE album=? ORDER BY taken_at DESC", (album_filter,)
        ).fetchall()
    else:
        photos = conn.execute("SELECT * FROM gallery ORDER BY taken_at DESC LIMIT 60").fetchall()
    conn.close()
    return render_template('admin/gallery.html', albums=albums, photos=photos,
                           album_filter=album_filter)


@admin_bp.route('/gallery/upload', methods=['POST'])
@require_admin
def gallery_upload():
    album   = (request.form.get('album') or '').strip() or 'Загальний'
    caption = request.form.get('caption', '').strip()
    taken   = request.form.get('taken_at', '') or None
    files   = request.files.getlist('photos')
    folder  = os.path.join(current_app.config['UPLOAD_FOLDER'], 'gallery')
    os.makedirs(folder, exist_ok=True)
    conn    = db.get_db()
    # Ensure album has a translation entry
    existing = conn.execute("SELECT name_en FROM gallery_albums WHERE name=?", (album,)).fetchone()
    if not existing:
        en = auto_fill_en({'name': album}, {'name': ''})
        conn.execute("INSERT OR IGNORE INTO gallery_albums (name, name_en) VALUES (?,?)",
                     (album, en.get('name', '')))
    count   = 0
    for f in files:
        if not f or not f.filename:
            continue
        ext = _ext(f.filename)
        if ext not in ALLOWED_IMG:
            continue
        name = uuid.uuid4().hex[:16] + '.' + ext
        f.save(os.path.join(folder, name))
        conn.execute(
            "INSERT INTO gallery (caption, filename, album, taken_at) VALUES (?,?,?,?)",
            (caption, 'gallery/' + name, album, taken)
        )
        count += 1
    conn.commit(); conn.close()
    flash(f'{count} фото завантажено' if _lang() == 'uk' else f'{count} photos uploaded')
    return redirect(url_for('admin.gallery_list', album=album))


@admin_bp.route('/gallery/<int:pid>/delete', methods=['POST'])
@require_admin
def gallery_delete(pid):
    conn = db.get_db()
    row = conn.execute("SELECT filename FROM gallery WHERE id=?", (pid,)).fetchone()
    if row:
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], row['filename'])
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except OSError:
                pass
    conn.execute("DELETE FROM gallery WHERE id=?", (pid,))
    conn.commit(); conn.close()
    flash(_L[_lang()]['deleted'])
    return redirect(request.referrer or url_for('admin.gallery_list'))


# ── Leadership ────────────────────────────────────────────────────────────────

@admin_bp.route('/leadership')
@require_admin
def leadership_list():
    rows = db.get_leadership()
    return render_template('admin/leadership.html', items=rows)


@admin_bp.route('/leadership/new', methods=['POST'])
@require_admin
def leadership_new():
    photo = _save_upload(request.files.get('photo'), 'leadership', ALLOWED_IMG)
    conn  = db.get_db()
    name  = request.form.get('name', '')
    role  = request.form.get('role', '')
    bio   = request.form.get('bio', '')
    en = auto_fill_en(
        {'name': name, 'role': role, 'bio': bio},
        {'name': request.form.get('name_en', ''),
         'role': request.form.get('role_en', ''),
         'bio': request.form.get('bio_en', '')}
    )
    conn.execute(
        "INSERT INTO leadership (name,name_en,role,role_en,bio,bio_en,photo,sort_order) VALUES (?,?,?,?,?,?,?,?)",
        (name, en.get('name', ''), role, en.get('role', ''),
         bio, en.get('bio', ''), photo,
         request.form.get('sort_order', 0, type=int))
    )
    conn.commit(); conn.close()
    flash(_L[_lang()]['saved'])
    return redirect(url_for('admin.leadership_list'))


@admin_bp.route('/leadership/<int:lid>/edit', methods=['GET', 'POST'])
@require_admin
def leadership_edit(lid):
    conn = db.get_db()
    item = conn.execute("SELECT * FROM leadership WHERE id=?", (lid,)).fetchone()
    if not item:
        conn.close(); return redirect(url_for('admin.leadership_list'))
    if request.method == 'POST':
        photo = _save_upload(request.files.get('photo'), 'leadership', ALLOWED_IMG) or item['photo']
        name  = request.form.get('name', '')
        role  = request.form.get('role', '')
        bio   = request.form.get('bio', '')
        en = auto_fill_en(
            {'name': name, 'role': role, 'bio': bio},
            {'name': request.form.get('name_en', ''),
             'role': request.form.get('role_en', ''),
             'bio': request.form.get('bio_en', '')}
        )
        conn.execute(
            "UPDATE leadership SET name=?,name_en=?,role=?,role_en=?,bio=?,bio_en=?,photo=?,sort_order=? WHERE id=?",
            (name, en.get('name', ''), role, en.get('role', ''),
             bio, en.get('bio', ''), photo,
             request.form.get('sort_order', 0, type=int),
             lid)
        )
        conn.commit(); conn.close()
        flash(_L[_lang()]['saved'])
        return redirect(url_for('admin.leadership_list'))
    conn.close()
    return render_template('admin/leadership.html',
                           items=db.get_leadership(), edit_item=item)


@admin_bp.route('/leadership/<int:lid>/delete', methods=['POST'])
@require_admin
def leadership_delete(lid):
    conn = db.get_db()
    conn.execute("DELETE FROM leadership WHERE id=?", (lid,))
    conn.commit(); conn.close()
    flash(_L[_lang()]['deleted'])
    return redirect(url_for('admin.leadership_list'))


# ── Committees ────────────────────────────────────────────────────────────────

@admin_bp.route('/committees')
@require_admin
def committees_list():
    rows = db.get_committees()
    return render_template('admin/committees.html', items=rows)


@admin_bp.route('/committees/new', methods=['POST'])
@require_admin
def committee_new():
    conn      = db.get_db()
    name      = request.form.get('name', '')
    desc      = request.form.get('description', '')
    head_name = request.form.get('head_name', '')
    en = auto_fill_en(
        {'name': name, 'description': desc, 'head_name': head_name},
        {'name': request.form.get('name_en', ''),
         'description': request.form.get('description_en', ''),
         'head_name': request.form.get('head_name_en', '')}
    )
    conn.execute(
        "INSERT INTO committees (name,name_en,description,description_en,head_name,head_name_en,phone,email,sort_order) VALUES (?,?,?,?,?,?,?,?,?)",
        (name, en.get('name', ''), desc, en.get('description', ''),
         head_name, en.get('head_name', ''),
         request.form.get('phone', ''),
         request.form.get('email', ''),
         request.form.get('sort_order', 0, type=int))
    )
    conn.commit(); conn.close()
    flash(_L[_lang()]['saved'])
    return redirect(url_for('admin.committees_list'))


@admin_bp.route('/committees/<int:cid>/edit', methods=['GET', 'POST'])
@require_admin
def committee_edit(cid):
    conn = db.get_db()
    item = conn.execute("SELECT * FROM committees WHERE id=?", (cid,)).fetchone()
    if not item:
        conn.close(); return redirect(url_for('admin.committees_list'))
    if request.method == 'POST':
        name      = request.form.get('name', '')
        desc      = request.form.get('description', '')
        head_name = request.form.get('head_name', '')
        en = auto_fill_en(
            {'name': name, 'description': desc, 'head_name': head_name},
            {'name': request.form.get('name_en', ''),
             'description': request.form.get('description_en', ''),
             'head_name': request.form.get('head_name_en', '')}
        )
        conn.execute(
            "UPDATE committees SET name=?,name_en=?,description=?,description_en=?,head_name=?,head_name_en=?,phone=?,email=?,sort_order=? WHERE id=?",
            (name, en.get('name', ''), desc, en.get('description', ''),
             head_name, en.get('head_name', ''),
             request.form.get('phone', ''),
             request.form.get('email', ''),
             request.form.get('sort_order', 0, type=int),
             cid)
        )
        conn.commit(); conn.close()
        flash(_L[_lang()]['saved'])
        return redirect(url_for('admin.committees_list'))
    conn.close()
    return render_template('admin/committees.html',
                           items=db.get_committees(), edit_item=item)


@admin_bp.route('/committees/<int:cid>/delete', methods=['POST'])
@require_admin
def committee_delete(cid):
    conn = db.get_db()
    conn.execute("DELETE FROM committees WHERE id=?", (cid,))
    conn.commit(); conn.close()
    flash(_L[_lang()]['deleted'])
    return redirect(url_for('admin.committees_list'))


# ── Secretariat ───────────────────────────────────────────────────────────────

@admin_bp.route('/secretariat')
@require_admin
def secretariat_list():
    rows = db.get_secretariat()
    return render_template('admin/secretariat.html', items=rows)


@admin_bp.route('/secretariat/new', methods=['POST'])
@require_admin
def secretariat_new():
    photo = _save_upload(request.files.get('photo'), 'leadership', ALLOWED_IMG)
    conn  = db.get_db()
    name  = request.form.get('name', '')
    role  = request.form.get('role', '')
    en = auto_fill_en(
        {'name': name, 'role': role},
        {'name': request.form.get('name_en', ''),
         'role': request.form.get('role_en', '')}
    )
    conn.execute(
        "INSERT INTO secretariat (name,name_en,role,role_en,email,phone,photo,sort_order) VALUES (?,?,?,?,?,?,?,?)",
        (name, en.get('name', ''), role, en.get('role', ''),
         request.form.get('email', ''),
         request.form.get('phone', ''),
         photo,
         request.form.get('sort_order', 0, type=int))
    )
    conn.commit(); conn.close()
    flash(_L[_lang()]['saved'])
    return redirect(url_for('admin.secretariat_list'))


@admin_bp.route('/secretariat/<int:sid>/edit', methods=['GET', 'POST'])
@require_admin
def secretariat_edit(sid):
    conn = db.get_db()
    item = conn.execute("SELECT * FROM secretariat WHERE id=?", (sid,)).fetchone()
    if not item:
        conn.close(); return redirect(url_for('admin.secretariat_list'))
    if request.method == 'POST':
        photo = _save_upload(request.files.get('photo'), 'leadership', ALLOWED_IMG) or item['photo']
        name  = request.form.get('name', '')
        role  = request.form.get('role', '')
        en = auto_fill_en(
            {'name': name, 'role': role},
            {'name': request.form.get('name_en', ''),
             'role': request.form.get('role_en', '')}
        )
        conn.execute(
            "UPDATE secretariat SET name=?,name_en=?,role=?,role_en=?,email=?,phone=?,photo=?,sort_order=? WHERE id=?",
            (name, en.get('name', ''), role, en.get('role', ''),
             request.form.get('email', ''),
             request.form.get('phone', ''),
             photo,
             request.form.get('sort_order', 0, type=int),
             sid)
        )
        conn.commit(); conn.close()
        flash(_L[_lang()]['saved'])
        return redirect(url_for('admin.secretariat_list'))
    conn.close()
    return render_template('admin/secretariat.html',
                           items=db.get_secretariat(), edit_item=item)


@admin_bp.route('/secretariat/<int:sid>/delete', methods=['POST'])
@require_admin
def secretariat_delete(sid):
    conn = db.get_db()
    conn.execute("DELETE FROM secretariat WHERE id=?", (sid,))
    conn.commit(); conn.close()
    flash(_L[_lang()]['deleted'])
    return redirect(url_for('admin.secretariat_list'))


# ── Regions ───────────────────────────────────────────────────────────────────

@admin_bp.route('/regions')
@require_admin
def regions_list():
    rows = db.get_regions()
    return render_template('admin/regions.html', items=rows)


@admin_bp.route('/regions/new', methods=['POST'])
@require_admin
def region_new():
    conn      = db.get_db()
    name      = request.form.get('name', '')
    city      = request.form.get('city', '')
    president = request.form.get('president', '')
    en = auto_fill_en(
        {'name': name, 'city': city, 'president': president},
        {'name': request.form.get('name_en', ''),
         'city': request.form.get('city_en', ''),
         'president': request.form.get('president_en', '')}
    )
    conn.execute(
        "INSERT INTO regions (name,name_en,city,city_en,president,president_en,contact_email,athletes_count,sort_order) VALUES (?,?,?,?,?,?,?,?,?)",
        (name, en.get('name', ''), city, en.get('city', ''),
         president, en.get('president', ''),
         request.form.get('contact_email', ''),
         request.form.get('athletes_count', 0, type=int),
         request.form.get('sort_order', 0, type=int))
    )
    conn.commit(); conn.close()
    flash(_L[_lang()]['saved'])
    return redirect(url_for('admin.regions_list'))


@admin_bp.route('/regions/<int:rid>/edit', methods=['GET', 'POST'])
@require_admin
def region_edit(rid):
    conn = db.get_db()
    item = conn.execute("SELECT * FROM regions WHERE id=?", (rid,)).fetchone()
    if not item:
        conn.close(); return redirect(url_for('admin.regions_list'))
    if request.method == 'POST':
        name      = request.form.get('name', '')
        city      = request.form.get('city', '')
        president = request.form.get('president', '')
        en = auto_fill_en(
            {'name': name, 'city': city, 'president': president},
            {'name': request.form.get('name_en', ''),
             'city': request.form.get('city_en', ''),
             'president': request.form.get('president_en', '')}
        )
        conn.execute(
            "UPDATE regions SET name=?,name_en=?,city=?,city_en=?,president=?,president_en=?,contact_email=?,athletes_count=?,sort_order=? WHERE id=?",
            (name, en.get('name', ''), city, en.get('city', ''),
             president, en.get('president', ''),
             request.form.get('contact_email', ''),
             request.form.get('athletes_count', 0, type=int),
             request.form.get('sort_order', 0, type=int),
             rid)
        )
        conn.commit(); conn.close()
        flash(_L[_lang()]['saved'])
        return redirect(url_for('admin.regions_list'))
    conn.close()
    return render_template('admin/regions.html',
                           items=db.get_regions(), edit_item=item)


@admin_bp.route('/regions/<int:rid>/delete', methods=['POST'])
@require_admin
def region_delete(rid):
    conn = db.get_db()
    conn.execute("DELETE FROM regions WHERE id=?", (rid,))
    conn.commit(); conn.close()
    flash(_L[_lang()]['deleted'])
    return redirect(url_for('admin.regions_list'))
