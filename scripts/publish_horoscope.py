#!/usr/bin/env python3
"""
Daily horoscope: Gemini -> Telegram channel.
Secrets: GEMINI_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
Optional: HOROSCOPE_LANG=uk|ru (default uk), GEMINI_MODEL
"""

from __future__ import annotations

import os
import re
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import google.generativeai as genai
import requests

from horoscope_cover import render_cover_png

MAX_RETRIES = 3
RETRY_DELAY_SEC = 5
TELEGRAM_MAX_MESSAGE = 4096

# У кінці кожної публікації (після гороскопу). Можна перевизначити змінною HOROSCOPE_POST_FOOTER.
_DEFAULT_POST_FOOTER = "🔮 Щоденний гороскоп тут\n👉 @goroskop_dnya_ua"


def _post_footer() -> str:
    custom = (os.environ.get("HOROSCOPE_POST_FOOTER") or "").strip()
    if not custom:
        return _DEFAULT_POST_FOOTER
    # Якщо в GitHub Variables лишився старий @ — підміняємо на новий канал
    return custom.replace("@ua_goroskop", "@goroskop_dnya_ua")


def _calendar_date_for_posts() -> date:
    """Календарна дата для обкладинки та промпту (не UTC на раннері, а ваш часовий пояс)."""
    tz_name = (os.environ.get("HOROSCOPE_TZ") or "Europe/Kyiv").strip()
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("Europe/Kyiv")
    return datetime.now(tz).date()


def _now_in_posts_tz() -> datetime:
    tz_name = (os.environ.get("HOROSCOPE_TZ") or "Europe/Kyiv").strip()
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("Europe/Kyiv")
    return datetime.now(tz)


def _is_truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in ("1", "true", "yes", "on")


