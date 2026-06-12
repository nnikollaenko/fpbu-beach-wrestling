import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'wrestling.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def migrate_db():
    """Add new columns / tables to existing DB without breaking data."""
    conn = get_db()
    # New columns on existing tables
    additions = [
        ("news",     "title_en",        "TEXT"),
        ("news",     "content_en",      "TEXT"),
        ("events",   "title_en",        "TEXT"),
        ("events",   "description_en",  "TEXT"),
        ("events",   "location_en",     "TEXT"),
        ("events",   "category_en",     "TEXT"),
        ("events",   "year",            "INTEGER"),
        ("events",   "pdf_regulations", "TEXT"),
        ("events",   "pdf_program",     "TEXT"),
        ("events",   "pdf_protocols",   "TEXT"),
        ("athletes", "achievements_en", "TEXT"),
        ("athletes", "name_en",         "TEXT"),
        ("athletes", "weight_class_en", "TEXT"),
        ("athletes", "region_en",       "TEXT"),
        ("documents",   "title_en",   "TEXT"),
        ("committees",  "phone",      "TEXT"),
        ("committees",  "email",      "TEXT"),
        ("secretariat", "phone",      "TEXT"),
        ("regions",     "city_en",       "TEXT"),
        ("regions",     "president_en",  "TEXT"),
        ("regions",     "contact_phone", "TEXT"),
        ("secretariat", "name_en",       "TEXT"),
        ("leadership",  "name_en",       "TEXT"),
    ]
    for table, col, typ in additions:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
        except Exception:
            pass

    # New tables
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS event_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER NOT NULL,
        label TEXT NOT NULL,
        file_path TEXT,
        sort_order INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS champions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        name_en TEXT,
        year INTEGER NOT NULL,
        competition TEXT NOT NULL,
        competition_en TEXT,
        medal TEXT DEFAULT 'gold',
        age_group TEXT DEFAULT 'Senior',
        weight_class TEXT,
        gender TEXT DEFAULT 'M',
        photo TEXT,
        total_medals TEXT,
        gold_count INTEGER DEFAULT 0,
        silver_count INTEGER DEFAULT 0,
        bronze_count INTEGER DEFAULT 0,
        sort_order INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS leadership (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        role TEXT NOT NULL,
        role_en TEXT,
        bio TEXT,
        bio_en TEXT,
        photo TEXT,
        sort_order INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS committees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        name_en TEXT,
        description TEXT,
        description_en TEXT,
        head_name TEXT,
        sort_order INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS secretariat (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        role TEXT NOT NULL,
        role_en TEXT,
        email TEXT,
        photo TEXT,
        sort_order INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS regions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        name_en TEXT,
        city TEXT,
        president TEXT,
        contact_email TEXT,
        athletes_count INTEGER DEFAULT 0,
        sort_order INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS partners (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        logo TEXT,
        website TEXT,
        category TEXT DEFAULT 'general',
        sort_order INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS history_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        year INTEGER NOT NULL,
        title TEXT NOT NULL,
        title_en TEXT,
        description TEXT,
        description_en TEXT,
        category TEXT DEFAULT 'achievement',
        sort_order INTEGER DEFAULT 0
    );
    """)
    conn.commit()

    # Seed new tables if empty
    cur = conn.cursor()
    if cur.execute("SELECT COUNT(*) FROM champions").fetchone()[0] == 0:
        _seed_champions(cur)
    if cur.execute("SELECT COUNT(*) FROM leadership").fetchone()[0] == 0:
        _seed_leadership(cur)
    if cur.execute("SELECT COUNT(*) FROM committees").fetchone()[0] == 0:
        _seed_committees(cur)
    if cur.execute("SELECT COUNT(*) FROM secretariat").fetchone()[0] == 0:
        _seed_secretariat(cur)
    if cur.execute("SELECT COUNT(*) FROM regions").fetchone()[0] == 0:
        _seed_regions(cur)
    if cur.execute("SELECT COUNT(*) FROM history_items").fetchone()[0] == 0:
        _seed_history(cur)

    # ── Fill EN translations for all seeded data ─────────────────────────────
    # Events
    ev_en = [
        ("Відкритий Кубок Одеси",              "Odesa Open Cup",                      "Odesa",                "Tournament",   "Opening rating start of the season"),
        ("Кубок України з пляжної боротьби",   "Ukrainian Beach Wrestling Cup",        "Odesa",                "Cup",          "The main domestic competition of the season"),
        ("Першість України серед юніорів",     "Ukrainian Junior Championships",       "Kherson",              "Tournament",   "Age groups 15–17 and 18–20 years"),
        ("Чемпіонат Європи з пляжної боротьби","European Beach Wrestling Championship","Rome, Italy",          "International","Official European Championship under UWW auspices"),
        ("Чемпіонат України",                  "Ukrainian Championship",               "Kyiv",                 "Championship", "Main national championship"),
        ("Чемпіонат світу з пляжної боротьби", "World Beach Wrestling Championship",   "Tashkent, Uzbekistan", "International","Main international competition of the year"),
        ("Кубок України — фінал",              "Ukrainian Cup — Final",                "Dnipro",               "Cup",          "Final stage of the Ukrainian Cup"),
        ("Першість України",                   "Ukrainian Championships",              "Kyiv",                 "Championship", "Determining the strongest wrestlers in the country"),
    ]
    for title_uk, title_en, loc_en, cat_en, desc_en in ev_en:
        try:
            conn.execute(
                "UPDATE events SET title_en=?, location_en=?, category_en=?, description_en=? WHERE title=? AND title_en IS NULL",
                (title_en, loc_en, cat_en, desc_en, title_uk)
            )
        except Exception:
            pass

    # Athletes
    ath_en = [
        ("Андрій Гаврилюк",  "Andriy Havryliuk",    "Up to 90 kg",      "Kherson region",   "World Champion 2025, European Champion 2024"),
        ("Іван Мельник",      "Ivan Melnyk",          "Up to 80 kg",      "Kyiv region",      "Ukrainian Champion 2023–2024, World Championship Medalist"),
        ("Олексій Ковальчук", "Oleksiy Kovalchuk",   "Up to 65 kg",      "Odesa region",     "Ukrainian Champion 2024, European Championship Medalist 2023"),
        ("Максим Сидоренко",  "Maksym Sydorenko",    "Over 90 kg",       "Odesa region",     "Ukrainian Champion 2022–2024"),
        ("Олена Кравченко",   "Olena Kravchenko",    "Up to 55 kg (W)",  "Odesa region",     "Ukrainian Champion 2023–2025"),
        ("Наталія Шевченко",  "Nataliia Shevchenko", "Up to 65 kg (W)",  "Mykolaiv region",  "European Championship Silver Medalist 2024, Ukrainian Champion"),
        ("Тетяна Василенко",  "Tetiana Vasylenko",   "Up to 72 kg (W)",  "Kherson region",   "Ukrainian Champion 2024"),
        ("Дмитро Луценко",    "Dmytro Lutsenko",     "Up to 70 kg",      "Kyiv region",      "Ukrainian Youth Champion 2025"),
    ]
    for name_uk, name_en, wc_en, reg_en, ach_en in ath_en:
        try:
            conn.execute(
                "UPDATE athletes SET name_en=?, weight_class_en=?, region_en=?, achievements_en=? WHERE name=? AND name_en IS NULL",
                (name_en, wc_en, reg_en, ach_en, name_uk)
            )
        except Exception:
            pass

    # Champions — names and competitions
    for name_uk, name_en in [
        ("Андрій Гаврилюк",  "Andriy Havryliuk"),
        ("Наталія Шевченко", "Nataliia Shevchenko"),
        ("Іван Мельник",     "Ivan Melnyk"),
        ("Олексій Ковальчук","Oleksiy Kovalchuk"),
        ("Олена Кравченко",  "Olena Kravchenko"),
        ("Тетяна Василенко", "Tetiana Vasylenko"),
    ]:
        try:
            conn.execute("UPDATE champions SET name_en=? WHERE name=? AND name_en IS NULL", (name_en, name_uk))
        except Exception:
            pass
    for comp_uk, comp_en in [
        ("Чемпіонат світу",   "World Championship"),
        ("Чемпіонат Європи",  "European Championship"),
        ("Чемпіонат України", "Ukrainian Championship"),
    ]:
        try:
            conn.execute("UPDATE champions SET competition_en=? WHERE competition=? AND competition_en IS NULL", (comp_en, comp_uk))
        except Exception:
            pass

    # Leadership bio_en
    for name, bio_en in [
        ("Іван Іванченко",    "Founder and President of UBWF since 2015. Master of Sports of International Class, champion of the Soviet Union."),
        ("Петро Коваленко",   "Honored worker of physical culture and sports of Ukraine. Was at the origins of beach wrestling development in Ukraine."),
        ("Олег Василенко",    "Responsible for the development of regional federations and work with athletes."),
        ("Марина Кирієнко",   "Coordinates international activities and interaction with UWW."),
        ("Андрій Бондаренко", "Manages the administrative work of the Federation, responsible for document management and reporting."),
    ]:
        try:
            conn.execute("UPDATE leadership SET bio_en=? WHERE name=? AND bio_en IS NULL", (bio_en, name))
        except Exception:
            pass

    # Committees description_en
    for name_uk, desc_en in [
        ("Тренерська рада",             "Develops methodology for training athletes, approves training programs, reviews issues of coach qualification improvement."),
        ("Суддівський комітет",         "Training of judges, maintaining the register and certification of the UBWF officiating corps."),
        ("Медична комісія",             "Control of medical support for competitions, admission of athletes, interaction with WADA and NADA."),
        ("Антидопінгова комісія",       "Implementation of anti-doping rules, organization of testing, education of athletes and coaches."),
        ("Комісія зі спортивного права","Legal support of the Federation's activities, resolution of sports disputes."),
    ]:
        try:
            conn.execute("UPDATE committees SET description_en=? WHERE name=? AND description_en IS NULL", (desc_en, name_uk))
        except Exception:
            pass

    # Secretariat name_en
    for name_uk, name_en in [
        ("Наталія Поліщук",   "Nataliia Polishchuk"),
        ("Дмитро Мартиненко", "Dmytro Martynenko"),
        ("Анна Романенко",    "Anna Romanenko"),
        ("Олег Кравчук",      "Oleh Kravchuk"),
    ]:
        try:
            conn.execute("UPDATE secretariat SET name_en=? WHERE name=? AND name_en IS NULL", (name_en, name_uk))
        except Exception:
            pass

    # Regions
    for city_uk, city_en, pres_uk, pres_en in [
        ("Одеса",     "Odesa",        "Петро Мороз",     "Petro Moroz"),
        ("Херсон",    "Kherson",      "Іван Степаненко", "Ivan Stepanenko"),
        ("Київ",      "Kyiv",         "Олена Ткаченко",  "Olena Tkachenko"),
        ("Миколаїв",  "Mykolaiv",     "Андрій Харченко", "Andriy Kharchenko"),
        ("Дніпро",    "Dnipro",       "Василь Коломієць","Vasyl Kolomiiets"),
        ("Запоріжжя", "Zaporizhzhia", "Михайло Яценко",  "Mykhailo Yatsenko"),
    ]:
        try:
            conn.execute(
                "UPDATE regions SET city_en=?, president_en=? WHERE city=? AND president=? AND city_en IS NULL",
                (city_en, pres_en, city_uk, pres_uk)
            )
        except Exception:
            pass

    # History
    for year, title_en, desc_en in [
        (2015, "Federation Founded",               "In 2015, the Ukrainian Beach Wrestling Federation was established. First President — Ivan Ivanchenko."),
        (2016, "Joined UWW",                       "UBWF officially became a member of United World Wrestling — the international wrestling federation."),
        (2017, "First Ukrainian Championship",     "The first official Ukrainian Beach Wrestling Championship was held with 8 regional teams."),
        (2018, "First European Championship Medals","Andriy Havryliuk won bronze at the European Junior Championships — the first international medal in UBWF history."),
        (2019, "Expanded to 20 Regions",           "Regional federations were established in 20 Ukrainian regions."),
        (2020, "Online Competition Format",        "Despite the pandemic, UBWF held a series of online tournaments and kept the sport developing."),
        (2021, "First European Championship Gold", "Andriy Havryliuk became Ukraine's first European Champion in beach wrestling history."),
        (2022, "Continuing Through War",           "Even during the full-scale invasion, UBWF continued its work, bringing athletes to international competitions."),
        (2023, "5 International Medals",           "A record season: 5 medals at World and European Championships. Andriy Havryliuk — European Champion for the second consecutive year."),
        (2024, "Best Season in History",           "Over 20 medals at international competitions. Nataliia Shevchenko — silver medalist at the European Championship."),
        (2025, "World Champion!",                  "Andriy Havryliuk became World Champion — the pinnacle of 10 years of the Federation's work."),
    ]:
        try:
            conn.execute(
                "UPDATE history_items SET title_en=?, description_en=? WHERE year=? AND title_en IS NULL",
                (title_en, desc_en, year)
            )
        except Exception:
            pass

    conn.commit()
    conn.close()


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    cur = conn.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS news (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        cover TEXT,
        published_at TEXT NOT NULL,
        is_featured INTEGER DEFAULT 0,
        title_en TEXT,
        content_en TEXT
    );

    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        location TEXT,
        start_date TEXT NOT NULL,
        end_date TEXT,
        category TEXT DEFAULT 'Змагання',
        status TEXT DEFAULT 'upcoming',
        description TEXT,
        title_en TEXT,
        description_en TEXT,
        year INTEGER,
        pdf_regulations TEXT,
        pdf_program TEXT,
        pdf_protocols TEXT
    );

    CREATE TABLE IF NOT EXISTS athletes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        weight_class TEXT,
        birth_year INTEGER,
        region TEXT,
        achievements TEXT,
        achievements_en TEXT,
        photo TEXT,
        is_active INTEGER DEFAULT 1,
        sort_order INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        title_en TEXT,
        filename TEXT NOT NULL,
        category TEXT DEFAULT 'Офіційні документи',
        uploaded_at TEXT NOT NULL,
        file_size TEXT
    );

    CREATE TABLE IF NOT EXISTS gallery (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        caption TEXT,
        filename TEXT NOT NULL,
        album TEXT DEFAULT 'Загальний',
        taken_at TEXT
    );
    CREATE TABLE IF NOT EXISTS gallery_albums (
        name TEXT PRIMARY KEY,
        name_en TEXT
    );
    """)

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS admin_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)

    if cur.execute("SELECT COUNT(*) FROM news").fetchone()[0] == 0:
        _seed_news(cur)
    if cur.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0:
        _seed_events(cur)
    if cur.execute("SELECT COUNT(*) FROM athletes").fetchone()[0] == 0:
        _seed_athletes(cur)
    if cur.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 0:
        _seed_documents(cur)

    # Seed admin user from env vars on first run
    if cur.execute("SELECT COUNT(*) FROM admin_users").fetchone()[0] == 0:
        _seed_admin_users(cur)

    # Migrations: add columns that may be missing in existing DBs
    for col in ['gold_count', 'silver_count', 'bronze_count']:
        try:
            cur.execute(f"ALTER TABLE champions ADD COLUMN {col} INTEGER DEFAULT 0")
        except Exception:
            pass

    conn.commit()
    conn.close()


