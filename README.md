# Article Writer — n8n Workflow

Автоматическая генерация экспертных статей для брендингового агентства DDVB. Workflow запускается через webhook, проводит параллельное исследование через Perplexity, пишет статью с голосом спикера через Claude Sonnet и прогоняет её через гуманизатор GPT-4o.

---

## Типы статей

| Тип | Объём | Структура |
|-----|-------|-----------|
| **Thought Leadership** | 1800–2200 слов | Лид → Контекст → Экспертный взгляд → Кейсы → Вывод |
| **How-to** | 1500–2000 слов | Введение → Проблема → Пошаговое руководство → Примеры → Заключение |
| **PR/Новость** | 800–1200 слов | Заголовок → Лид → Основная часть → Справка → Контакты |

---

## Режимы ввода

### Scratch (с нуля)
Вы указываете тему и краткое описание. Workflow запускает **4 параллельных потока исследования** через Perplexity Sonar и собирает из них единый контекст для автора.

### Theses (по тезисам)
Вы передаёте готовый план статьи в виде списка тезисов. Для каждого тезиса запускается **отдельный поток исследования** последовательно, что даёт более глубокую проработку каждого раздела.

---

## Архитектура pipeline

```
Webhook
  └── Parse Request (mode, articleType, speakerId, topic, theses)
        └── Fetch Speaker Profile (GitHub → fallback default)
              └── Parse Profile (base64 decode, voice guidelines)
                    ├── [Scratch] 4× Perplexity Research (параллельно)
                    │     └── Merge Scratch Research
                    └── [Theses] Perplexity Research per thesis (последовательно)
                          └── Merge Thesis Research
                                └── Build Writer Prompt (type-aware)
                                      └── Claude Sonnet — Article Writer
                                            └── GPT-4o — Humanizer
                                                  └── Callback → Web App
```

---

## Параметры запроса

Webhook принимает POST на `/webhook/article/generate`:

```json
{
  "jobId": "uuid",
  "mode": "scratch",
  "articleType": "thought_leadership",
  "speakerId": "maria_arkhangelskaya",
  "topic": "Брендинг как инструмент B2B-продаж",
  "description": "Почему сильный бренд сокращает цикл сделки",
  "callbackUrl": "https://your-app.com/api/webhooks/n8n-callback",
  "source": "web"
}
```

Для режима `theses` вместо `description` передайте массив:

```json
{
  "mode": "theses",
  "theses": [
    "Бренд снижает стоимость привлечения клиента",
    "Доверие как конкурентное преимущество в тендерах",
    "ROI инвестиций в бренд: как считать"
  ]
}
```

### Поля

| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| `jobId` | string (UUID) | да | ID задачи из Supabase `jobs` |
| `mode` | `scratch` \| `theses` | да | Режим генерации |
| `articleType` | `thought_leadership` \| `howto` \| `pr_news` | да | Тип статьи |
| `speakerId` | string | да | Slug профиля спикера (GitHub) |
| `topic` | string | да | Тема статьи |
| `description` | string | scratch | Контекст и ключевые сообщения |
| `theses` | string[] | theses | Список тезисов (минимум 2) |
| `callbackUrl` | string | да | URL для доставки результата |
| `source` | string | нет | `web` для интеграции с DDVB Marketing App |

---

## Профили спикеров

Профили хранятся в GitHub-репозитории `cybernexcorps/ceo-comment-writer/profiles/` в формате JSON.

Пример: `maria_arkhangelskaya.json`

```json
{
  "name": "Мария Архангельская",
  "title": "CEO & Managing Partner",
  "company": "DDVB",
  "voice_guidelines": "Экспертный, но живой тон..."
}
```

Workflow подставляет голос спикера в промпт автора через `{{speaker_voice_guidelines}}`. Если профиль не найден — используется `default.json`.

---

## Callback (результат)

После завершения workflow отправляет POST на `callbackUrl`:

