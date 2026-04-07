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
from datetime import date

import google.generativeai as genai
import requests

MAX_RETRIES = 3
RETRY_DELAY_SEC = 5


def _prompt(lang: str, today: date) -> str:
    if lang == "ru":
        return (
            f"Сегодня {today.isoformat()}. Напиши короткий развлекательный гороскоп на день "
            "для широкой аудитории: ровно 1–2 предложения, нейтральный доброжелательный тон, "
            "без категоричных предсказаний и медицинских/финансовых советов. "
            "Только текст поста, без заголовков и хэштегов."
        )
    return (
        f"Сьогодні {today.isoformat()}. Напиши короткий розважальний гороскоп на день "
        "для широкої аудиторії: рівно 1–2 речення, нейтральний доброзичливий тон, "
        "без категоричних передбачень і медичних/фінансових порад. "
        "Лише текст поста, без заголовків і хештегів."
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
    today = date.today()
    prompt = _prompt(lang, today)
    response = model.generate_content(prompt)
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
    За замовчуванням тільки 1.5-flash: у багатьох проєктів на free tier квота на 2.0 = 0.
    Щоб увімкнути 2.0 — задайте змінну GEMINI_MODEL=gemini-2.0-flash (і переконайтесь у квоті в Google AI).
    """
    preferred = (os.environ.get("GEMINI_MODEL") or "").strip()
    models: list[str] = []
    if preferred:
        models.append(preferred)
    # Без 2.0 у списку за замовчуванням — уникнути limit: 0 на free tier
    for m in ("gemini-1.5-flash", "gemini-1.5-flash-8b"):
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


def send_telegram(token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    r = requests.post(
        url,
        json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
        timeout=60,
    )
    if not r.ok:
        raise RuntimeError(f"Telegram API {r.status_code}: {r.text[:500]}")


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

    last_err: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            body = generate_text_with_fallback(api_key, lang)
            send_telegram(token, chat_id, body)
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
