"""Replace/extend this module in Umar's branch; public contract is frozen in docs/API.md."""
from time import perf_counter


async def recommend(engine, employee_id: str, language: str = 'ru') -> dict:
    """Honest non-AI baseline so UI/backend can be developed without an API key."""
    started = perf_counter()
    candidates = engine.candidates(employee_id)
    recommendations = []
    for candidate in candidates[:3]:
        recommendations.append({**candidate, 'reason': ' • '.join(item['text'] for item in candidate['evidence'])})
    return {
        'mode': 'rules',
        'warning': 'Резервный подбор по правилам. OpenAI-агент ещё не подключён; это не AI-рекомендация.',
        'recommendations': recommendations,
        'empty_reason': None if candidates else 'Нет доступных активностей, закрывающих разрыв к выбранной цели.',
        'trace': [{'tool': 'list_candidates', 'summary': f'Проверены ограничения; допустимых кандидатов: {len(candidates)}',
                   'duration_ms': round((perf_counter()-started)*1000)}],
        'duration_ms': round((perf_counter()-started)*1000),
    }
