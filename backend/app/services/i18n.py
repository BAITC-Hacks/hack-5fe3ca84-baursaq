"""Templates for deterministic explanations in the employee's language (kk / ru / en)."""

T: dict[str, dict[str, str]] = {
    "gap": {
        "ru": "{skill}: {before}→{after} (для {grade} нужно {req})",
        "kk": "{skill}: {before}→{after} ({grade} үшін {req} қажет)",
        "en": "{skill}: {before}→{after} ({req} needed for {grade})",
    },
    "critical": {
        "ru": "{skill} — критичный навык для {grade}",
        "kk": "{skill} — {grade} үшін шешуші дағды",
        "en": "{skill} is critical for {grade}",
    },
    "catchup": {
        "ru": "{skill} ниже требования текущего грейда ({eff} < {req})",
        "kk": "{skill} қазіргі грейд талабынан төмен ({eff} < {req})",
        "en": "{skill} is below your current grade requirement ({eff} < {req})",
    },
    "growth": {
        "ru": "Рост {skill} сверх требований",
        "kk": "{skill} талаптан жоғары өседі",
        "en": "{skill} growth beyond requirements",
    },
    "goal": {
        "ru": "Ведёт к цели: {role} {grade}",
        "kk": "Мақсатқа жетелейді: {role} {grade}",
        "en": "Leads to your goal: {role} {grade}",
    },
    "neg_same": {
        "ru": "Это мероприятие ранее срывалось {n}×",
        "kk": "Бұл іс-шара бұрын {n} рет үзілді",
        "en": "This activity fell through {n}× before",
    },
    "neg_similar": {
        "ru": "Похожие активности ({skill}) срывались {n}×",
        "kk": "Ұқсас белсенділіктер ({skill}) {n} рет үзілді",
        "en": "Similar activities ({skill}) fell through {n}×",
    },
    "neg_format": {
        "ru": "Формат «{format}»: {n} из {total} срывов",
        "kk": "«{format}» форматы: {total} ішінен {n} үзіліс",
        "en": "{format} format: {n} of {total} fell through",
    },
    "pos_type": {
        "ru": "Уже завершено {n} активностей типа «{type}»",
        "kk": "«{type}» түріндегі {n} белсенділік аяқталған",
        "en": "{n} {type} activities already completed",
    },
    "pos_feedback": {
        "ru": "Средняя ваша оценка «{type}»: {avg}/5",
        "kk": "«{type}» бойынша орташа бағаңыз: {avg}/5",
        "en": "Your average rating for {type}: {avg}/5",
    },
    "motivation": {
        "ru": "Вы сами выбирали развитие навыка {skill}",
        "kk": "{skill} дағдысын дамытуды өзіңіз таңдадыңыз",
        "en": "You chose to develop {skill} yourself",
    },
    "clean": {
        "ru": "Срывов по теме не было · завершено добровольных: {done}",
        "kk": "Бұл тақырыпта үзіліс болмаған · аяқталған ерікті: {done}",
        "en": "No failed attempts on this topic · voluntary completed: {done}",
    },
    "in_progress": {
        "ru": "Уже начато: {pct}%",
        "kk": "Басталған: {pct}%",
        "en": "Already started: {pct}%",
    },
    "session": {
        "ru": "Ближайшая сессия {date}",
        "kk": "Жақын сессия {date}",
        "en": "Next session {date}",
    },
    "self_paced": {
        "ru": "В своём темпе — можно начать сразу",
        "kk": "Өз қарқыныңызбен — бірден бастауға болады",
        "en": "Self-paced — start any time",
    },
    "remote_offline": {
        "ru": "Офлайн-формат при удалённой работе",
        "kk": "Қашықтан жұмыс істейсіз, ал формат — офлайн",
        "en": "Offline format while you work remotely",
    },
    "long": {
        "ru": "Большая нагрузка: {hours} ч",
        "kk": "Үлкен жүктеме: {hours} сағ",
        "en": "Heavy workload: {hours} h",
    },
    "unlocked": {
        "ru": "Откроется после шага {n} (пререквизиты)",
        "kk": "{n}-қадамнан кейін ашылады (алғышарттар)",
        "en": "Unlocked after step {n} (prerequisites)",
    },
    # --- rationale sentences (fallback, when no LLM) ---
    "r_gap": {
        "ru": "Закрывает разрыв к цели {role} {grade}: {items}.",
        "kk": "{role} {grade} мақсатына дейінгі алшақтықты жабады: {items}.",
        "en": "Closes the gap to {role} {grade}: {items}.",
    },
    "r_critical": {
        "ru": "{skill} — критичный навык для повышения, поэтому шаг в приоритете.",
        "kk": "{skill} — жоғарылау үшін шешуші дағды, сондықтан бұл қадам басым.",
        "en": "{skill} is critical for promotion, so this step comes first.",
    },
    "r_history_pos": {
        "ru": "По истории участия вам подходит этот формат: {detail}.",
        "kk": "Қатысу тарихына қарағанда бұл формат сізге сай: {detail}.",
        "en": "Your participation history fits this format: {detail}.",
    },
    "r_history_neg": {
        "ru": "Учли историю участия ({detail}), но по пользе для цели этот шаг всё равно впереди.",
        "kk": "Қатысу тарихы ескерілді ({detail}), бірақ мақсатқа пайдасы бойынша бұл қадам бәрібір алда.",
        "en": "We accounted for your history ({detail}), but this step still leads on value for your goal.",
    },
    "r_history_clean": {
        "ru": "История участия: {done} активностей завершено, срывов по этой теме нет.",
        "kk": "Қатысу тарихы: {done} белсенділік аяқталды, бұл тақырып бойынша үзіліс жоқ.",
        "en": "Participation history: {done} activities completed, none failed on this topic.",
    },
    "r_when": {
        "ru": "{when}; нагрузка {hours} ч.",
        "kk": "{when}; жүктеме {hours} сағ.",
        "en": "{when}; workload {hours} h.",
    },
    "r_readiness": {
        "ru": "Готовность к {grade}: {before}% → {after}%.",
        "kk": "{grade} грейдіне дайындық: {before}% → {after}%.",
        "en": "Readiness for {grade}: {before}% → {after}%.",
    },
    "summary": {
        "ru": "Цель — {role} {grade}. Готовность {ready}%. Главный разрыв — {skill} ({eff} из {req}){crit}. "
        "Рекомендуемых шагов: {n}, готовность вырастет до {final}%.",
        "kk": "Мақсат — {role} {grade}. Дайындық {ready}%. Басты алшақтық — {skill} ({req} ішінен {eff}){crit}. "
        "Ұсынылған қадамдар: {n}, дайындық {final}%-ға дейін өседі.",
        "en": "Goal: {role} {grade}. Readiness {ready}%. Main gap: {skill} ({eff} of {req}){crit}. "
        "Recommended steps: {n}, readiness grows to {final}%.",
    },
    "summary_crit": {"ru": ", критичный", "kk": ", шешуші", "en": ", critical"},
    "summary_ready": {
        "ru": "Цель — {role} {grade}. Требования выполнены ({ready}%) — обсудите повышение с руководителем.",
        "kk": "Мақсат — {role} {grade}. Талаптар орындалды ({ready}%) — жоғарылауды басшымен талқылаңыз.",
        "en": "Goal: {role} {grade}. Requirements met ({ready}%) — discuss the promotion with your manager.",
    },
    "summary_none": {
        "ru": "Цель — {role} {grade}. Готовность {ready}%. Подходящих активностей сейчас нет — HR видит этот пробел.",
        "kk": "Мақсат — {role} {grade}. Дайындық {ready}%. Қазір лайықты белсенділік жоқ — HR бұл олқылықты көреді.",
        "en": "Goal: {role} {grade}. Readiness {ready}%. No suitable activities right now — HR sees this gap.",
    },
    # --- why not (rejected) ---
    "why_lowest_history": {
        "ru": "Самый низкий навык — {skill} ({eff}), но похожие активности срывались {n}×; сейчас важнее {top}.",
        "kk": "Ең төмен дағды — {skill} ({eff}), бірақ ұқсас белсенділіктер {n} рет үзілді; қазір {top} маңыздырақ.",
        "en": "Your lowest skill is {skill} ({eff}), but similar activities fell through {n}×; {top} matters more now.",
    },
    "why_lowest_priority": {
        "ru": "Самый низкий навык — {skill} ({eff}), но для {grade} приоритетнее {top}.",
        "kk": "Ең төмен дағды — {skill} ({eff}), бірақ {grade} үшін {top} басымырақ.",
        "en": "Your lowest skill is {skill} ({eff}), but {top} has priority for {grade}.",
    },
    "why_prereq": {
        "ru": "Пока недоступно: нужен {skill} ≥ {req} (сейчас {eff}).",
        "kk": "Әзірге қолжетімсіз: {skill} ≥ {req} қажет (қазір {eff}).",
        "en": "Not available yet: needs {skill} ≥ {req} (now {eff}).",
    },
    "why_critical_done": {
        "ru": "{skill} — критичный для {grade} ({eff} из {req}), но подходящие активности уже пройдены ({events}): "
        "дальше — практика на проекте или новая программа от HR.",
        "kk": "{skill} — {grade} үшін шешуші ({req} ішінен {eff}), бірақ лайықты белсенділіктер өтіп қойған ({events}): "
        "енді — жобадағы тәжірибе немесе HR-дың жаңа бағдарламасы.",
        "en": "{skill} is critical for {grade} ({eff} of {req}), but the matching activities are done ({events}): "
        "next is on-the-job practice or a new HR programme.",
    },
    "why_no_events": {
        "ru": "Для навыка {skill} в каталоге нет подходящих мероприятий — сигнал для HR.",
        "kk": "{skill} дағдысы үшін каталогта лайықты іс-шара жоқ — HR үшін белгі.",
        "en": "No suitable catalogue activity for {skill} — a signal for HR.",
    },
    "why_penalty": {
        "ru": "Отложено: {detail}.",
        "kk": "Кейінге қалдырылды: {detail}.",
        "en": "Postponed: {detail}.",
    },
}

