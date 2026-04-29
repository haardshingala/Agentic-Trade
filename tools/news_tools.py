
import os
import yfinance as yf
from typing import List, Dict, Optional
from tavily import TavilyClient
from tools.utils.news_tool_helper import (
    _extract_news_fields,
    _to_iso,
    _get_top5,
    _deduplicate,
    _format_articles,
    _map_priority,
    _score_global,
    _score_indian,
)
from dotenv import load_dotenv
load_dotenv(dotenv_path="../.env")  

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
client     = TavilyClient(api_key=TAVILY_API_KEY)

INDIAN_QUERIES = [
    ("index_movement", "India stock market news Sensex Nifty today"),
    ("macro_policy",   "India economy RBI policy inflation FII rupee news"),
]

INDIAN_DOMAINS = [
    "reuters.com",
    "moneycontrol.com",
    "business-standard.com",
    "livemint.com",
    "m.economictimes.com",
    "economictimes.indiatimes.com",
    "financialexpress.com",
    "cnbctv18.com",
]

GLOBAL_QUERIES = [
    ("indices",    "S&P 500 Nasdaq global stock markets trading today"),
    ("fed_macro",  "Federal Reserve interest rates inflation bond yields outlook"),
    ("commodities","oil crude gold dollar global markets today"),
]

GLOBAL_DOMAINS = [
    "reuters.com",
    "bloomberg.com",
    "cnbc.com",
    "wsj.com",
    "marketwatch.com",
    "ft.com",
]