# ── Seed data ─────────────────────────────────────────────────────────────────

def _seed_news(cur):
    cur.executemany(
        "INSERT INTO news (slug,title,content,cover,published_at,is_featured) VALUES (?,?,?,?,?,?)",
        [
            ("zbirna-ukrainy-zoloto-chempionat-svitu-2025",
             "Збірна України здобула золото на Чемпіонаті світу з пляжної боротьби",
             "<p>Українські борці продемонстрували блискучий виступ на Чемпіонаті світу. Андрій Гаврилюк здобув золото у ваговій категорії до 90 кг, підтвердивши статус найкращого в світі.</p><p>Це перемога не лише спортсмена, а всієї команди — тренерів, лікарів та всіх, хто вірив у цей результат.</p>",
             None, "2025-08-15", 1),
            ("anons-kubok-ukrainy-2025",
             "Анонс: Кубок України з пляжної боротьби 2025",
             "<p>Федерація пляжної боротьби України оголошує про проведення Кубку України. Реєстрація відкрита до 1 липня 2025 року.</p>",
             None, "2025-06-01", 1),
            ("naybilshi-dosiahnennia-2024",
             "Підсумки сезону 2024: понад 20 медалей на міжнародних змаганнях",
             "<p>Завершився сезон 2024. Збірна України здобула понад 20 медалей на міжнародних змаганнях — найкращий результат за всю історію федерації.</p>",
             None, "2024-11-20", 0),
            ("trenirovochni-zbory-2025",
             "Збірна розпочала підготовку до нового сезону",
             "<p>Національна збірна розпочала тренувальні збори в Центрі олімпійської підготовки. Головний тренер визначив ключові цілі на сезон-2025.</p>",
             None, "2025-01-10", 0),
            ("pervynstvo-ukrainy-junory",
             "Першість України серед юніорів: результати",
             "<p>Завершилась Першість України серед юніорів. Змагання зібрали понад 150 учасників з усіх регіонів країни.</p>",
             None, "2025-05-05", 0),
            ("spivpratsia-uww",
             "ФПБУ підписала угоду про співпрацю з UWW",
             "<p>Федерація пляжної боротьби України підписала меморандум з United World Wrestling. Документ відкриває нові можливості для розвитку спорту в Україні.</p>",
             None, "2025-03-22", 0),
        ]
    )


