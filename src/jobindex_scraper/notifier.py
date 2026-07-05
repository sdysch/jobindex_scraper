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

        lang_emoji = {
            'english': '\U0001f1ec\U0001f1e7',
            'danish': '\U0001f1e9\U0001f1f0',
            'unknown': '\u2753',
        }

        parts = ['\U0001f514 <b>New Job Matches</b>\n']
        for i, m in enumerate(matches, 1):
            lang = m.get('language', '?')
            emoji = lang_emoji.get(lang, '\u2753')
            parts.append(
                f'{i}. <a href="{m["url"]}">{m["title"]}</a>\n'
                f'\U0001f3e2 {m.get("company", "?")}  '
                f'\U0001f4cd {m.get("location", "?")}\n'
                f'{emoji} {lang.capitalize()}  '
                f'\u2705 {m.get("match_reason", "")}\n'
            )

        text = '\n'.join(parts)
        if len(text) > 4000:
            text = text[:4000] + '\n\n... truncated'

        self.send_message(text)