FORMATS = {
    "online": {"ru": "онлайн", "kk": "онлайн", "en": "online"},
    "offline": {"ru": "офлайн", "kk": "офлайн", "en": "offline"},
    "self_paced": {"ru": "в своём темпе", "kk": "өз қарқынымен", "en": "self-paced"},
}

TYPES = {
    "course": {"ru": "курс", "kk": "курс", "en": "course"},
    "workshop": {"ru": "воркшоп", "kk": "воркшоп", "en": "workshop"},
    "mentoring": {"ru": "менторинг", "kk": "тәлімгерлік", "en": "mentoring"},
    "certification": {"ru": "сертификация", "kk": "сертификаттау", "en": "certification"},
    "meetup": {"ru": "митап", "kk": "кездесу", "en": "meetup"},
    "compliance": {"ru": "обязательное обучение", "kk": "міндетті оқыту", "en": "compliance"},
    "onboarding": {"ru": "онбординг", "kk": "бейімдеу", "en": "onboarding"},
}


def t(key: str, lang: str, **kw) -> str:
    templates = T[key]
    return templates.get(lang, templates["en"]).format(**kw)


def fmt(value: str, lang: str) -> str:
    return FORMATS.get(value, {}).get(lang, value)


def typ(value: str, lang: str) -> str:
    return TYPES.get(value, {}).get(lang, value)