def _seed_events(cur):
    cur.executemany(
        "INSERT INTO events (title,location,start_date,end_date,category,status,description,year) VALUES (?,?,?,?,?,?,?,?)",
        [
            ("Відкритий Кубок Одеси", "Одеса", "2025-06-30", "2025-06-30", "Першість", "upcoming", "Відкритий рейтинговий старт сезону", 2025),
            ("Кубок України з пляжної боротьби", "Одеса", "2025-07-15", "2025-07-17", "Кубок", "upcoming", "Головний внутрішній старт сезону", 2025),
            ("Першість України серед юніорів", "Херсон", "2025-07-25", "2025-07-27", "Першість", "upcoming", "Вікова група 15–17 та 18–20 років", 2025),
            ("Чемпіонат Європи з пляжної боротьби", "Рим, Італія", "2025-08-10", "2025-08-14", "Міжнародні", "upcoming", "Офіційний ЧЄ під егідою UWW", 2025),
            ("Чемпіонат України", "Київ", "2025-09-05", "2025-09-07", "Чемпіонат", "upcoming", "Головний чемпіонат країни", 2025),
            ("Чемпіонат світу з пляжної боротьби", "Ташкент, Узбекистан", "2025-09-20", "2025-09-25", "Міжнародні", "upcoming", "Головний міжнародний старт року", 2025),
            ("Кубок України — фінал", "Дніпро", "2024-09-10", "2024-09-12", "Кубок", "past", "Фінальний етап Кубку України", 2024),
            ("Першість України", "Київ", "2024-08-01", "2024-08-03", "Першість", "past", "Визначення найсильніших борців країни", 2024),
        ]
    )


