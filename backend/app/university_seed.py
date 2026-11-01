# -*- coding: utf-8 -*-
"""
Начальное наполнение: факультеты, демо-карточки и демо-аккаунты.

Идемпотентно и безопасно для существующей базы:
  * демо-пользователи создаются только в пустой базе (и не в production без
    SEED_DEMO_USERS=true);
  * факультеты и демо-карточки создаются, только пока в базе нет ни одного факультета;
  * в production первого суперадмина можно создать переменными SUPERUSER_USERNAME,
    SUPERUSER_EMAIL, SUPERUSER_PASSWORD (если суперадмина ещё нет).

Пароли демо-аккаунтов берутся из окружения (см. .env.example).
"""
import html
import os
from datetime import datetime

from sqlalchemy.orm import Session

from . import models
from .auth import get_password_hash
from .sanitize import sanitize_html
from .taxonomy import normalize_tags

# «or»: docker-compose передаёт незаданные переменные как пустые строки
SEED_ADMIN_PASSWORD = os.getenv("SEED_ADMIN_PASSWORD") or "Sup3r-Adm1n!mp2026"
SEED_USER_PASSWORD = os.getenv("SEED_USER_PASSWORD") or "Dem0-Us3r!mp2026"

FACULTIES = [
    ("Факультет кибернетики", "ФК", "Искусственный интеллект, робототехника и системы управления."),
    ("Факультет биотехнологий", "ФБТ", "Биосенсоры, клеточные технологии и пищевая биотехнология."),
    ("Факультет энергетики", "ФЭ", "Возобновляемая энергетика, накопители и умные сети."),
    ("Факультет материаловедения и машиностроения", "ФММ", "Новые материалы, аддитивные технологии и конструкции."),
    ("Факультет информационных технологий", "ФИТ", "Анализ данных, медицинская информатика и цифровые двойники."),
]

# (индекс факультета, название, краткое описание, описание, теги, готовность, статус, контакт)
CARDS = [
    (0, "Система компьютерного зрения для распознавания объектов",
     "Нейросетевое распознавание и отслеживание объектов на видео в реальном времени на встраиваемых платформах.",
     ["Система обнаруживает и классифицирует объекты в видеопотоке, определяет их положение и траекторию. "
      "Работает на компактных вычислителях без облака, поэтому подходит для роботов, дронов и промышленных линий.",
      "Разработана на кафедре технической кибернетики; есть рабочий пилот на складе."],
     ["компьютерное зрение", "нейронные сети", "распознавание образов"], "pilot", "published",
     ("Иван Петров", "i.petrov@example.edu")),
    (0, "Автономная мобильная платформа для складов",
     "Беспилотная тележка с навигацией по лидару для перевозки грузов внутри склада без разметки.",
     ["Платформа строит карту помещения, объезжает препятствия и самостоятельно доставляет грузы между зонами. "
      "Грузоподъёмность до 300 кг, управление через веб-интерфейс."],
     ["робототехника", "навигация", "лидар", "склад"], "prototype", "published",
     ("Мария Соколова", "m.sokolova@example.edu")),
    (0, "Предиктивная аналитика состояния оборудования",
     "Модель предсказывает отказ станков по вибрации и току за недели до поломки.",
     ["Датчики вибрации и тока передают данные в модель машинного обучения, которая оценивает остаточный ресурс узлов. "
      "Снижает внеплановые простои и стоимость ремонта."],
     ["машинное обучение", "аналитика данных", "промышленность", "датчики"], "pilot", "published",
     ("Алексей Иванов", "a.ivanov@example.edu")),
    (1, "Биосенсор для экспресс-анализа качества воды",
     "Портативный датчик определяет токсичные загрязнения в воде за несколько минут.",
     ["Биосенсор на основе модифицированных ферментов реагирует на тяжёлые металлы и пестициды. "
      "Подходит для полевых измерений на водоёмах и очистных сооружениях."],
     ["биосенсоры", "экология", "анализ воды"], "prototype", "published",
     ("Анна Смирнова", "a.smirnova@example.edu")),
    (1, "Штамм дрожжей для производства кормового белка",
     "Дрожжи на побочных продуктах пищевых производств дают дешёвый белок для кормов.",
     ["Штамм растёт на отходах переработки зерна и накапливает до 50% белка. "
      "Технология готова к масштабированию на опытном производстве."],
     ["биотехнологии", "пищевая промышленность", "белок"], "ready", "published",
     ("Анна Смирнова", "a.smirnova@example.edu")),
    (2, "Умная система управления солнечной электростанцией",
     "Алгоритмы прогноза выработки и управления накопителем повышают отдачу солнечных станций.",
     ["Система прогнозирует выработку по погодным данным и распределяет энергию между сетью, накопителем и потребителями. "
      "Внедрена на опытной станции вуза."],
     ["возобновляемая энергетика", "умные сети", "управление"], "pilot", "published",
     ("Сергей Орлов", "s.orlov@example.edu")),
    (2, "Накопитель энергии на новых электродных материалах",
     "Аккумулятор с повышенной ёмкостью и числом циклов за счёт нового электродного материала.",
     ["Лабораторные образцы выдерживают более 3000 циклов с потерей ёмкости менее 10%. "
      "Ведётся подготовка пилотной партии."],
     ["аккумуляторы", "накопитель энергии", "материалы"], "prototype", "published",
     ("Сергей Орлов", "s.orlov@example.edu")),
    (3, "Композитные материалы для лёгких конструкций",
     "Углепластики с заданными свойствами для авиастроения и транспорта.",
     ["Разработаны составы и режимы формования, дающие снижение массы деталей на 30-40% при сохранении прочности. "
      "Есть опыт изготовления деталей по заказу предприятий."],
     ["композиты", "авиастроение", "материалы"], "ready", "published",
     ("Ольга Кузнецова", "o.kuznetsova@example.edu")),
    (3, "3D-печать металлических деталей",
     "Аддитивное производство сложных металлических деталей по цифровой модели.",
     ["Технология селективного лазерного сплавления позволяет изготавливать детали сложной формы без оснастки. "
      "Принимаем заказы на опытные партии."],
     ["аддитивные технологии", "материалы", "производство"], "pilot", "published",
     ("Ольга Кузнецова", "o.kuznetsova@example.edu")),
    (4, "Система поддержки врача по медицинским снимкам",
     "Нейросеть выделяет подозрительные области на снимках и помогает врачу принять решение.",
     ["Модель анализирует рентгенограммы и КТ, подсвечивает области, требующие внимания, и оценивает уверенность. "
      "Не заменяет врача, а ускоряет первичный просмотр."],
     ["медицина", "компьютерное зрение", "нейронные сети", "анализ изображений"], "prototype", "published",
     ("Дмитрий Волков", "d.volkov@example.edu")),
    (4, "Платформа цифровых двойников производства",
     "Моделирование производственной линии для поиска узких мест до внедрения изменений.",
     ["Цифровой двойник воспроизводит работу линии и позволяет проверить сценарии без остановки производства. "
      "Находится на стадии концепции."],
     ["цифровой двойник", "моделирование", "производство"], "idea", "draft",
     ("Дмитрий Волков", "d.volkov@example.edu")),
]


