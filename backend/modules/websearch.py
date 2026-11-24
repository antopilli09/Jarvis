from ddgs import DDGS


def search_web(query):

    try:

        with DDGS() as ddgs:

            results = list(
                ddgs.text(query, max_results=5)
            )

        return results

    except Exception as e:

        return [{
            "title": "Errore",
            "body": str(e),
            "href": ""
        }]