def _seed_athletes(cur):
    cur.executemany(
        "INSERT INTO athletes (name,weight_class,birth_year,region,achievements,is_active,sort_order) VALUES (?,?,?,?,?,?,?)",
        [
            ("Андрій Гаврилюк", "До 90 кг", 1999, "Херсонська обл.", "Чемпіон світу 2025, Чемпіон Європи 2024", 1, 1),
            ("Іван Мельник", "До 80 кг", 1996, "Київська обл.", "Чемпіон України 2023–2024, Призер ЧС", 1, 2),
            ("Олексій Ковальчук", "До 65 кг", 1998, "Одеська обл.", "Чемпіон України 2024, Призер ЧЄ 2023", 1, 3),
            ("Максим Сидоренко", "Понад 90 кг", 1997, "Одеська обл.", "Чемпіон України 2022–2024", 1, 4),
            ("Олена Кравченко", "До 55 кг (Ж)", 2000, "Одеська обл.", "Чемпіонка України 2023–2025", 1, 5),
            ("Наталія Шевченко", "До 65 кг (Ж)", 1998, "Миколаївська обл.", "Призер ЧЄ 2024, Чемпіонка України", 1, 6),
            ("Тетяна Василенко", "До 72 кг (Ж)", 1997, "Херсонська обл.", "Чемпіонка України 2024", 1, 7),
            ("Дмитро Луценко", "До 70 кг", 2002, "Київська обл.", "Чемпіон України серед молоді 2025", 1, 8),
        ]
    )


