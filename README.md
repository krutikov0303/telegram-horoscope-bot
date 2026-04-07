# Telegram horoscope bot (Gemini + GitHub Actions)

Один щоденний пост у канал: гороскоп на день **для всіх 12 знаків** (заголовок «назва + емодзі» і 1–2 речення на знак), текст генерує Gemini, публікація через Bot API.

Мова тексту: **змінна** `HOROSCOPE_LANG` — `uk` (за замовчуванням) або `ru` (як у прикладі з «Овен 🔥», «Телец 🐂» тощо).

В кінці тексту поста **завжди** додається підпис (за замовчуванням: `🔮 Щоденний гороскоп тут` і посилання на `@ua_goroskop`). Можна замінити змінною `HOROSCOPE_POST_FOOTER` (багаторядковий текст через `\n`).

Перед текстом у канал відправляється **квадратне зображення** (кремовий фон, клевер, підпис **завжди українською**: «Гороскоп на 8 квітня» з **поточною календарною датою** дня запуску; російський варіант на зображенні не використовується). Щоб вимкнути картинку: змінна `HOROSCOPE_SKIP_COVER=1`.

## Що потрібно заздалегідь

1. **Канал у Telegram** і **бот** [@BotFather](https://t.me/BotFather) → токен бота.
2. Додайте бота в канал **як адміністратора** з правом **публікувати повідомлення**.
3. **ID каналу**: `@your_channel` або числовий `-100...` (наприклад, через [@userinfobot](https://t.me/userinfobot) / властивості каналу).
4. **Ключ Gemini**: [Google AI Studio](https://aistudio.google.com/) → Create API key. Перевірте актуальні умови безкоштовного рівня.

> Якщо доступ до Google AI з вашого регіону обмежений, знадобиться інший спосіб отримати ключ або інший провайдер (тоді треба буде змінити скрипт).

## Локальний тест

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Далі задайте змінні середовища (див. `.env.example`). У PowerShell:

```powershell
$env:GEMINI_API_KEY="..."
$env:TELEGRAM_BOT_TOKEN="..."
$env:TELEGRAM_CHAT_ID="@channel_or_id"
$env:HOROSCOPE_LANG="uk"
python scripts/publish_horoscope.py
```

## GitHub Actions

1. Створіть репозиторій і запуште цей проєкт.
2. **Settings → Secrets and variables → Actions** → додайте secrets:
   - `GEMINI_API_KEY`
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
3. Опційно: **Variables** → `HOROSCOPE_LANG` = `uk` або `ru` (якщо не задано, скрипт використовує `uk`).
4. Опційно: **Variables** → `GEMINI_MODEL` — наприклад `gemini-2.5-flash` ([список моделей](https://ai.google.dev/gemini-api/docs/models)). Якщо не задано, скрипт перебирає `gemini-2.5-flash` → `gemini-2.5-flash-lite` → `gemini-2.0-flash`. Старі `gemini-1.5-*` у API часто повертають **404**.
5. Розклад у `.github/workflows/daily_horoscope.yml` зараз **06:27 UTC** ≈ **08:27 за Києвом** (UTC+2). Змінити час можна лише через `cron` у UTC. У GitHub Actions старт інколи запізнюється на кілька хвилин.

Ручний запуск: вкладка **Actions** → workflow **Daily horoscope** → **Run workflow**.

## Часовий пояс

Cron у GitHub — **тільки UTC**. Для сталого «локального» часу перерахуйте годину в UTC або запускайте двічі на добу під літній/зимовий час (якщо це ще актуально для вашого календаря).

## Помилка 404 «model … is not found»

Модель зняли або перейменували. Подивіться [актуальні id](https://ai.google.dev/gemini-api/docs/models) і задайте **Variables** → `GEMINI_MODEL`, наприклад `gemini-2.5-flash`.

## Помилка 429 / «quota exceeded» / `limit: 0`

Це **ліміт Google Gemini** на безкоштовному API (або денна квота вичерпана, або для обраної моделі квота **0**).

- Перевірте [квоти](https://ai.google.dev/gemini-api/docs/rate-limits) і [використання](https://ai.dev/rate-limit) для свого ключа / проєкту.
- Спробуйте іншу модель через `GEMINI_MODEL` (наприклад `gemini-2.5-flash-lite`), інколи ліміти рахуються окремо.
- Зачекайте до наступного дня (денні ліміти) або увімкніть біллінг у Google Cloud для цього API, якщо потрібно стабільніше.