```json
{
  "jobId": "uuid",
  "status": "completed",
  "workflowType": "article",
  "result": {
    "content": "## Заголовок статьи\n\nТекст...",
    "metadata": {
      "charCount": 12500,
      "wordCount": 1950,
      "articleType": "thought_leadership",
      "speakerName": "Мария Архангельская",
      "speakerTitle": "CEO & Managing Partner"
    }
  },
  "executionTime": 87000,
  "timestamp": "2026-03-13T16:01:18.000Z"
}
```

---

## Структура файлов

```
article-writer/
├── workflow/
│   ├── article-writer-v1.0.json   # n8n workflow (импортировать в n8n)
│   └── api-ready.json             # Версия для деплоя через API
├── prompts/
│   ├── thought-leadership-writer.md
│   ├── howto-writer.md
│   ├── pr-news-writer.md
│   ├── humanizer.md
│   ├── perplexity-research.md     # Scratch mode
│   └── thesis-research.md         # Theses mode
├── sync_local_json.py             # Синхронизация workflow из n8n
└── README.md
```

---

## Деплой

### Импорт workflow

1. Откройте n8n → **Workflows → Import from File**
2. Выберите `workflow/article-writer-v1.0.json`
3. В узлах `Validate API Key`, `Build Callback` и `Build Error Callback` замените `YOUR_N8N_API_KEY` на актуальный JWT-ключ
4. Убедитесь, что в учётных данных n8n настроены: Anthropic, OpenAI, Perplexity, GitHub
5. Активируйте workflow

### Деплой через API

```bash
curl -s -X PUT \
  -H "X-N8N-API-KEY: $N8N_API_KEY" \
  -H "Content-Type: application/json; charset=utf-8" \
  --data-binary @workflow/api-ready.json \
  "https://ddvb.app.n8n.cloud/api/v1/workflows/WORKFLOW_ID"
```

### Синхронизация локальной копии из n8n

```bash
N8N_API_KEY=<ключ> python sync_local_json.py
```

---

## Тестирование

```bash
# Scratch mode — Thought Leadership
curl -s -X POST "https://ddvb.app.n8n.cloud/webhook/article/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "jobId": "00000000-0000-4000-8000-000000000001",
    "mode": "scratch",
    "articleType": "thought_leadership",
    "speakerId": "maria_arkhangelskaya",
    "topic": "Роль бренда в B2B-продажах",
    "description": "Тестовая генерация",
    "callbackUrl": "https://httpbin.org/post",
    "source": "test"
  }'

# Theses mode
curl -s -X POST "https://ddvb.app.n8n.cloud/webhook/article/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "jobId": "00000000-0000-4000-8000-000000000002",
    "mode": "theses",
    "articleType": "howto",
    "speakerId": "maria_arkhangelskaya",
    "topic": "Как провести ребрендинг без потери клиентов",
    "theses": ["Аудит текущего бренда", "Коммуникация изменений", "Мягкий переход"],
    "callbackUrl": "https://httpbin.org/post",
    "source": "test"
  }'
```

Ожидаемое время генерации: **60–120 секунд**.

---

## Интеграция с DDVB Marketing App

Workflow интегрирован с веб-приложением по паттерну async job:

```
ArticleForm → Server Action → jobs (processing)
           → POST /webhook/article/generate
                   ↓ (60–120 сек)
             n8n → POST /api/webhooks/n8n-callback
                   ↓
             Supabase Realtime → ArticleResult (completed)
```

Результирующая страница: `/articles/[jobId]`

---

## Требования

- n8n (cloud или self-hosted)
- Учётные данные: **Anthropic** (Claude Sonnet), **OpenAI** (GPT-4o), **Perplexity** (Sonar), **GitHub** (чтение профилей)
- Supabase `jobs` таблица (если используется с DDVB Marketing App)

---

## Связанные репозитории

- [ceo-comment-writer](https://github.com/cybernexcorps/ceo-comment-writer) — профили спикеров
- [portfolio-cases-writer](https://github.com/cybernexcorps/portfolio-cases-writer) — кейсы для портфолио
