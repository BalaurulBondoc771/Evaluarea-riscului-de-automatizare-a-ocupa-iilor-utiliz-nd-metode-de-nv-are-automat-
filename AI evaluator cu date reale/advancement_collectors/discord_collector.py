"""
discord_collector.py — Colector opțional pentru știri AI din canale Discord.

CERINȚE:
  pip install discord.py

CONFIGURARE (env vars sau .streamlit/secrets.toml):
  DISCORD_BOT_TOKEN    = "Bot ..."
  DISCORD_CHANNEL_IDS  = "123456789,987654321"  (ID-uri separate prin virgulă)
  DISCORD_LOOKBACK_DAYS = "7"

DATE STOCATE: NUMAI link, titlu, dată, canal și sumar (max 500 caractere).
Nu se stochează autori, roluri, avatare sau alte date personale.

MARCAJ în UI: "Semnal curatorial (Discord)" — nu se prezintă ca sursă academică.
"""
from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timedelta, timezone

from advancement_collectors import BaseCollector, make_advancement

logger = logging.getLogger(__name__)

_URL_RE = re.compile(r"https?://\S+")


def _discord_available() -> bool:
    try:
        import discord  # noqa: F401
        return True
    except ImportError:
        return False


def _extract_url(text: str) -> str:
    m = _URL_RE.search(text)
    return m.group(0) if m else ""


def _extract_title(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line[:200]
    return text[:100]


def _extract_summary(text: str) -> str:
    return text[:500].strip()


class DiscordCollector(BaseCollector):
    """
    Citește mesaje recente din canale Discord configurate via bot.

    Salvează NUMAI: link, titlu, dată, canal, sumar.
    Autorul și alte date personale sunt ignorate.
    """

    SOURCE_TYPE = "discord"

    def __init__(self) -> None:
        self._token = os.environ.get("DISCORD_BOT_TOKEN", "")
        raw_ids     = os.environ.get("DISCORD_CHANNEL_IDS", "")
        self._channel_ids = [
            int(cid.strip())
            for cid in raw_ids.split(",")
            if cid.strip().isdigit()
        ]
        self._lookback_days = int(os.environ.get("DISCORD_LOOKBACK_DAYS", "7"))

    def is_available(self) -> bool:
        return _discord_available() and bool(self._token) and bool(self._channel_ids)

    def collect(self, max_results: int = 50) -> list[dict]:
        if not self.is_available():
            logger.info(
                "discord_collector: neconfigurat "
                "(discord.py sau token/channel_ids lipsesc)"
            )
            return []
        try:
            return self._run_sync(max_results)
        except Exception as exc:
            logger.warning("discord_collector: collect failed: %s", exc)
            return []

    def _run_sync(self, max_results: int) -> list[dict]:
        import asyncio
        import discord

        results:  list[dict] = []
        after_dt = datetime.now(timezone.utc) - timedelta(days=self._lookback_days)

        async def _fetch() -> None:
            intents = discord.Intents.default()
            intents.message_content = True
            client = discord.Client(intents=intents)

            @client.event
            async def on_ready() -> None:
                try:
                    for channel_id in self._channel_ids:
                        try:
                            channel      = await client.fetch_channel(channel_id)
                            channel_name = getattr(channel, "name", str(channel_id))
                            async for msg in channel.history(limit=200, after=after_dt):
                                content = (msg.content or "").strip()
                                if not content:
                                    continue
                                url   = _extract_url(content)
                                title = _extract_title(content)
                                summ  = _extract_summary(content)
                                pub   = msg.created_at.strftime("%Y-%m-%d")

                                results.append(make_advancement(
                                    title=title,
                                    summary=summ,
                                    source_type="discord",
                                    source_name=f"Discord — #{channel_name}",
                                    source_url=url or f"discord://channel/{channel_id}/{msg.id}",
                                    published_date=pub,
                                    maturity="emerging",
                                    impact="low",
                                    evidence_strength="low",
                                    adoption_readiness="low",
                                    confidence="low",
                                ))
                                if len(results) >= max_results:
                                    return
                        except Exception as exc:
                            logger.warning(
                                "discord_collector: canal %s failed: %s", channel_id, exc
                            )
                finally:
                    await client.close()

            await client.start(self._token)

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_fetch())
        finally:
            loop.close()

        return results