def _seed_documents(cur):
    cur.executemany(
        "INSERT INTO documents (title,filename,category,uploaded_at,file_size) VALUES (?,?,?,?,?)",
        [
            ("Статут ФПБУ", "statut-fpbu.pdf", "Офіційні документи", "2024-01-15", "245 КБ"),
            ("Правила змагань UWW 2024", "rules-uww-2024-uk.pdf", "Офіційні документи", "2024-02-01", "1.2 МБ"),
            ("Антидопінгові правила ФПБУ", "antidoping-rules.pdf", "Анти-допінг", "2024-03-20", "95 КБ"),
            ("Кодекс ВАДА 2024 (укр.)", "wada-code-2024-uk.pdf", "Анти-допінг", "2024-01-05", "2.1 МБ"),
            ("Заборонений список ВАДА 2025", "wada-list-2025.pdf", "Анти-допінг", "2025-01-01", "180 КБ"),
        ]
    )


def _seed_champions(cur):
    cur.executemany(
        "INSERT INTO champions (name,year,competition,medal,age_group,weight_class,gender,total_medals,sort_order) VALUES (?,?,?,?,?,?,?,?,?)",
        [
            ("Андрій Гаврилюк", 2025, "Чемпіонат світу", "gold", "Senior", "До 90 кг", "M", "2 золота ЧС, 3 золота ЧЄ", 1),
            ("Андрій Гаврилюк", 2024, "Чемпіонат Європи", "gold", "Senior", "До 90 кг", "M", "2 золота ЧС, 3 золота ЧЄ", 2),
            ("Наталія Шевченко", 2024, "Чемпіонат Європи", "silver", "Senior", "До 65 кг", "F", "1 срібло ЧЄ, 2 золота ЧУ", 3),
            ("Іван Мельник", 2023, "Чемпіонат світу", "bronze", "Senior", "До 80 кг", "M", "1 бронза ЧС, 3 золота ЧУ", 4),
            ("Олексій Ковальчук", 2023, "Чемпіонат Європи", "bronze", "Senior", "До 65 кг", "M", "1 бронза ЧЄ, 2 золота ЧУ", 5),
            ("Андрій Гаврилюк", 2023, "Чемпіонат Європи", "gold", "Senior", "До 90 кг", "M", "2 золота ЧС, 3 золота ЧЄ", 6),
            ("Олена Кравченко", 2024, "Чемпіонат України", "gold", "Senior", "До 55 кг", "F", "3 золота ЧУ", 7),
            ("Тетяна Василенко", 2024, "Чемпіонат України", "gold", "Senior", "До 72 кг", "F", "1 золото ЧУ", 8),
        ]
    )


