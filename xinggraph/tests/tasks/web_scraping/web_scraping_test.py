import asyncio
import xinggraph
from xinggraph.tasks.web_scraper.config import DefaultCrawlerConfig
from xinggraph.tasks.web_scraper import cron_web_scraper_task


async def test_web_scraping_using_bs4():
    await xinggraph.prune.prune_data()
    await xinggraph.prune.prune_system()

    url = "https://quotes.toscrape.com/"
    rules = {
        "quotes": {"selector": ".quote span.text", "all": True},
        "authors": {"selector": ".quote small", "all": True},
    }

    soup_config = DefaultCrawlerConfig(
        concurrency=5,
        crawl_delay=0.5,
        timeout=15.0,
        max_retries=2,
        retry_delay_factor=0.5,
        extraction_rules=rules,
        use_playwright=False,
    )

    await xinggraph.add(
        data=url,
        soup_crawler_config=soup_config,
        incremental_loading=False,
    )

    await xinggraph.cognify()

    results = await xinggraph.search(
        "Who said 'The world as we have created it is a process of our thinking. It cannot be changed without changing our thinking'?",
        query_type=xinggraph.SearchType.GRAPH_COMPLETION,
    )
    assert "Albert Einstein" in results[0]
    print("Test passed! Found Albert Einstein in scraped data.")


async def test_web_scraping_using_bs4_and_incremental_loading():
    await xinggraph.prune.prune_data()
    await xinggraph.prune.prune_system(metadata=True)

    url = "https://books.toscrape.com/"
    rules = {"titles": "article.product_pod h3 a", "prices": "article.product_pod p.price_color"}

    soup_config = DefaultCrawlerConfig(
        concurrency=1,
        crawl_delay=0.1,
        timeout=10.0,
        max_retries=1,
        retry_delay_factor=0.5,
        extraction_rules=rules,
        use_playwright=False,
        structured=True,
    )

    await xinggraph.add(
        data=url,
        soup_crawler_config=soup_config,
        incremental_loading=True,
    )

    await xinggraph.cognify()

    results = await xinggraph.search(
        "What is the price of 'A Light in the Attic' book?",
        query_type=xinggraph.SearchType.GRAPH_COMPLETION,
    )
    assert "51.77" in results[0]
    print("Test passed! Found 'A Light in the Attic' in scraped data.")


async def test_web_scraping_using_tavily():
    await xinggraph.prune.prune_data()
    await xinggraph.prune.prune_system(metadata=True)

    url = "https://quotes.toscrape.com/"

    await xinggraph.add(
        data=url,
        incremental_loading=False,
    )

    await xinggraph.cognify()

    results = await xinggraph.search(
        "Who said 'The world as we have created it is a process of our thinking. It cannot be changed without changing our thinking'?",
        query_type=xinggraph.SearchType.GRAPH_COMPLETION,
    )
    assert "Albert Einstein" in results[0]
    print("Test passed! Found Albert Einstein in scraped data.")


async def test_web_scraping_using_tavily_and_incremental_loading():
    await xinggraph.prune.prune_data()
    await xinggraph.prune.prune_system(metadata=True)

    url = "https://quotes.toscrape.com/"

    await xinggraph.add(
        data=url,
        incremental_loading=True,
    )

    await xinggraph.cognify()

    results = await xinggraph.search(
        "Who said 'The world as we have created it is a process of our thinking. It cannot be changed without changing our thinking'?",
        query_type=xinggraph.SearchType.GRAPH_COMPLETION,
    )
    assert "Albert Einstein" in results[0]
    print("Test passed! Found Albert Einstein in scraped data.")


# ---------- cron job tests ----------
async def test_cron_web_scraper():
    await xinggraph.prune.prune_data()
    await xinggraph.prune.prune_system(metadata=True)
    urls = ["https://quotes.toscrape.com/", "https://books.toscrape.com/"]
    extraction_rules = {
        "quotes": ".quote .text",
        "authors": ".quote .author",
        "titles": "article.product_pod h3 a",
        "prices": "article.product_pod p.price_color",
    }

    # Run cron_web_scraper_task
    await cron_web_scraper_task(
        url=urls,
        job_name="cron_scraping_job",
        extraction_rules=extraction_rules,
    )
    results = await xinggraph.search(
        "Who said 'The world as we have created it is a process of our thinking. It cannot be changed without changing our thinking'?",
        query_type=xinggraph.SearchType.GRAPH_COMPLETION,
    )

    assert "Albert Einstein" in results[0]

    results_books = await xinggraph.search(
        "What is the price of 'A Light in the Attic' book?",
        query_type=xinggraph.SearchType.GRAPH_COMPLETION,
    )

    assert "51.77" in results_books[0]

    print("Cron job web_scraping test passed!")


async def main():
    print("Starting BS4 incremental loading test...")
    await test_web_scraping_using_bs4_and_incremental_loading()

    print("Starting BS4 normal test...")
    await test_web_scraping_using_bs4()

    print("Starting Tavily incremental loading test...")
    await test_web_scraping_using_tavily_and_incremental_loading()

    print("Starting Tavily normal test...")
    await test_web_scraping_using_tavily()

    print("Starting cron job test...")
    await test_cron_web_scraper()


if __name__ == "__main__":
    asyncio.run(main())