def _load_posted_dates(state_path: Path) -> set[str]:
    if not state_path.exists():
        return set()
    try:
        return {
            line.strip()
            for line in state_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
    except Exception:
        return set()


def _save_posted_dates(state_path: Path, dates: set[str]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(sorted(dates)) + "\n"
    state_path.write_text(body, encoding="utf-8")


def _mark_posted_flag() -> None:
    flag_path_raw = (os.environ.get("HOROSCOPE_POSTED_FLAG_PATH") or "").strip()
    if not flag_path_raw:
        return
    flag_path = Path(flag_path_raw)
    flag_path.parent.mkdir(parents=True, exist_ok=True)
    flag_path.write_text("1\n", encoding="utf-8")

# Заголовки знаків у фіксованому порядку (як у прикладі користувача)
_SIGN_HEADERS_RU = """Овен 🔥
Телец 🐂
Близнецы 🌬️
Рак 🦀
Лев 🦁
Дева 🌾
Весы ⚖️
Скорпион 🦂
Стрелец 🏹
Козерог 🐐
Водолей 🌊
Рыбы 🐟"""

_SIGN_HEADERS_UK = """Овен 🔥
Телець 🐂
Близнюки 🌬️
Рак 🦀
Лев 🦁
Діва 🌾
Терези ⚖️
Скорпіон 🦂
Стрілець 🏹
Козеріг 🐐
Водолій 🌊
Риби 🐟"""


def _prompt(lang: str, today: date) -> str:
    if lang == "ru":
        return (
            f"Дата: {today.isoformat()}.\n\n"
            "Напиши развлекательный гороскоп на день для ВСЕХ 12 знаков зодиака.\n\n"
            "Формат строго такой:\n"
            "- Каждый знак — отдельный блок.\n"
            "- Первая строка блока: ровно одна строка «Название эмодзи» из списка ниже (скопируй название и эмодзи как есть).\n"
            "- Со следующей строки: 1–2 предложения гороскопа для этого знака (живой тон, лёгкая ирония допустима).\n"
            "- Между блоками — одна пустая строка.\n"
            "- Порядок знаков — как в списке, сверху вниз.\n"
            "- Без вступления перед первым знаком, без общего заголовка поста, без нумерации «1.», без Markdown (# **), без хэштегов.\n"
            "- Не давай медицинских, юридических и финансовых советов; избегай категоричных предсказваний.\n\n"
            "Используй ТОЛЬКО эти строки-заголовки (по одной на знак, в этом порядке):\n\n"
            f"{_SIGN_HEADERS_RU}\n"
        )
    return (
        f"Дата: {today.isoformat()}.\n\n"
        "Напиши розважальний гороскоп на день для УСІХ 12 знаків зодіаку.\n\n"
        "Формат строго такий:\n"
        "- Кожен знак — окремий блок.\n"
        "- Перший рядок блоку: рівно один рядок «Назва емодзі» зі списку нижче (скопіюй назву та емодзі як є).\n"
        "- З наступного рядка: 1–2 речення гороскопу для цього знаку (живий тон, легка іронія доречна).\n"
        "- Між блоками — один порожній рядок.\n"
        "- Порядок знаків — як у списку, зверху вниз.\n"
        "- Без вступу перед першим знаком, без заголовка всього посту, без нумерації «1.», без Markdown (# **), без хештегів.\n"
        "- Не давай медичних, юридичних і фінансових порад; уникай категоричних передбачень.\n\n"
        "Використовуй ЛИШЕ ці рядки-заголовки (по одному на знак, у цьому порядку):\n\n"
        f"{_SIGN_HEADERS_UK}\n"
    )


def _extract_gemini_text(response) -> str:
    """Gemini иногда не даёт .text (блок, пустой ответ) — разбираем явно."""
    if getattr(response, "prompt_feedback", None) and getattr(
        response.prompt_feedback, "block_reason", None
    ):
        br = response.prompt_feedback.block_reason
        raise RuntimeError(f"Gemini blocked the prompt: {br}")
    if not response.candidates:
        raise RuntimeError("Gemini returned no candidates (empty or blocked)")
    parts: list[str] = []
    for cand in response.candidates:
        content = getattr(cand, "content", None)
        if not content:
            continue
        for part in getattr(content, "parts", []) or []:
            t = getattr(part, "text", None)
            if t:
                parts.append(t)
    text = "".join(parts).strip()
    if not text:
        try:
            text = (response.text or "").strip()
        except (ValueError, AttributeError) as e:
            raise RuntimeError(f"Could not read Gemini text: {e}") from e
    if not text:
        raise RuntimeError("Empty text from Gemini")
    return text


def generate_text_one_model(api_key: str, model_name: str, lang: str) -> str:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    today = _calendar_date_for_posts()
    prompt = _prompt(lang, today)
    generation_config = genai.GenerationConfig(
        max_output_tokens=8192,
        temperature=0.85,
    )
    response = model.generate_content(
        prompt,
        generation_config=generation_config,
    )
    return _extract_gemini_text(response)


def _sleep_if_rate_limited(err: Exception) -> None:
    """Після 429 API часто просить почекати (retry in Ns)."""
    s = str(err)
    if "429" not in s and "quota" not in s.lower() and "Resource exhausted" not in s:
        return
    m = re.search(r"retry in ([\d.]+)\s*s", s, re.I)
    if m:
        sec = min(120.0, float(m.group(1)) + 2.0)
        print(f"Waiting {sec:.0f}s (rate limit / quota hint)...", file=sys.stderr)
        time.sleep(sec)


def generate_text_with_fallback(api_key: str, lang: str) -> str:
    """
    Актуальні імена моделей (Google AI): див. https://ai.google.dev/gemini-api/docs/models
    Старі gemini-1.5-* часто дають 404. За замовчуванням — 2.5, потім lite, потім 2.0.
    Свою модель можна задати через GEMINI_MODEL.
    """
    preferred = (os.environ.get("GEMINI_MODEL") or "").strip()
    models: list[str] = []
    if preferred:
        models.append(preferred)
    for m in (
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.0-flash",
    ):
        if m not in models:
            models.append(m)
    last_err: Exception | None = None
    for model_name in models:
        try:
            return generate_text_one_model(api_key, model_name, lang)
        except Exception as e:
            last_err = e
            print(f"Gemini model {model_name}: {e}", file=sys.stderr)
            _sleep_if_rate_limited(e)
    raise last_err or RuntimeError("All Gemini models failed")


def send_photo_png(token: str, chat_id: str, png_bytes: bytes) -> None:
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    r = requests.post(
        url,
        data={"chat_id": chat_id},
        files={"photo": ("horoscope_cover.png", png_bytes, "image/png")},
        timeout=120,
    )
    if not r.ok:
        raise RuntimeError(f"Telegram sendPhoto {r.status_code}: {r.text[:500]}")


def _send_one_message(token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    r = requests.post(
        url,
        json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
        timeout=60,
    )
    if not r.ok:
        raise RuntimeError(f"Telegram API {r.status_code}: {r.text[:500]}")


def _split_long_message(text: str) -> list[str]:
    """Розбиття основного тексту без футера."""
    text = text.strip()
    if len(text) <= TELEGRAM_MAX_MESSAGE:
        return [text]
    parts: list[str] = []
    current = ""
    for block in text.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        candidate = current + ("\n\n" if current else "") + block
        if len(candidate) <= TELEGRAM_MAX_MESSAGE:
            current = candidate
        else:
            if current:
                parts.append(current)
            if len(block) > TELEGRAM_MAX_MESSAGE:
                for i in range(0, len(block), TELEGRAM_MAX_MESSAGE - 100):
                    parts.append(block[i : i + TELEGRAM_MAX_MESSAGE - 100])
                current = ""
            else:
                current = block
    if current:
        parts.append(current)
    return parts


def send_telegram(token: str, chat_id: str, text: str) -> None:
    """Telegram ~4096 символів; футер завжди внизу (в останньому повідомленні)."""
    footer = _post_footer()
    sep = "\n\n"
    parts = _split_long_message(text)
    if not parts:
        parts = [footer]
    else:
        suffix = sep + footer
        if len(parts[-1]) + len(suffix) <= TELEGRAM_MAX_MESSAGE:
            parts[-1] = parts[-1] + suffix
        else:
            parts.append(footer)
    for i, chunk in enumerate(parts):
        _send_one_message(token, chat_id, chunk)
        if i < len(parts) - 1:
            time.sleep(0.35)


def main() -> int:
    api_key = os.environ.get("GEMINI_API_KEY")
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    lang = (os.environ.get("HOROSCOPE_LANG") or "uk").lower()
    if lang not in ("uk", "ru"):
        print("HOROSCOPE_LANG must be uk or ru", file=sys.stderr)
        return 2
    if not api_key or not token or not chat_id:
        print(
            "Set GEMINI_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID",
            file=sys.stderr,
        )
        return 2

    enforce_time_gate = _is_truthy(os.environ.get("HOROSCOPE_ENFORCE_TIME_GATE"))
    target_hour = int((os.environ.get("HOROSCOPE_TARGET_HOUR") or "8").strip())
    target_minute = int((os.environ.get("HOROSCOPE_TARGET_MINUTE") or "27").strip())
    post_window_minutes = int((os.environ.get("HOROSCOPE_POST_WINDOW_MINUTES") or "10").strip())

    now_local = _now_in_posts_tz()
    today_local = now_local.date()
    target_local = now_local.replace(
        hour=target_hour,
        minute=target_minute,
        second=0,
        microsecond=0,
    )
    window_end = target_local + timedelta(minutes=post_window_minutes)

    state_path = Path((os.environ.get("HOROSCOPE_STATE_PATH") or ".state/posted_dates.txt").strip())
    posted_dates = _load_posted_dates(state_path)
    today_key = today_local.isoformat()

    if enforce_time_gate and not (target_local <= now_local < window_end):
        print(
            (
                f"SKIP: now={now_local.strftime('%Y-%m-%d %H:%M:%S %Z')}, "
                f"target={target_local.strftime('%H:%M')}, window={post_window_minutes}m"
            )
        )
        return 0

    if enforce_time_gate and today_key in posted_dates:
        print(f"SKIP: already posted for {today_key}")
        return 0

    last_err: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            body = generate_text_with_fallback(api_key, lang)
            skip_cover = (os.environ.get("HOROSCOPE_SKIP_COVER") or "").strip().lower() in (
                "1",
                "true",
                "yes",
            )
            if not skip_cover:
                cover = render_cover_png(_calendar_date_for_posts())
                send_photo_png(token, chat_id, cover)
                time.sleep(0.4)
            send_telegram(token, chat_id, body)
            posted_dates.add(today_key)
            _save_posted_dates(state_path, posted_dates)
            _mark_posted_flag()
            print("OK: posted to Telegram")
            return 0
        except Exception as e:
            last_err = e
            print(f"Attempt {attempt}/{MAX_RETRIES}: {e}", file=sys.stderr)
            if attempt < MAX_RETRIES:
                _sleep_if_rate_limited(e)
                time.sleep(RETRY_DELAY_SEC)

    print(f"Failed: {last_err}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