def _description_html(paragraphs) -> str:
    return sanitize_html("".join(f"<p>{html.escape(p)}</p>" for p in paragraphs))


def _is_production_without_demo() -> bool:
    return os.getenv("ENV", "development") == "production" and os.getenv("SEED_DEMO_USERS") != "true"


def _bootstrap_superuser(db: Session) -> None:
    """Первый суперадмин для production: из переменных окружения, только если суперадмина нет."""
    username = os.getenv("SUPERUSER_USERNAME")
    email = os.getenv("SUPERUSER_EMAIL")
    password = os.getenv("SUPERUSER_PASSWORD")
    if not (username and email and password):
        return
    if db.query(models.User).filter(models.User.role == "superuser").first():
        return
    db.add(models.User(
        username=username, email=email, hashed_password=get_password_hash(password),
        full_name="Суперадмин", role="superuser",
    ))
    db.commit()
    print(f"🔑 [seed] Создан суперадмин «{username}» из переменных окружения")


def _seed_demo_users(db: Session, faculties: list) -> None:
    users = [
        ("superuser", "super@example.com", SEED_ADMIN_PASSWORD, "Суперадмин вуза", "superuser", None),
        ("admin_cyber", "admin.cyber@example.com", SEED_ADMIN_PASSWORD, "Администратор факультета кибернетики", "admin", faculties[0].id),
        ("admin_bio", "admin.bio@example.com", SEED_ADMIN_PASSWORD, "Администратор факультета биотехнологий", "admin", faculties[1].id),
        ("anna", "anna@example.com", SEED_USER_PASSWORD, "Анна Смирнова", "user", None),
    ]
    for username, email, password, full_name, role, faculty_id in users:
        db.add(models.User(
            username=username, email=email, hashed_password=get_password_hash(password),
            full_name=full_name, role=role, faculty_id=faculty_id,
        ))
    db.commit()


def _seed_faculties_and_cards(db: Session, author_id) -> list:
    faculties = [models.Faculty(name=n, short_name=s, description=d) for n, s, d in FACULTIES]
    db.add_all(faculties)
    db.flush()

    tags = {}
    now = datetime.utcnow()
    for faculty_index, title, summary, paragraphs, tag_names, readiness, status, contact in CARDS:
        card = models.Card(
            faculty_id=faculties[faculty_index].id,
            title=title,
            summary=summary,
            description=_description_html(paragraphs),
            status=status,
            readiness=readiness,
            gallery=[],
            contact_name=contact[0],
            contact_email=contact[1],
            author_id=author_id,
            published_at=now if status == "published" else None,
        )
        card_tags = []
        for name in normalize_tags(tag_names):
            if name not in tags:
                tags[name] = models.Tag(name=name)
                db.add(tags[name])
            card_tags.append(tags[name])
        card.tags = card_tags
        db.add(card)
    db.commit()
    return faculties


def run(db: Session) -> None:
    _bootstrap_superuser(db)

    users_empty = db.query(models.User).count() == 0
    no_faculties = db.query(models.Faculty).count() == 0

    if _is_production_without_demo():
        if users_empty or no_faculties:
            print("⚠️  [seed] production: демо-данные не создаются (SEED_DEMO_USERS != true)")
        return

    if not (users_empty or no_faculties):
        return  # уже инициализировано

    print("🌱 [seed] Создаю факультеты, демо-карточки и демо-аккаунты…")
    if no_faculties:
        # Автор карточек — суперадмин, если он уже есть (база с прежними пользователями)
        existing_super = db.query(models.User).filter(models.User.role == "superuser").first()
        faculties = _seed_faculties_and_cards(db, existing_super.id if existing_super else None)
    else:
        faculties = db.query(models.Faculty).order_by(models.Faculty.id).all()

    if users_empty and len(faculties) >= 2:
        _seed_demo_users(db, faculties)
        # Карточки без автора передаём суперадмину, чтобы у них был владелец
        owner = db.query(models.User).filter(models.User.username == "superuser").first()
        if owner:
            db.query(models.Card).filter(models.Card.author_id.is_(None)).update({"author_id": owner.id})
            db.commit()

    print(f"✅ [seed] Готово: факультетов {db.query(models.Faculty).count()}, "
          f"карточек {db.query(models.Card).count()}, пользователей {db.query(models.User).count()}")
