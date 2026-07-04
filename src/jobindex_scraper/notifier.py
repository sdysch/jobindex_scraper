import httpx


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str) -> None:
        self.api_url = f'https://api.telegram.org/bot{bot_token}'
        self.chat_id = chat_id

    def send_message(self, text: str) -> None:
        response = httpx.post(
            f'{self.api_url}/sendMessage',
            json={
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': 'HTML',
                'disable_web_page_preview': False,
            },
            timeout=15.0,
        )
        response.raise_for_status()

    def send_match_summary(self, matches: list[dict]) -> None:
        if not matches:
            return

        parts = ['<b>New Job Matches</b>\n']
        for m in matches:
            parts.append(
                f'<a href="{m["url"]}">{m["title"]}</a>\n'
                f'{m.get("company", "?")} \u2014 {m.get("location", "?")}\n'
                f'Lang: {m.get("language", "?")}\n'
                f'{m.get("match_reason", "")}\n'
            )

        text = '\n'.join(parts)
        if len(text) > 4000:
            text = text[:4000] + '\n\n... truncated'

        self.send_message(text)