def _seed_leadership(cur):
    cur.executemany(
        "INSERT INTO leadership (name,role,role_en,bio,sort_order) VALUES (?,?,?,?,?)",
        [
            ("Іван Іванченко", "Президент", "President",
             "Засновник та президент ФПБУ з 2015 року. Майстер спорту міжнародного класу, чемпіон Радянського Союзу.", 1),
            ("Петро Коваленко", "Почесний президент", "Honorary President",
             "Заслужений діяч фізичної культури і спорту України. Стояв у витоків розвитку пляжної боротьби в Україні.", 2),
            ("Олег Василенко", "Перший віце-президент", "First Vice-President",
             "Відповідає за розвиток регіональних федерацій та роботу зі спортсменами.", 3),
            ("Марина Кирієнко", "Віце-президент", "Vice-President",
             "Координує міжнародну діяльність та взаємодію з UWW.", 4),
            ("Андрій Бондаренко", "Генеральний секретар", "General Secretary",
             "Керує адміністративною роботою Федерації, відповідає за документообіг та звітність.", 5),
        ]
    )


def _seed_committees(cur):
    cur.executemany(
        "INSERT INTO committees (name,name_en,description,head_name,sort_order) VALUES (?,?,?,?,?)",
        [
            ("Тренерська рада", "Coaching Council",
             "Формує методику підготовки спортсменів, затверджує навчальні програми, розглядає питання підвищення кваліфікації тренерів.",
             "Василь Дорошенко", 1),
            ("Суддівський комітет", "Referees Committee",
             "Підготовка суддів, ведення реєстру та атестація суддівського корпусу ФПБУ.",
             "Сергій Мороз", 2),
            ("Медична комісія", "Medical Commission",
             "Контроль медичного забезпечення змагань, допуск спортсменів, взаємодія з ВАДА та НАДА.",
             "Олена Сидоренко", 3),
            ("Антидопінгова комісія", "Anti-Doping Commission",
             "Впровадження антидопінгових правил, організація тестування, освіта спортсменів та тренерів.",
             "Микола Луценко", 4),
            ("Комісія зі спортивного права", "Sports Law Commission",
             "Правове супроводження діяльності Федерації, вирішення спортивних спорів.",
             "Тетяна Гончар", 5),
        ]
    )


def _seed_secretariat(cur):
    cur.executemany(
        "INSERT INTO secretariat (name,role,role_en,email,sort_order) VALUES (?,?,?,?,?)",
        [
            ("Наталія Поліщук", "Виконавчий директор", "Executive Director", "n.polishchuk@ubwf.com.ua", 1),
            ("Дмитро Мартиненко", "Фінансовий менеджер", "Finance Manager", "d.martynenko@ubwf.com.ua", 2),
            ("Анна Романенко", "Прес-секретар", "Press Secretary", "pr@ubwf.com.ua", 3),
            ("Олег Кравчук", "Менеджер зі спортивних заходів", "Events Manager", "events@ubwf.com.ua", 4),
        ]
    )


def _seed_regions(cur):
    cur.executemany(
        "INSERT INTO regions (name,name_en,city,president,athletes_count,sort_order) VALUES (?,?,?,?,?,?)",
        [
            ("Одеська обласна федерація", "Odesa Regional Federation", "Одеса", "Петро Мороз", 85, 1),
            ("Херсонська обласна федерація", "Kherson Regional Federation", "Херсон", "Іван Степаненко", 62, 2),
            ("Київська обласна федерація", "Kyiv Regional Federation", "Київ", "Олена Ткаченко", 75, 3),
            ("Миколаївська обласна федерація", "Mykolaiv Regional Federation", "Миколаїв", "Андрій Харченко", 48, 4),
            ("Дніпропетровська обласна федерація", "Dnipropetrovsk Regional Federation", "Дніпро", "Василь Коломієць", 55, 5),
            ("Запорізька обласна федерація", "Zaporizhzhia Regional Federation", "Запоріжжя", "Михайло Яценко", 40, 6),
        ]
    )


