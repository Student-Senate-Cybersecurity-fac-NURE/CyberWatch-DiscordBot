# Cyber Watch Discord-бот

Discord-бот Cyber Watch (форк Threat Intelligence від vx-underground) отримує оновлення з різних clearnet доменів через RSS-стрічки.

* Не хочете налаштовувати? [Цей бот Cyber Watch уже працює у Discord.](https://discord.com/invite/cYWSUM7vYK)
* Написано на Python 3.13
* Працює на Windows або Linux
* Потрібен вебхук Discord
* Легко додавати або видаляти домени для моніторингу
* Логіка синхронізації RSS знаходиться в /Source/Bots/RSS.py

## Початок роботи

* Крок 1. Створіть вебхук. Не знаєте, як створити вебхук? [Discord робить це просто!](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks)
* Крок 2. Створіть файл .env на основі .env.example. Заповніть його вебхуками Discord, створеними на попередньому кроці.
* Крок 3. Переконайтеся, що є інтернет-з'єднання
* Крок 4. Запустіть RSS синхронізатор:

```bash
python -m Source rss-sync
```

## Інші нотатки

* За замовчуванням цей скрипт потребує 3 вебхуки Discord. Він надсилає повідомлення про оновлення приватного сектору, урядові оновлення та статусні логи, щоб показати, чи він працює.
* Для запланованих запусків зберігається стан між виконаннями, щоб уникати дублювань і прогалин.

## Додавання або видалення RSS-стрічок для моніторингу

Усі RSS-стрічки для моніторингу налаштовані в [OriginFeeds/rss_feeds.json](OriginFeeds/rss_feeds.json).

Щоб додати нову RSS-стрічку, додайте новий запис `[url, source_name]` в один із списків:
- `private_rss_feed_list`
- `gov_rss_feed_list`

## Відзнака

* Оригінальний коміт, кодова база, proof-of-concept — [smelly__vx](https://twitter.com/smelly__vx)
* Загальні покращення якості життя та налагодження — [Julien Mousqueton](https://github.com/JMousqueton)
* Розширення функціональності, стандартизація тощо — [hRun](https://github.com/hRun)
* Розширення функціональності, стандартизація тощо — [come2darkside](https://twitter.com/come2darkside_)
