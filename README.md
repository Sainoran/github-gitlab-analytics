# Вариант 1

## Цель

Написать скрипт, который собирает данные о пользователе с GitHub и GitLab
и формирует аналитическую сводку в файле `result.json`.

---

## Настройка окружения

Токены и базовые URL загружаются из файла `.env`:

```
GITHUB_TOKEN = "<ваш-токен>"
GITLAB_TOKEN = "<ваш-токен>"

GITHUB_API_URL = "https://api.github.com"
GITLAB_API_URL = "https://gitlab.example.com/api/v4"
```

> `GITHUB_API_URL` и `GITLAB_API_URL` — базовые адреса API **без завершающего
> слеша**. К ним вы добавляете путь эндпоинта: `{GITHUB_API_URL}/user`.

---

## Какие данные нужно получить

### GitHub

| Эндпоинт | Метод | Описание |
|-----------|-------|----------|
| `/user` | GET | Профиль текущего пользователя |
| `/user/repos` | GET | Список репозиториев пользователя |

Для каждого репозитория из `/user/repos` в ответе есть поле
`languages_url` — это готовая ссылка на список языков этого
репозитория. Отправьте GET-запрос по этой ссылке, чтобы получить
языки.

**Пример цепочки запросов:**

1. `GET /user/repos` → получаете список репозиториев
2. Для каждого репозитория берёте значение `languages_url`
3. `GET {languages_url}` → получаете языки этого репозитория

> Это значит, что для N репозиториев вы сделаете 1 + N запросов:
> один за списком и по одному за языками каждого.

Заголовки (для всех запросов к GitHub):

```
Authorization: Bearer <GITHUB_TOKEN>
Accept: application/vnd.github+json
X-GitHub-Api-Version: 2022-11-28
```

Из `/user` понадобятся: `login`, `name`, `bio`, `email`.

Из `/user/repos` понадобятся (для каждого репозитория):
`name`, `stargazers_count`, `forks_count`, `updated_at`.

Из `languages_url` вы получите объект вида
`{"Python": 15000, "JavaScript": 3000}` — вам нужны только
названия языков (ключи).

Документация:
- https://docs.github.com/en/rest/users/users#get-the-authenticated-user
- https://docs.github.com/en/rest/repos/repos#list-repositories-for-the-authenticated-user
- https://docs.github.com/en/rest/repos/repos#list-repository-languages

### GitLab

| Эндпоинт | Метод | Описание |
|-----------|-------|----------|
| `/user` | GET | Профиль текущего пользователя |

Заголовок:

```
PRIVATE-TOKEN: <GITLAB_TOKEN>
```

Из `/user` понадобятся: `username`, `state`, `location`,
`public_email`.

Документация:
https://docs.gitlab.com/ee/api/users.html#for-normal-users-1

---

## Что должно быть в `result.json`

В итоговый файл записывается **только сводка** — сырые данные из API
сохранять не нужно.

### Структура

```json
{
  "github_username": "octocat_pro",
  "gitlab_username": "alex_gitlab_99",
  "total_repos": 5,
  "total_stars": 1335,
  "total_forks": 352,
  "most_popular_repo": "awesome-project-v1",
  "languages": ["Go", "JavaScript", "Python"],
  "github_profile_filled": 4,
  "gitlab_profile_filled": 3,
  "errors": []
}
```

### Описание полей

| Поле | Тип | Описание |
|------|-----|----------|
| `github_username` | `str \| null` | `login` из GitHub. `null`, если не удалось получить |
| `gitlab_username` | `str \| null` | `username` из GitLab. `null`, если не удалось получить |
| `total_repos` | `int` | Количество репозиториев из GitHub |
| `total_stars` | `int` | Сумма `stargazers_count` по всем репозиториям |
| `total_forks` | `int` | Сумма `forks_count` по всем репозиториям |
| `most_popular_repo` | `str \| null` | `name` репозитория с наибольшим `stargazers_count`. `null`, если репозиториев нет |
| `languages` | `list` | **Уникальные** языки со всех репозиториев, отсортированные по алфавиту. `[]`, если данных нет |
| `github_profile_filled` | `int` | Сколько из 4 полей GitHub-профиля заполнены (не `null` и не `""`) |
| `gitlab_profile_filled` | `int` | Сколько из 4 полей GitLab-профиля заполнены (не `null` и не `""`) |
| `errors` | `list` | Список строк с описанием ошибок (см. ниже) |