def _seed_history(cur):
    cur.executemany(
        "INSERT INTO history_items (year,title,description,category,sort_order) VALUES (?,?,?,?,?)",
        [
            (2015, "Заснування Федерації", "У 2015 році була заснована Федерація пляжної боротьби України. Перший президент — Іван Іванченко.", "milestone", 1),
            (2016, "Вступ до UWW", "ФПБУ офіційно стала членом United World Wrestling — міжнародної федерації боротьби.", "milestone", 1),
            (2017, "Перша Першість України", "Проведено першу офіційну Першість України з пляжної боротьби за участю 8 регіонів.", "event", 1),
            (2018, "Перші медалі Чемпіонату Європи", "Андрій Гаврилюк здобув бронзу на ЧЄ серед юніорів — перша міжнародна медаль в історії ФПБУ.", "achievement", 1),
            (2019, "Розширення до 20 регіонів", "Обласні федерації створено в 20 регіонах України.", "milestone", 1),
            (2020, "Онлайн-формат змагань", "Попри пандемію, ФПБУ провела серію онлайн-турнірів і не зупинила розвиток спорту.", "event", 1),
            (2021, "Перше золото Чемпіонату Європи", "Андрій Гаврилюк став першим чемпіоном Європи в історії України.", "achievement", 1),
            (2022, "Продовження попри війну", "Навіть під час повномасштабного вторгнення ФПБУ продовжувала роботу, вивозячи спортсменів на міжнародні змагання.", "milestone", 1),
            (2023, "5 медалей на міжнародній арені", "Рекордний сезон: 5 медалей ЧС та ЧЄ. Андрій Гаврилюк — чемпіон Європи вдруге поспіль.", "achievement", 1),
            (2024, "Найкращий сезон в історії", "Понад 20 медалей на міжнародних змаганнях. Наталія Шевченко — срібний призер Чемпіонату Європи.", "achievement", 1),
            (2025, "Чемпіон світу!", "Андрій Гаврилюк став чемпіоном світу — вершина 10 років роботи Федерації.", "achievement", 1),
        ]
    )


# ── Queries ───────────────────────────────────────────────────────────────────

def get_news(limit=None, featured_only=False, exclude_id=None):
    conn = get_db()
    q, params = "SELECT * FROM news", []
    conds = []
    if featured_only: conds.append("is_featured = 1")
    if exclude_id:    conds.append("id != ?"); params.append(exclude_id)
    if conds: q += " WHERE " + " AND ".join(conds)
    q += " ORDER BY published_at DESC"
    if limit: q += f" LIMIT {int(limit)}"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return rows


def get_news_paginated(page=1, per_page=12):
    conn = get_db()
    offset = (page - 1) * per_page
    total = conn.execute("SELECT COUNT(*) FROM news").fetchone()[0]
    rows  = conn.execute("SELECT * FROM news ORDER BY published_at DESC LIMIT ? OFFSET ?", (per_page, offset)).fetchall()
    conn.close()
    return rows, total


def get_news_by_slug(slug):
    conn = get_db()
    row = conn.execute("SELECT * FROM news WHERE slug = ?", (slug,)).fetchone()
    conn.close()
    return row


def get_upcoming_events(limit=5):
    conn = get_db()
    today = datetime.today().strftime('%Y-%m-%d')
    rows  = conn.execute("SELECT * FROM events WHERE start_date >= ? ORDER BY start_date LIMIT ?", (today, limit)).fetchall()
    conn.close()
    return rows


def get_events_by_year(year):
    conn = get_db()
    rows = conn.execute("SELECT * FROM events WHERE year = ? OR strftime('%Y', start_date) = ? ORDER BY start_date", (year, str(year))).fetchall()
    conn.close()
    return rows


def get_events_by_year_paginated(year, page=1, per_page=10, category=None):
    conn = get_db()
    base = "WHERE (year = ? OR strftime('%Y', start_date) = ?)"
    params = [year, str(year)]
    if category:
        base += " AND category = ?"
        params.append(category)
    total = conn.execute(f"SELECT COUNT(*) FROM events {base}", params).fetchone()[0]
    offset = (page - 1) * per_page
    rows = conn.execute(
        f"SELECT * FROM events {base} ORDER BY start_date LIMIT ? OFFSET ?",
        params + [per_page, offset]
    ).fetchall()
    conn.close()
    return rows, total


def get_all_events():
    conn = get_db()
    rows = conn.execute("SELECT * FROM events ORDER BY start_date DESC").fetchall()
    conn.close()
    return rows


def get_extra_docs_for_events(event_ids):
    """Return {event_id: [row, ...]} for a list of event IDs."""
    if not event_ids:
        return {}
    conn = get_db()
    placeholders = ','.join('?' * len(event_ids))
    rows = conn.execute(
        f"SELECT * FROM event_documents WHERE event_id IN ({placeholders}) ORDER BY event_id, sort_order",
        list(event_ids)
    ).fetchall()
    conn.close()
    result = {}
    for row in rows:
        result.setdefault(row['event_id'], []).append(row)
    return result


def get_extra_docs_for_event(event_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM event_documents WHERE event_id=? ORDER BY sort_order", (event_id,)
    ).fetchall()
    conn.close()
    return rows


def get_calendar_years():
    conn = get_db()
    rows = conn.execute("SELECT DISTINCT COALESCE(year, CAST(strftime('%Y', start_date) AS INTEGER)) AS y FROM events ORDER BY y DESC").fetchall()
    conn.close()
    return [r['y'] for r in rows if r['y']]