def get_company_news(ticker: str, limit: int = 5):
    """
    Fetch latest news for a given stock ticker from Yahoo Finance.

    Args:
        ticker (str): Stock ticker (e.g., "RELIANCE.NS")
        limit (int): Max number of articles to return

    Returns:
        dict: {
            "status": "success" | "no_news" | "error",
            "articles": List[dict]
        }

    Notes:
        Assumes news is returned in descending chronological order.
    """
    try:
        stock = yf.Ticker(ticker)
        news = stock.get_news()

        if not news:
            return {
                "status": "no_news",
                "articles": []
            }

        news = news[:limit]

        return {
            "status": "success",
            "articles": _extract_news_fields(news)
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
    
def get_indian_market_news() -> Dict:
    """
    Fetch broad Indian stock market news covering Sensex, Nifty 50,
    FII/DII flows, RBI policy, rupee, and macro data.

    Runs 2 Tavily queries targeting different angles:
      Query 1 (index_movement) → Sensex, Nifty, sector performance
      Query 2 (macro_policy)   → RBI, FII/DII, rupee, inflation

    Results are merged, deduplicated, scored, and filtered.
    Only articles scoring >= 3 are returned to reduce noise.

    Returns:
        Structured dict with ai_summary, prioritized articles, article count.
    """
    try:
        all_articles: List[Dict] = []
        summaries:    List[str]  = []

        for tag, query in INDIAN_QUERIES:
            response = client.search(
                query           = query,
                search_depth    = "advanced",
                topic           = "news",
                max_results     = 7,
                include_domains = INDIAN_DOMAINS,
                include_answer  = True,
            )

            if response.get("answer"):
                summaries.append(response["answer"])

            formatted = _format_articles(response.get("results", []), tag)
            all_articles.extend(formatted)

        unique = _deduplicate(all_articles)

        for a in unique:
            a["score"] = _score_indian(a)
            a["priority"] = _map_priority(a["score"], thresholds=(8, 5))

        filtered = [a for a in unique if a["score"] >= 3]
        normalized = [
            {
                "title"        : a["title"],
                "source"       : a["source"],
                "published_at" : _to_iso(a["date"]),       # renamed
                "summary"      : a["snippet"],    # renamed
                "priority"     : a["priority"],
            }
            for a in filtered
        ]
    
        final_articles = _get_top5(normalized)

        return {
            "status"     : "success",
            "ai_summary" : summaries[0] if summaries else None,
            "articles"   : final_articles,
        }
    except Exception as e:
        return {
            "status"  : "error",
            "message" : str(e),
        }
    

# TOOL 3: Global Market News 

def get_global_market_news() -> Dict:
    """
    Fetch global financial market news covering S&P 500, Nasdaq, Dow,
    Fed decisions, oil, gold, dollar, and major macro events.

    Runs 3 Tavily queries targeting different angles:
      Query 1 (indices)    → S&P 500, Nasdaq, global index movement
      Query 2 (fed_macro)  → Fed, interest rates, bond yields, inflation
      Query 3 (commodities)→ Oil, gold, dollar, commodity markets

    Use this for global context that impacts Indian markets —
    Fed decisions, risk-on/off sentiment, oil prices.

    Returns:
        Structured dict with ai_summary, prioritized articles, article count.
    """
    try:
        all_articles: List[Dict] = []
        summaries:    List[str]  = []
    
        for tag, query in GLOBAL_QUERIES:
            response = client.search(
                query           = query,
                search_depth    = "advanced",
                topic           = "news",
                max_results     = 6,
                include_domains = GLOBAL_DOMAINS,
                include_answer  = True,
            )

            if response.get("answer"):
                summaries.append(response["answer"])

            formatted = _format_articles(response.get("results", []), tag)
            all_articles.extend(formatted)

        unique = _deduplicate(all_articles)
        
        for a in unique:
            a["score"]    = _score_global(a)
            a["priority"] = _map_priority(a["score"], thresholds=(8, 5))
    
        filtered = [a for a in unique if a["score"] >= 3]
    
        normalized = [
            {
                "title"        : a["title"],
                "source"       : a["source"],
                "published_at" : _to_iso(a["date"]),       # renamed
                "summary"      : a["snippet"],    # renamed
                "priority"     : a["priority"]
            }
            for a in filtered
        ]
    
        final_articles = _get_top5(normalized)

        return {
            "status"     : "success",
            "ai_summary" : summaries[0] if summaries else None,
            "articles"   : final_articles,
        }
    except Exception as e:
        return {
            "status"  : "error",
            "message" : str(e),
        }



# if __name__ == "__main__":
#     import json

#     print("\n" + "═"*60)
#     print("  TEST 1 — Company News")
#     print("═"*60)

#     result = get_company_news(
#         "RELIANCE.NS", limit=5
#     )

#     print(f"  Articles: {len(result.get('articles', []))}")
#     for a in result.get("articles", []):
#         print(f"  - {a['title']}")
#         print(f"    {a['source']} | {a.get('published_at', a.get('date', 'N/A'))}")

#     print("\n" + "═"*60)
#     print("  TEST 2 — Indian Market News")
#     print("═"*60)

#     result = get_indian_market_news()

#     print(f"  Summary  : {result.get('ai_summary', '')[:150]}...")
#     for a in result.get("articles", []):
#         print(f"  [{a['priority'].upper():6}] {a['title']}")
#         print(f"           {a['source']} | {a.get('published_at', a.get('date', 'N/A'))}")

#     print("\n" + "═"*60)
#     print("  TEST 3 — Global Market News")
#     print("═"*60)

#     result = get_global_market_news()

#     print(f"  Summary  : {result.get('ai_summary', '')[:150]}...")
#     for a in result.get("articles", []):
#         print(f"  [{a['priority'].upper():6}] {a['title']}")
#         print(f"           {a['source']} | {a.get('published_at', a.get('date', 'N/A'))}")

#     # Save full output
#     print("\n  Saving full output to news_test_output.json...")

#     with open("check/news/news_test_output.json", "w", encoding="utf-8") as f:
#         json.dump({
#             "company_news": get_company_news(
#                "RELIANCE.NS", limit=5
#             ),
#             "indian_news": get_indian_market_news(),
#             "global_news": get_global_market_news(),
#         }, f, indent=2, ensure_ascii=False)

#     print("  Saved")