### Подсчёт заполненности профиля

**GitHub** — 4 поля: `login`, `name`, `bio`, `email`.
**GitLab** — 4 поля: `username`, `state`, `location`, `public_email`.

Поле считается заполненным, если API вернул для него непустое значение
(не `null` и не `""`).

### Пример

API GitHub `/user` вернул:
```json
{"login": "octocat", "name": "Octo", "bio": null, "email": null}
```

Тогда `github_profile_filled` = `2` (заполнены `login` и `name`).

---

## Обработка ошибок

Каждый запрос обрабатывается **независимо**. Если один упал — остальные
должны выполниться.

Если запрос завершился ошибкой (код 4xx/5xx, таймаут, сетевая ошибка),
добавьте строку с описанием в массив `"errors"`:

```json
{
  "github_username": null,
  "gitlab_username": "alex_gitlab_99",
  "total_repos": 0,
  "total_stars": 0,
  "total_forks": 0,
  "most_popular_repo": null,
  "languages": [],
  "github_profile_filled": 0,
  "gitlab_profile_filled": 4,
  "errors": [
    "github /user: не удалось загрузить профиль",
    "github /user/repos: не удалось загрузить репозитории"
  ]
}
```

Формат строки ошибки: `"<платформа> <эндпоинт>: <описание>"`.

Если ошибок нет — `"errors": []`.

Если не удалось загрузить репозитории, счётчики равны `0`,
`most_popular_repo` — `null`, `languages` — `[]`.

> Если запрос `/user/repos` упал, запросы за языками отдельных
> репозиториев делать не нужно.
> Если `/user/repos` успешен, но запрос языков для конкретного
> репозитория упал — добавьте ошибку в `"errors"`, но остальные
> репозитории обработайте.

---

## Требования к коду

### PEP 8 и flake8

Ваш код проверяется линтером **flake8** — инструментом, который находит
нарушения стиля PEP 8 (стандарт оформления Python-кода). Грейдер не
примет решение, если flake8 находит ошибки.

**Установка:**

```bash
pip install flake8
```

**Запуск проверки:**

```bash
flake8 main.py
```

Если всё в порядке — команда ничего не выведет. Если есть ошибки,
вы увидите список вида:

```
main.py:16:80: E501 line too long (87 > 79 characters)
main.py:25:1: W291 trailing whitespace
```

Формат: `файл:строка:колонка: код описание`.

**Частые ошибки:**

| Код | Что значит | Как исправить |
|-----|------------|---------------|
| E501 | Строка длиннее 79 символов | Разбейте на несколько строк |
| W291 | Лишние пробелы в конце строки | Удалите пробелы |
| E302 | Нет двух пустых строк перед функцией | Добавьте пустую строку |
| E231 | Нет пробела после запятой | `f(a, b)` вместо `f(a,b)` |
| E261 | Нет двух пробелов перед комментарием | `x = 1  # comment` |

Документация flake8: https://flake8.pycqa.org/en/latest/

Полный список правил PEP 8:
https://peps.python.org/pep-0008/

### Прочие требования

1. **Зависимости**: все библиотеки в `requirements.txt`.
2. **Точка входа**: `python main.py` создаёт `result.json`.

## Как сдать работу

В репозитории должны быть два файла:

1. `main.py` — код решения
2. `requirements.txt` — зависимости

После этого сделайте коммит и запушьте в репозиторий — проверка
запустится автоматически.

## Чек-лист перед отправкой

- [ ] `flake8 main.py` — без ошибок
- [ ] `.env` добавлен в `.gitignore`
- [ ] `python main.py` создаёт корректный `result.json`
- [ ] Ошибки API не ломают скрипт, а попадают в `"errors"`
- [ ] Счётчики, языки и заполненность корректны
- [ ] В репозитории есть `main.py` и `requirements.txt`

## Что делать, если проверка не проходит

Если ошибка на стороне грейдера — напишите преподавателям,
приложив скриншоты с контекстом.