def get_athletes():
    conn = get_db()
    rows = conn.execute("SELECT * FROM athletes WHERE is_active = 1 ORDER BY sort_order, name").fetchall()
    conn.close()
    return rows


def get_champions(year=None, gender=None, age_group=None):
    conn = get_db()
    q, params = "SELECT * FROM champions", []
    conds = []
    if year:      conds.append("year = ?");       params.append(year)
    if gender:    conds.append("gender = ?");     params.append(gender)
    if age_group: conds.append("age_group = ?");  params.append(age_group)
    if conds: q += " WHERE " + " AND ".join(conds)
    q += " ORDER BY CASE WHEN sort_order = 0 THEN 1 ELSE 0 END, sort_order, id DESC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return rows


def get_champion_years():
    conn = get_db()
    rows = conn.execute("SELECT DISTINCT year FROM champions ORDER BY year DESC").fetchall()
    conn.close()
    return [r['year'] for r in rows]


def get_leadership():
    conn = get_db()
    rows = conn.execute("SELECT * FROM leadership ORDER BY sort_order").fetchall()
    conn.close()
    return rows


def get_committees():
    conn = get_db()
    rows = conn.execute("SELECT * FROM committees ORDER BY sort_order").fetchall()
    conn.close()
    return rows


def get_secretariat():
    conn = get_db()
    rows = conn.execute("SELECT * FROM secretariat ORDER BY sort_order").fetchall()
    conn.close()
    return rows


def get_regions():
    conn = get_db()
    rows = conn.execute("SELECT * FROM regions ORDER BY sort_order, name").fetchall()
    conn.close()
    return rows


def get_partners():
    conn = get_db()
    rows = conn.execute("SELECT * FROM partners ORDER BY sort_order").fetchall()
    conn.close()
    return rows


def get_history():
    conn = get_db()
    rows = conn.execute("SELECT * FROM history_items ORDER BY year DESC, sort_order").fetchall()
    conn.close()
    return rows


def get_documents(category=None):
    conn = get_db()
    if category:
        rows = conn.execute("SELECT * FROM documents WHERE category = ? ORDER BY uploaded_at DESC", (category,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM documents ORDER BY category, uploaded_at DESC").fetchall()
    conn.close()
    return rows


def get_gallery(album=None):
    conn = get_db()
    if album:
        rows = conn.execute("SELECT * FROM gallery WHERE album = ? ORDER BY taken_at DESC", (album,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM gallery ORDER BY taken_at DESC").fetchall()
    conn.close()
    return rows


def _seed_admin_users(cur):
    """Seed admin users from ADMIN_USERS env var (format: user1:pass1,user2:pass2)."""
    raw = os.environ.get('ADMIN_USERS', '')
    pairs = []
    if raw:
        for item in raw.split(','):
            item = item.strip()
            if ':' in item:
                u, p = item.split(':', 1)
                pairs.append((u.strip(), p.strip()))
    if not pairs:
        # Default dev credentials — override ADMIN_USERS in production
        pairs = [('admin', 'admin')]
    now = datetime.now().isoformat()
    for username, password in pairs:
        cur.execute(
            "INSERT OR IGNORE INTO admin_users (username, password_hash, created_at) VALUES (?, ?, ?)",
            (username, generate_password_hash(password, method='pbkdf2:sha256'), now)
        )


def get_admin_by_username(username):
    conn = get_db()
    row = conn.execute("SELECT * FROM admin_users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return row


def verify_admin(username, password):
    user = get_admin_by_username(username)
    if user and check_password_hash(user['password_hash'], password):
        return user
    return None


def list_admin_users():
    conn = get_db()
    rows = conn.execute("SELECT id, username, created_at FROM admin_users ORDER BY id").fetchall()
    conn.close()
    return rows


def get_albums():
    conn = get_db()
    rows = conn.execute("SELECT DISTINCT album FROM gallery ORDER BY album").fetchall()
    conn.close()
    return [r['album'] for r in rows]


def get_album_info(sort='date'):
    """Returns list of dicts: album name, name_en, cover filename, photo count, event_date."""
    conn = get_db()
    order = "MAX(g.taken_at) DESC, g.album ASC" if sort != 'alpha' else "g.album ASC"
    rows = conn.execute(f"""
        SELECT g.album,
               ga.name_en,
               MIN(g.filename) AS cover,
               COUNT(*) AS cnt,
               MAX(g.taken_at) AS event_date
          FROM gallery g
          LEFT JOIN gallery_albums ga ON ga.name = g.album
         GROUP BY g.album
         ORDER BY {order}
    """).fetchall()
    conn.close()
    return [{'name': r['album'], 'name_en': r['name_en'] or '', 'cover': r['cover'], 'count': r['cnt'], 'event_date': r['event_date']} for r in rows]
