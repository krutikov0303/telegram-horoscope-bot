# Telegram horoscope bot (Gemini + GitHub Actions)

Один щоденний пост у канал: короткий гороскоп від Gemini, публікація через Bot API.

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
4. Розклад у `.github/workflows/daily_horoscope.yml` зараз **06:00 UTC** (приблизно ранок за київським часом; підлаштуйте `cron` під себе). GitHub використовує лише UTC.

Ручний запуск: вкладка **Actions** → workflow **Daily horoscope** → **Run workflow**.

## Часовий пояс

Cron у GitHub — **тільки UTC**. Для сталого «локального» часу перерахуйте годину в UTC або запускайте двічі на добу під літній/зимовий час (якщо це ще актуально для вашого календаря).
