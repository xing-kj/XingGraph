<div align="center">
  <a href="https://github.com/xing-kj/xinggraph">
    <h1>XingGraph</h1>
  </a>

  <br />

XingGraph - это платформа для управления памятью ИИ, предназначенная для повышения точности и надежности ответов больших языковых моделей (LLM) и ИИ-агентов.

<p align="center">
  <a href="https://www.youtube.com/watch?v=1bezuvLwJmw&t=2s">Демо</a>
  ·
  <a href="https://xinggraph.ai">Узнать больше</a>
  ·
  <a href="https://discord.gg/NQPKmU5CCg">Присоединиться к Discord</a>
</p>



  [![GitHub forks](https://img.shields.io/github/forks/xing-kj/xinggraph.svg?style=social&label=Fork&maxAge=2592000)](https://GitHub.com/xing-kj/xinggraph/network/)
  [![GitHub stars](https://img.shields.io/github/stars/xing-kj/xinggraph.svg?style=social&label=Star&maxAge=2592000)](https://GitHub.com/xing-kj/xinggraph/stargazers/)
  [![GitHub commits](https://badgen.net/github/commits/xing-kj/xinggraph)](https://GitHub.com/xing-kj/xinggraph/commit/)
  [![Github tag](https://badgen.net/github/tag/xing-kj/xinggraph)](https://github.com/xing-kj/xinggraph/tags/)
  [![Downloads](https://static.pepy.tech/badge/xinggraph)](https://pepy.tech/project/xinggraph)
  [![License](https://img.shields.io/github/license/xing-kj/xinggraph?colorA=00C586&colorB=000000)](https://github.com/xing-kj/xinggraph/blob/main/LICENSE)
  [![Contributors](https://img.shields.io/github/contributors/xing-kj/xinggraph?colorA=00C586&colorB=000000)](https://github.com/xing-kj/xinggraph/graphs/contributors)

<a href="https://www.producthunt.com/posts/xinggraph?embed=true&utm_source=badge-top-post-badge&utm_medium=badge&utm_souce=badge-xinggraph" target="_blank"><img src="https://api.producthunt.com/widgets/embed-image/v1/top-post-badge.svg?post_id=946346&theme=light&period=daily&t=1744472480704" alt="xinggraph - Memory&#0032;for&#0032;AI&#0032;Agents&#0032;&#0032;in&#0032;5&#0032;lines&#0032;of&#0032;code | Product Hunt" style="width: 250px; height: 54px;" width="250" height="54" /></a>


Создавай динамическую память для агентов, используя ECL (Extract -> Cognify -> Load) конвейер.

Узнайте больше о [вариантах использования](https://docs.xinggraph.ai/use-cases) и [бенчмарках](https://github.com/xing-kj/xinggraph/tree/main/evals)

</div>



## Функциональность

- Интеграция и извлечение данных: Позволяет подключать и извлекать прошлые разговоры, документы, изображения и аудиозаписи, обеспечивая доступ к разнообразным источникам информации.

- Снижение галлюцинаций и затрат: Уменьшает вероятность генерации недостоверных ответов, снижает затраты на разработку и эксплуатацию ИИ-приложений.

- Загрузка данных с использованием Pydantic: Обеспечивает загрузку данных в графовые и векторные базы данных с использованием только Pydantic, упрощая процесс интеграции.

- Трансформация и организация данных: Позволяет трансформировать и структурировать данные, собирая их из более чем 30 различных источников, включая PDF, таблицы и другие форматы.

- Модульные ECL-пайплайны: Использует модульные пайплайны Extract, Cognify, Load (ECL) для обработки данных, что обеспечивает гибкость и масштабируемость системы.

- Поддержка онтологий на основе RDF: Использует онтологии на основе RDF для более интеллектуального управления данными и улучшения семантического понимания.

- Локальное развертывание и масштабируемость: Позволяет развернуть систему на собственных серверах, обеспечивая безопасность данных и соответствие требованиям конфиденциальности. Система масштабируется для обработки больших объемов данных.

## Начало работы

Начните легко с помощью Google Colab <a href="https://colab.research.google.com/drive/1g-Qnx6l_ecHZi0IOw23rg0qC4TYvEvWZ?usp=sharing">блокнота</a> или <a href="https://github.com/xing-kj/xinggraph-starter">стартового репозитория</a>

## Помощь проекту

Ваш вклад является основой для превращения этого в настоящий проект с открытым исходным кодом. Любой вклад, который вы сделаете, будет **очень приветствоваться**. Смотрите [`CONTRIBUTING.md`](/CONTRIBUTING.md) для получения дополнительной информации.

## 📦 Установка

Вы можете установить XingGraph, используя **pip**, **poetry**, **uv** или любой другой менеджер пакетов Python.

### С помощью pip

```bash
pip install xinggraph
```

## 💻 Базовое использование

### Настройка

```python
import os
os.environ["LLM_API_KEY"] = "ВАШ_OPENAI_API_KEY"
```

Вы также можете установить переменные, создав файл .env, используя наш <a href="https://github.com/xing-kj/xinggraph/blob/main/.env.template">шаблон</a>.
Для использования различных провайдеров LLM смотрите нашу <a href="https://docs.xinggraph.ai">документацию</a>.

### Пример использования

Этот скрипт выполнит *стандартный* конвейер:

```python
import xinggraph
import asyncio


async def main():
    # Добавляем текст в xinggraph
    await xinggraph.add("Обработка естественного языка (NLP) - это междисциплинарная область компьютерных наук и информационного поиска.")

    # Генерируем граф знаний
    await xinggraph.cognify()

    # Делаем поиск
    results = await xinggraph.search("Расскажите мне о NLP")

    # Отображаем результаты
    for result in results:
        print(result)


if __name__ == '__main__':
    asyncio.run(main())

```
Пример вывода:
```
Обработка естественного языка (NLP) — это междисциплинарная область, которая объединяет компьютерные науки и информационный поиск. Она включает в себя технологии и методы обработки человеческого языка для создания интерфейсов и обработки данных.
```

Визуализация графа:
<a href="https://rawcdn.githack.com/xing-kj/xinggraph/refs/heads/main/assets/graph_visualization.html"><img src="graph_visualization_ru.png" width="100%" alt="Визуализация графа"></a>
[Открыть пример графа в браузере](https://rawcdn.githack.com/xing-kj/xinggraph/refs/heads/main/assets/graph_visualization.html).


Больше примеров в <a href="https://docs.xinggraph.ai">документации</a>.


## Изучите нашу архитектуру

## Демонстрации

1. Что такое память ИИ:
[Видео](https://github.com/user-attachments/assets/8b2a0050-5ec4-424c-b417-8269971503f0)

2. Простая демонстрация GraphRAG
[Видео](https://github.com/user-attachments/assets/d80b0776-4eb9-4b8e-aa22-3691e2d44b8f)

3. XingGraph с Ollama
[Видео](https://github.com/user-attachments/assets/8621d3e8-ecb8-4860-afb2-5594f2ee17db)

## Правила поведения

Мы стремимся сделать открытый исходный код приятным и уважительным опытом для нашего сообщества. Смотрите <a href="/CODE_OF_CONDUCT.md"><code>CODE_OF_CONDUCT</code></a> для получения дополнительной информации.

## 💫 Контрибьюторы

<a href="https://github.com/xing-kj/xinggraph/graphs/contributors">
  <img alt="участники" src="https://contrib.rocks/image?repo=xing-kj/xinggraph"/>
</a>

## История звёзд на GitHub

[![График истории звёзд](https://api.star-history.com/svg?repos=xing-kj/xinggraph&type=Date)](https://star-history.com/#xing-kj/xinggraph&Date)
