#!/usr/bin/env python3
"""
Daily horoscope: Gemini -> Telegram channel.
Secrets: GEMINI_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
Optional: HOROSCOPE_LANG=uk|ru (default uk), GEMINI_MODEL
"""

from __future__ import annotations

import os
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


def generate_text(api_key: str, model_name: str, lang: str) -> str:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    today = date.today()
    text = model.generate_content(_prompt(lang, today)).text
    if not text or not text.strip():
        raise RuntimeError("Empty response from Gemini")
    return text.strip()


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
    model_name = os.environ.get("GEMINI_MODEL") or "gemini-2.0-flash"

    if not api_key or not token or not chat_id:
        print(
            "Set GEMINI_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID",
            file=sys.stderr,
        )
        return 2

    last_err: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            body = generate_text(api_key, model_name, lang)
            send_telegram(token, chat_id, body)
            print("OK: posted to Telegram")
            return 0
        except Exception as e:
            last_err = e
            print(f"Attempt {attempt}/{MAX_RETRIES}: {e}", file=sys.stderr)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SEC)

    print(f"Failed: {last_err}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
