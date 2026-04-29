from langchain_core.messages import HumanMessage
from agents.base_agent import BaseAgent
from tools.news_tools import get_company_news, get_indian_market_news, get_global_market_news

class NewsAnalyst(BaseAgent):
    prompt_path = "prompts/news_analyst_prompt.yaml"
    tools       = [get_company_news, get_indian_market_news, get_global_market_news]

    def run(self , ticker : str):

        messages = [HumanMessage(content=f"Analysize the news for : {ticker}")]
        return self._invoke(messages)
