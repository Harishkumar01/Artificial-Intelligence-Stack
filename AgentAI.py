from langchain_community.tools import DuckDuckGoSearchResults
def search_web(query: str) -> str:
    return DuckDuckGoSearchResults(backend="news").run(query)

#import ollama
#llm = "llama3.2"
#stream = ollama.generate(model=llm, prompt='''what is the time?''', stream=True)
#for chunk in stream:
#    print(chunk['response'], end='', flush=True)

tool_search_web = {'type':'function', 'function':{
  'name': 'search_web',
  'description': 'Search the web',
  'parameters': {'type': 'object',
                'required': ['query'],
                'properties': {
                    'query': {'type':'str', 'description':'the topic or subject to search on the web'},
}}}}

print(search_web(query="nvidia"))