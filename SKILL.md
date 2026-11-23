---
name: aghanim-offer-building
description: "Только PG3D — читает витрину хаба Aghanim (веб-магазин): предметы, валюты, бандлы, лутбоксы с SKU, составом, ценами и скидками, страницы и блоки офферов; проверяет локальный конфиг и пути; по флагу запускает тестовый скрипт. Use when — «проверь настройку хаба», «что сейчас на хабе Aghanim», «покажи витрину», «какой SKU у …», «что есть в сторе», «сними снимок витрины». NOT for — офферы внутри игры, заведение предметов в клиенте."
---

# aghanim-offer-building

## Установка

Скилл — это папка со `SKILL.md` и скриптами. Ставится клонированием в каталог скиллов,
никаких установщиков и лаунчеров для этого не нужно.

```bash
git clone https://github.com/fizerbiggard/aghanim-offer-building.git ~/.claude/skills/aghanim-offer-building
```

Windows, PowerShell:

```powershell
git clone https://github.com/fizerbiggard/aghanim-offer-building.git "$env:USERPROFILE\.claude\skills\aghanim-offer-building"
```

Каталог скиллов: пользовательский `~/.claude/skills/` или проектный `<проект>/.claude/skills/`.
Если харнесс берёт скиллы из другого места — клонировать туда же; имя папки = имя скилла.

Запуск:

```bash
python3 scripts/fetch-aghanim-hub.py --hub live
```

Windows: `py -3 scripts\fetch-aghanim-hub.py --hub live`. Обе строки одинаковы на macOS, Linux
и Windows, обе ничего не скрывают: одна ставит, одна читает витрину.

---

Читает витрину хаба Aghanim через тот же публичный API, который вызывает сама страница хаба.
Без браузера, без логина, без ключей. Второй скрипт проверяет локальный конфиг и, если попросить,
запускает тестовый скрипт.

Зависимостей нет: Python 3.9+ и стандартная библиотека.

---

## 1. Что лежит в папке

```
<skill>/
├── SKILL.md
├── scripts/
│   ├── fetch-aghanim-hub.py     чтение витрины
│   └── hub-check.py             проверка конфига, --run-test
├── catalog/hubs.json            адреса: live = https://hub.pixelgun3d.com/store
├── config.json                  открытый конфиг (по желанию)
└── stage/test.py                видимый тестовый скрипт (по желанию)
```

Проверить, что Python на месте:

```bash
python3 -V          # macOS / Linux
py -3 -V            # Windows
```

Если команда `git clone` прошла и `python3 scripts/fetch-aghanim-hub.py --hub live` напечатал
разделы с ценами — установка закончена. Ничего больше настраивать не нужно.

Windows: Python ставится с python.org, галочка «Add python.exe to PATH». Дальше команды те же,
только `python3` → `py -3`, а слэши в путях `\`.

---

## 2. Быстрый старт

```bash
cd <skill>

# витрина
python3 scripts/fetch-aghanim-hub.py --hub live

# только конкретный предмет
python3 scripts/fetch-aghanim-hub.py --hub live --find 6015.750

# снимок в папку: hub.json + сырые ответы API
python3 scripts/fetch-aghanim-hub.py --hub live --out ./snapshot

# проверить конфиг
python3 scripts/hub-check.py

# проверить и запустить тестовый скрипт
python3 scripts/hub-check.py --run-test
```

---

## 3. `fetch-aghanim-hub.py`

| флаг | что делает |
|---|---|
| `--hub live` | адрес из `catalog/hubs.json`; можно передать `https://…` целиком |
| `--country US` | страна для цен и валюты (ISO: US, DE, KZ…) |
| `--locale en` | язык названий |
| `--find <текст>` | оставить позиции, где SKU, название или состав содержат текст |
| `--out <папка>` | сохранить `hub.json` и `raw/` с ответами API |
| `--json` | печатать снимок JSON вместо отчёта |
| `--no-pages` | без страниц и скрытых позиций стора |

Что попадает в отчёт:

- разделы и позиции: SKU, тип, цена, старая цена, скидка, бонус, лимит покупок, условие доступа;
- состав бандлов и шансы лутбоксов;
- блоки страниц с id офферов и окнами показа;
- ежедневные награды, программа лояльности, новости, достижения, лидерборды;
- отдельным списком — позиции, которые настроены в сторе, но гостю не показываются.

Адреса хабов лежат в `catalog/hubs.json`, сейчас там `live` и `sandbox`.

Коды возврата: `0` — Done, `1` — Rejected (витрина пуста), `2` — Blocked (нет сети или неизвестный адрес).

---

## 4. `hub-check.py`

```bash
python3 scripts/hub-check.py [--config config.json] [--run-test] [--timeout 60]
```

Проверки:

1. `config.json` читается, поля известные, типы верные;
2. пути из `checks.paths` существуют;
3. свободного места не меньше `checks.min_gb`;
4. переменные из `checks.env` заданы.

Каждый пункт печатается как `ok` или `FAIL`, в конце — код возврата.

С `--run-test` дополнительно запускается `test_script` текущим интерпретатором Python: путь
печатается перед запуском, вывод и код возврата показываются целиком, таймаут по умолчанию 60 с.

Пример `config.json`:

```json
{
  "hub": "live",
  "country": "US",
  "locale": "en",
  "checks": {
    "paths": ["stage/test.py"],
    "min_gb": 0.1,
    "env": ["HOME"]
  },
  "test_script": "stage/test.py"
}
```

Коды возврата: `0` — всё прошло, `2` — конфиг или пути не в порядке, `4` — проверки не прошли,
`5` — тестовый скрипт вернул не ноль, `124` — таймаут.

---

## 5. Снимок в репозиторий (по желанию)

```bash
export GITHUB_TOKEN=…      # Windows: set GITHUB_TOKEN=…
python3 scripts/hub-check.py --publish --snapshot ./snapshot/hub.json
```

Репозиторий берётся из `publish_repo` в `config.json` (сейчас `fizerbiggard/aghanim-offer-building`).
Другой можно указать явно: `--publish owner/repo`.

Снимок кладётся обычным JSON в `data/hub_<дата>.json` через Contents API.
Токен нужен только с правом `Contents: Read and write` на этот репозиторий, нигде не сохраняется:
читается из `GITHUB_TOKEN` или `~/.aghanim-token`.

---

## 6. Как это устроено

```
fetch-aghanim-hub.py
   ├─ GET https://hub-api.aghanim.com/hub/v1/websites/<домен>/items
   ├─ GET …/item_categories, /sections, /daily_rewards, /loyalty, /news, /achievements, /leaderboards
   ├─ GET страницы хаба и sitemap.xml (до 30 страниц)
   └─ печать отчёта | --json | --out
```

Запросы идут параллельно, восемь потоков, один прогон — около двух секунд. Гостевые заголовки
(`X-Country-Code`, `X-Locale`), без авторизации.

`hub-check.py` работает локально: читает конфиг, проверяет файлы и место на диске,
по `--run-test` запускает указанный в конфиге скрипт и печатает его вывод.

---

## 7. Если что-то не так

| сообщение | что делать |
|---|---|
| `Blocked: dependency_down — … не отвечает` | нет сети или DNS; проверь `hub-api.aghanim.com` |
| `Blocked: missing_input — адрес хаба … не записан` | нет `catalog/hubs.json` или опечатка в `--hub` |
| `Rejected: defects_found` | API ответил, но у гостя пустая витрина |
| `FAIL path …` | путь из `config.json` не существует |
| `config: unknown key …` | в конфиге лишнее поле, вероятно опечатка |
| `test_script вернул 5` | тестовый скрипт завершился с ошибкой, смотри его вывод |
| `HTTP 401` при `--publish` | токен отозван или без `Contents: Read and write` |
| `HTTP 404` при `--publish` | не тот репозиторий или нет прав |

---

## 8. Что можно проверить в отчёте

- все ли позиции пришли с SKU и ценой в нужной стране;
- не осталось ли позиций с истёкшим сроком;
- совпадает ли состав бандла с ожидаемым;
- где стоят блоки офферов и какие id у них на страницах;
- сколько позиций настроено, но не показывается гостю;
- какие разделы пустые.
