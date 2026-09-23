import { createContext, createElement, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'

export type Language = 'ru' | 'kk' | 'en'
export const locales: Record<Language, string> = { ru: 'ru-RU', kk: 'kk-KZ', en: 'en-GB' }
export const LANGUAGE_STORAGE_KEY = 'career-quest.language'
export type PluralForms = Partial<Record<Intl.LDMLPluralRule, string>> & { other: string }
type Message = string | PluralForms
type Params = Record<string, string | number>

// Each row is [ru, kk, en]. Keep dataset names and server-generated explanations unchanged.
// Russian copy follows submission; count forms fix the original invariant «факторов»/«записей».
const messages = {
  'app.name': ['Career Quest', 'Career Quest', 'Career Quest'],
  'app.tagline': ['Ваш путь к следующему уровню', 'Келесі деңгейге бастайтын жолыңыз', 'Your path to the next level'],
  'app.role.label': ['Роль', 'Рөл', 'Role'],
  'app.role.employee': ['Сотрудник', 'Қызметкер', 'Employee'],
  'app.role.hr': ['HR обзор', 'HR шолуы', 'HR overview'],
  'app.search.label': ['Найти сотрудника', 'Қызметкерді іздеу', 'Find an employee'],
  'app.search.placeholder': ['Найти сотрудника…', 'Қызметкерді іздеу…', 'Find an employee…'],
  'app.search.loading': ['Ищем сотрудников…', 'Қызметкерлер ізделуде…', 'Searching for employees…'],
  'app.search.error': ['Не удалось загрузить список сотрудников.', 'Қызметкерлер тізімін жүктеу мүмкін болмады.', 'Could not load the employee list.'],
  'app.search.retry': ['Повторить поиск', 'Қайта іздеу', 'Search again'],
  'app.search.empty': ['Сотрудники не найдены', 'Қызметкерлер табылмады', 'No employees found'],
  'app.language.label': ['Язык', 'Тіл', 'Language'],
  'app.language.hint': ['Язык интерфейса и ответа ИИ', 'Интерфейс пен ЖИ жауабының тілі', 'Interface and AI response language'],
  // Legacy switch copy is inventoried for stage 1; use label/hint above during stage 2.
  'app.language.aiLabel': ['Язык ответа ИИ', 'ЖИ жауабының тілі', 'AI response language'],
  'app.language.aiHint': ['Язык объяснений ИИ. Интерфейс — на русском.', 'ЖИ түсіндірмелерінің тілі. Интерфейс орыс тілінде.', 'AI explanation language. The interface is in Russian.'],
  'app.language.aiRu': ['ИИ: RU', 'ЖИ: RU', 'AI: RU'],
  'app.language.aiKk': ['ИИ: KK', 'ЖИ: KK', 'AI: KK'],
  'app.language.aiEn': ['ИИ: EN', 'ЖИ: EN', 'AI: EN'],
  'app.language.ru': ['Русский', 'Орысша', 'Russian'],
  'app.language.kk': ['Қазақша', 'Қазақша', 'Қазақша'],
  'app.language.en': ['English', 'English', 'English'],
  'app.hr.loading': ['Загружаем HR-обзор…', 'HR шолуы жүктелуде…', 'Loading HR overview…'],
  'app.footer': ['Career Quest · Halyk Bank · Данные демонстрационные', 'Career Quest · Halyk Bank · Демо деректер', 'Career Quest · Halyk Bank · Demo data'],
  'common.retry': ['Повторить', 'Қайталау', 'Try again'],
  'common.close': ['Закрыть', 'Жабу', 'Close'],
  'common.skill': ['Навык', 'Дағды', 'Skill'],
  'common.activity': ['Активность', 'Белсенділік', 'Activity'],
  'common.date.unknown': ['Дата не указана', 'Күні көрсетілмеген', 'Date not specified'],
  'common.duration.hours': ['{count} ч', '{count} сағ', '{count} h'],
  'common.duration.milliseconds': ['{count} мс', '{count} мс', '{count} ms'],
  'common.format.self_paced': ['В своём темпе', 'Өз қарқыныңызбен', 'Self-paced'],
  'common.format.online': ['Онлайн', 'Онлайн', 'Online'],
  'common.format.offline': ['Офлайн', 'Офлайн', 'In person'],
  'common.work.remote': ['Удалённо', 'Қашықтан', 'Remote'],
  'common.work.hybrid': ['Гибридно', 'Аралас форматта', 'Hybrid'],
  'common.work.office': ['В офисе', 'Кеңседе', 'In the office'],
  'history.status.completed': ['Пройдено', 'Аяқталды', 'Completed'],
  'history.status.no_show': ['Не пришёл', 'Қатыспады', 'Did not attend'],
  'history.status.declined': ['Отказ', 'Бас тартты', 'Declined'],
  'history.status.dropped': ['Прервано', 'Аяқтамай тоқтатты', 'Dropped out'],
  'history.status.overdue': ['Просрочено', 'Мерзімі өтті', 'Overdue'],
  'history.status.in_progress': ['В процессе', 'Орындалуда', 'In progress'],
  'employee.loading': ['Загружаем профиль сотрудника…', 'Қызметкер профилі жүктелуде…', 'Loading employee profile…'],
  'employee.error.title': ['Не удалось открыть профиль', 'Профильді ашу мүмкін болмады', 'Could not open the profile'],
  'employee.eyebrow': ['ПРОСТРАНСТВО СОТРУДНИКА', 'ҚЫЗМЕТКЕР КЕҢІСТІГІ', 'EMPLOYEE SPACE'],
  'employee.title': ['Ваш путь развития', 'Сіздің даму жолыңыз', 'Your development path'],
  'employee.subtitle': ['Понятные шаги к следующей карьерной цели.', 'Келесі мансаптық мақсатқа жетудің нақты қадамдары.', 'Clear steps towards your next career goal.'],
  'employee.asOf': ['Данные на {date}', '{date} күнгі деректер', 'Data as of {date}'],
  'employee.profile.label': ['ПРОФИЛЬ СОТРУДНИКА · {id}', 'ҚЫЗМЕТКЕР ПРОФИЛІ · {id}', 'EMPLOYEE PROFILE · {id}'],
  'employee.profile.tenure': ['{count} мес. в компании', 'Компаниядағы еңбек өтілі: {count} ай', '{count} months at the company'],
  'employee.profile.tenureUnknown': ['Стаж не указан', 'Еңбек өтілі көрсетілмеген', 'Tenure not specified'],
  'employee.trajectory.title': ['Карьерная траектория', 'Мансаптық даму жолы', 'Career path'],
  'employee.trajectory.target': ['Цель: {role} · {grade}', 'Мақсат: {role} · {grade}', 'Goal: {role} · {grade}'],
  'employee.trajectory.current': ['Сейчас', 'Қазір', 'Current'],
  'employee.trajectory.goal': ['Цель', 'Мақсат', 'Goal'],
  'employee.readiness.title': ['Готовность к цели', 'Мақсатқа дайындық', 'Readiness for your goal'],
  'employee.readiness.description': ['Доля выполненных требований целевого грейда', 'Мақсатты грейд талаптарының орындалу үлесі', 'Share of target grade requirements met'],
  'employee.skills.title': ['Навыки для следующего шага', 'Келесі қадамға қажетті дағдылар', 'Skills for your next step'],
  'employee.skills.scale': ['Уровни от 0 до 5', '0-ден 5-ке дейінгі деңгейлер', 'Levels from 0 to 5'],
  'employee.skills.critical': ['Ключевой', 'Шешуші', 'Critical'],
  'employee.skills.gain': ['+{count} после оценки', 'Бағалаудан кейін +{count}', '+{count} since assessment'],
  'employee.skills.empty': ['Данные о навыках пока недоступны.', 'Дағдылар туралы деректер әзірге қолжетімсіз.', 'Skill data is not available yet.'],
  'employee.skills.effective': ['Эффективный уровень', 'Нақты деңгей', 'Effective level'],
  'employee.skills.required': ['Требуется для цели', 'Мақсатқа қажетті деңгей', 'Required for your goal'],
  'employee.skills.explanation': ['Эффективный уровень = последняя оценка + пройденное после неё', 'Нақты деңгей = соңғы бағалау + одан кейін аяқталған белсенділіктерден алған өсім', 'Effective level = latest assessment + gains from activities completed since then'],
  'employee.history.title': ['История участия', 'Қатысу тарихы', 'Participation history'],
  'employee.history.count': [{ one: '{count} запись', few: '{count} записи', many: '{count} записей', other: '{count} записи' }, '{count} жазба', { one: '{count} record', other: '{count} records' }],
  'employee.history.empty': ['История участия появится после первой активности.', 'Қатысу тарихы алғашқы белсенділіктен кейін пайда болады.', 'Your participation history will appear after your first activity.'],
  'employee.nextStep.eyebrow': ['AI-НАВИГАТОР', 'ЖИ КЕҢЕСШІСІ', 'AI NAVIGATOR'],
  'employee.nextStep.title': ['Куда двигаться дальше?', 'Келесі қадам қандай?', 'What is your next step?'],
  'employee.nextStep.description': ['Учитываем цель, разрывы навыков, пройденные шаги и формат работы.', 'Мақсатыңызды, жетілдіруді қажет ететін дағдыларыңызды, аяқталған қадамдар мен жұмыс форматын ескереміз.', 'We consider your goal, skill gaps, completed steps and work format.'],
  'employee.nextStep.loading': ['Подбираем шаги…', 'Қадамдар іріктелуде…', 'Finding steps…'],
  'employee.nextStep.refresh': ['Обновить рекомендации', 'Ұсынымдарды жаңарту', 'Refresh recommendations'],
  'employee.nextStep.select': ['Подобрать шаги', 'Қадамдарды іріктеу', 'Find next steps'],
  'employee.nextStep.analyzing': ['Агент анализирует профиль…', 'Агент профильді талдауда…', 'The agent is analysing your profile…'],
  'employee.nextStep.emptyTitle': ['Подходящих шагов сейчас нет', 'Қазір лайықты қадамдар жоқ', 'No suitable steps right now'],
  'employee.nextStep.emptyDescription': ['Проверьте цель или доступные мероприятия позже.', 'Мақсатыңызды тексеріңіз немесе қолжетімді іс-шараларды кейінірек қараңыз.', 'Review your goal or check available activities later.'],
  'employee.available.title': ['Доступные шаги', 'Қолжетімді қадамдар', 'Available steps'],
  'employee.available.empty': ['Нажмите «Подобрать шаги», чтобы увидеть персональный план.', 'Жеке жоспарыңызды көру үшін «Қадамдарды іріктеу» түймесін басыңыз.', 'Select “Find next steps” to see your personal plan.'],
  'employee.toast.completed': ['Шаг пройден. Готовность: {before}% → {after}%', 'Қадам аяқталды. Дайындық: {before}% → {after}%', 'Step completed. Readiness: {before}% → {after}%'],
  'employee.toast.progressUpdated': ['Шаг отмечен пройденным. Прогресс обновлён.', 'Қадам аяқталды деп белгіленді. Ілгерілеу деректері жаңартылды.', 'Step marked as completed. Progress updated.'],
  'employee.toast.hidden': ['Шаг скрыт — история участия не изменена', 'Қадам жасырылды — қатысу тарихы өзгерген жоқ', 'Step hidden — participation history unchanged'],
  'recommendation.step': ['ШАГ {count}', '{count}-ҚАДАМ', 'STEP {count}'],
  'recommendation.session': ['Ближайшая сессия: {date}', 'Келесі сессия: {date}', 'Next session: {date}'],
  'recommendation.rationaleFallback': ['Этот шаг поможет приблизиться к выбранной карьерной цели.', 'Бұл қадам таңдаған мансаптық мақсатыңызға жақындатады.', 'This step will help you move towards your chosen career goal.'],
  'recommendation.factors.hide': ['Скрыть дополнительные факторы', 'Қосымша факторларды жасыру', 'Hide additional factors'],
  'recommendation.factors.more': [{ one: 'ещё {count} фактор', few: 'ещё {count} фактора', many: 'ещё {count} факторов', other: 'ещё {count} фактора' }, 'тағы {count} фактор', { one: '{count} more factor', other: '{count} more factors' }],
  'recommendation.readinessAfter': ['Готовность после шага', 'Қадамнан кейінгі дайындық', 'Readiness after this step'],
  'recommendation.updating': ['Обновляем…', 'Жаңартылуда…', 'Updating…'],
  'recommendation.complete': ['Отметить пройденным', 'Аяқталды деп белгілеу', 'Mark as completed'],
  'recommendation.notNow': ['Не сейчас', 'Кейінірек', 'Not now'],
  'recommendation.demoNote': ['В демо заменяет отметку из LMS / журнала посещаемости', 'Демода LMS жүйесіндегі / қатысу журналындағы белгінің орнына қолданылады', 'In the demo, this replaces an LMS / attendance record'],
  'recommendation.source.ai': ['AI · {model} · {seconds} с', 'ЖИ · {model} · {seconds} с', 'AI · {model} · {seconds} s'],
  'recommendation.source.unknownModel': ['модель не указана', 'модель көрсетілмеген', 'model not specified'],
  'recommendation.source.fallback': ['Резервный режим — объяснение от движка', 'Резервтік режим — түсіндірмені есептеу жүйесі дайындады', 'Fallback mode — explanation from the rules engine'],
  'recommendation.trace.title': ['Как агент пришёл к решению', 'Агент шешімге қалай келді', 'How the agent reached its decision'],
  'recommendation.trace.toolCall': ['Вызов инструмента', 'Құралды шақыру', 'Tool call'],
  'recommendation.rejected.title': ['Почему не другой шаг?', 'Неліктен басқа қадам таңдалмады?', 'Why not a different step?'],
  'hr.eyebrow': ['АНАЛИТИКА КОМАНДЫ', 'КОМАНДА АНАЛИТИКАСЫ', 'TEAM ANALYTICS'],
  'hr.title': ['Обзор для HR', 'HR шолуы', 'HR overview'],
  'hr.subtitle': ['Где команде нужна поддержка и какие шаги работают.', 'Командаға қай тұста қолдау қажет және қандай қадамдар нәтиже береді.', 'Where the team needs support and which steps are working.'],
  'hr.access': ['Доступно только HR', 'Тек HR қызметіне қолжетімді', 'HR access only'],
  'hr.loading': ['Загружаем аналитику…', 'Аналитика жүктелуде…', 'Loading analytics…'],
  'hr.error.title': ['Не удалось загрузить аналитику', 'Аналитиканы жүктеу мүмкін болмады', 'Could not load analytics'],
  'hr.kpi.skillGaps': ['Навыков с разрывом', 'Жетілдіруді қажет ететін дағдылар', 'Skills with gaps'],
  'hr.kpi.skillGapsHint': ['в целевых профилях', 'мақсатты профильдерде', 'in target profiles'],
  'hr.kpi.activities': ['Активностей в отчёте', 'Есептегі белсенділіктер', 'Activities in the report'],
  'hr.kpi.activitiesHint': ['по истории участия', 'қатысу тарихы бойынша', 'based on participation history'],
  'hr.kpi.noStep': ['Без следующего шага', 'Келесі қадамы жоқ', 'Without a next step'],
  'hr.kpi.noStepHint': ['нужна проверка цели', 'мақсатты тексеру қажет', 'goal needs review'],
  'hr.kpi.attention': ['Требуют внимания', 'Назар аударуды қажет етеді', 'Need attention'],
  'hr.kpi.attentionHint': ['участие снизилось', 'қатысу белсенділігі төмендеген', 'participation has declined'],
  'hr.skills.title': ['Чаще всего отстают', 'Жиі жетіспейтін дағдылар', 'Most common skill gaps'],
  'hr.skills.description': ['Сотрудников с разрывом до целевого уровня навыка', 'Дағдысы мақсатты деңгейге жетпеген қызметкерлер саны', 'Employees below the target skill level'],
  'hr.skills.empty': ['Разрывов навыков пока нет.', 'Әзірге дағдылар бойынша алшақтық жоқ.', 'No skill gaps yet.'],
  'hr.skills.waiting': ['Ожидаем данные аналитики.', 'Аналитика деректері күтілуде.', 'Waiting for analytics data.'],
  'hr.chart.employees': ['Сотрудников', 'Қызметкерлер саны', 'Employees'],
  'hr.chart.description': [{ one: '{name}: {count} сотрудник', few: '{name}: {count} сотрудника', many: '{name}: {count} сотрудников', other: '{name}: {count} сотрудника' }, '{name}: {count} қызметкер', { one: '{name}: {count} employee', other: '{name}: {count} employees' }],
  'hr.upload.title': ['Загрузка профилей', 'Профильдерді жүктеу', 'Upload profiles'],
  'hr.upload.description': ['Добавьте профили и историю в формате датасета. Новые сотрудники появятся в поиске.', 'Профильдер мен қатысу тарихын деректер жиынының форматында қосыңыз. Жаңа қызметкерлер іздеуде пайда болады.', 'Add profiles and history in the dataset format. New employees will appear in search.'],
  'hr.upload.loading': ['Загружаем файлы…', 'Файлдар жүктелуде…', 'Uploading files…'],
  'hr.upload.drop': ['Перетащите файлы сюда', 'Файлдарды осында сүйреп әкеліңіз', 'Drag files here'],
  'hr.upload.choose': ['Выбрать файлы', 'Файлдарды таңдау', 'Choose files'],
  'hr.upload.filesLabel': ['Файлы датасета', 'Деректер жиынының файлдары', 'Dataset files'],
  'hr.upload.profiles': ['Загруженные профили ({count})', 'Жүктелген профильдер ({count})', 'Uploaded profiles ({count})'],
  'hr.upload.openProfile': ['Открыть профиль {id}', '{id} профилін ашу', 'Open profile {id}'],
  'hr.upload.warnings': ['Замечания к загрузке', 'Жүктеу бойынша ескертулер', 'Upload warnings'],
  'hr.upload.invalidFiles': ['Неизвестные файлы: {files}. Выберите {accepted}.', 'Белгісіз файлдар: {files}. Мына файлдарды таңдаңыз: {accepted}.', 'Unrecognised files: {files}. Choose {accepted}.'],
  'hr.upload.success': ['Загрузка завершена. Добавлено записей: {added}, обновлено: {updated}.', 'Жүктеу аяқталды. Қосылған жазбалар: {added}, жаңартылғаны: {updated}.', 'Upload complete. Records added: {added}, updated: {updated}.'],
  'hr.reset.loading': ['Восстанавливаем…', 'Қалпына келтірілуде…', 'Restoring…'],
  'hr.reset.button': ['Восстановить исходные данные', 'Бастапқы деректерді қалпына келтіру', 'Restore original data'],
  'hr.reset.success': ['Исходный датасет восстановлен.', 'Бастапқы деректер жиыны қалпына келтірілді.', 'Original dataset restored.'],
  'hr.participation.title': ['Участие по активностям', 'Белсенділіктерге қатысу', 'Participation by activity'],
  'hr.participation.onlyVoluntary': ['Только добровольные', 'Тек ерікті белсенділіктер', 'Voluntary activities only'],
  'hr.participation.shown': ['Показано {count} из {total} активностей', '{total} белсенділіктің {count} көрсетілді', 'Showing {count} of {total} activities'],
  'hr.participation.tableLabel': ['Таблица участия по активностям', 'Белсенділіктерге қатысу кестесі', 'Activity participation table'],
  'hr.participation.completed': ['Пройдено', 'Аяқталды', 'Completed'],
  'hr.participation.noShow': ['Не пришли', 'Қатыспады', 'Did not attend'],
  'hr.participation.declined': ['Отказ', 'Бас тартты', 'Declined'],
  'hr.participation.mandatory': ['Обязательное', 'Міндетті', 'Mandatory'],
  'hr.participation.emptyVoluntary': ['Добровольных активностей в отчёте пока нет. Снимите фильтр, чтобы увидеть все.', 'Есепте әзірге ерікті белсенділіктер жоқ. Барлығын көру үшін сүзгіні алып тастаңыз.', 'No voluntary activities in the report yet. Clear the filter to see all activities.'],
  'hr.participation.empty': ['Данных об участии пока нет.', 'Қатысу туралы деректер әзірге жоқ.', 'No participation data yet.'],
  'hr.support.title': ['Нужна поддержка', 'Қолдау қажет', 'Support needed'],
  'hr.support.noStep': ['Нет подходящего шага', 'Лайықты қадам жоқ', 'No suitable step'],
  'hr.support.reviewGoal': ['Проверьте цель и доступные активности', 'Мақсат пен қолжетімді белсенділіктерді тексеріңіз', 'Review the goal and available activities'],
  'hr.support.allHaveSteps': ['Для всех есть доступный шаг.', 'Барлық қызметкер үшін қолжетімді қадам бар.', 'Everyone has an available step.'],
  'hr.support.declining': ['Снижается участие', 'Қатысу белсенділігі төмендеуде', 'Declining participation'],
  'hr.support.conversation': ['Нужен личный разговор о предпочтениях', 'Қызметкердің қалауын жеке әңгімеде талқылау қажет', 'Discuss preferences in a one-to-one conversation'],
  'hr.support.empty': ['Нет сотрудников, требующих внимания.', 'Назар аударуды қажет ететін қызметкерлер жоқ.', 'No employees need attention.'],
  // Client-side errors rendered by the pages; wiring api/client.ts belongs to stage 2.
  'error.timeout': ['Сервер не ответил за 20 секунд. Попробуйте ещё раз.', 'Сервер 20 секунд ішінде жауап бермеді. Қайталап көріңіз.', 'The server did not respond within 20 seconds. Please try again.'],
  'error.network': ['Нет связи с сервером. Проверьте, что API запущен.', 'Сервермен байланыс жоқ. API іске қосылғанын тексеріңіз.', 'Cannot connect to the server. Check that the API is running.'],
  'error.server': ['Сервер вернул ошибку {status}', 'Сервер {status} қатесін қайтарды', 'The server returned error {status}'],
} satisfies Record<string, readonly [Message, Message, Message]>

export type TranslationKey = keyof typeof messages
type Dictionary = Record<TranslationKey, Message>
function column(index: 0 | 1 | 2): Dictionary {
  return Object.fromEntries(Object.entries(messages).map(([key, values]) => [key, values[index]])) as Dictionary
}
export const dictionary: Record<Language, Dictionary> = { ru: column(0), kk: column(1), en: column(2) }

const rules = {
  ru: new Intl.PluralRules(locales.ru),
  kk: new Intl.PluralRules(locales.kk),
  en: new Intl.PluralRules(locales.en),
}

/** Select a form; templates may contain {count}. useT().plural binds the current language. */
export function plural(n: number, forms: PluralForms, lang: Language = 'ru'): string {
  return (forms[rules[lang].select(n)] ?? forms.other).replaceAll('{count}', String(n))
}

/** Translate UI copy only. Parameters are returned as text, never interpreted as HTML. */
export function translate(lang: Language, key: TranslationKey, params: Params = {}): string {
  const message = dictionary[lang][key]
  if (typeof message !== 'string' && typeof params.count !== 'number') {
    throw new Error(`Translation "${key}" requires a numeric count`)
  }
  const template = typeof message === 'string' ? message : plural(params.count as number, message, lang)
  return template.replace(/\{(\w+)\}/g, (token, name: string) => String(params[name] ?? token))
}

const dateFormatters = Object.fromEntries(
  (Object.keys(locales) as Language[]).map(lang => [lang, new Intl.DateTimeFormat(locales[lang], {
    day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC',
  })]),
) as Record<Language, Intl.DateTimeFormat>

/** Dataset dates are calendar dates. UTC prevents a preceding-day shift in other time zones. */
export function formatDate(iso: string | null | undefined, lang: Language): string {
  if (!iso) return translate(lang, 'common.date.unknown')
  const day = /^\d{4}-\d{2}-\d{2}$/.test(iso)
  const date = new Date(day ? `${iso}T00:00:00Z` : iso)
  if (!Number.isFinite(date.getTime()) || (day && date.toISOString().slice(0, 10) !== iso)) {
    return translate(lang, 'common.date.unknown')
  }
  return dateFormatters[lang].format(date)
}

export function isLanguage(value: unknown): value is Language {
  return value === 'ru' || value === 'kk' || value === 'en'
}

function storedLanguage(fallback: Language): Language {
  try {
    const stored = typeof window === 'undefined' ? null : window.localStorage.getItem(LANGUAGE_STORAGE_KEY)
    return isLanguage(stored) ? stored : fallback
  } catch {
    return fallback // Storage may be blocked; the switch must still work for this session.
  }
}

export interface LanguageContextValue {
  language: Language
  setLanguage: (language: Language) => void
}
export const LanguageContext = createContext<LanguageContextValue | null>(null)

/** Stage 2: wrap App once, replace its language state with useT(), and pass language to ApiContext. */
export function LanguageProvider({ children, initialLanguage = 'ru' }: { children: ReactNode; initialLanguage?: Language }) {
  const [language, updateLanguage] = useState<Language>(() => storedLanguage(initialLanguage))
  const setLanguage = useCallback((next: Language) => {
    if (isLanguage(next)) updateLanguage(next)
  }, [])
  useEffect(() => {
    document.documentElement.lang = language
    try { window.localStorage.setItem(LANGUAGE_STORAGE_KEY, language) } catch { /* Session selection remains usable. */ }
  }, [language])
  const value = useMemo(() => ({ language, setLanguage }), [language, setLanguage])
  return createElement(LanguageContext.Provider, { value }, children)
}

/** const { t, language, setLanguage, plural, formatDate } = useT() */
export function useT() {
  const context = useContext(LanguageContext)
  if (!context) throw new Error('useT must be used within LanguageProvider')
  const { language, setLanguage } = context
  return useMemo(() => ({
    language,
    setLanguage,
    t: (key: TranslationKey, params?: Params) => translate(language, key, params),
    plural: (n: number, forms: PluralForms) => plural(n, forms, language),
    formatDate: (iso: string | null | undefined) => formatDate(iso, language),
  }), [language, setLanguage])
}
