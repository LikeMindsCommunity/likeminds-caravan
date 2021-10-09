from urllib import parse


class UrlUtilities:

    @staticmethod
    def encode_query_url(query):
        return parse.urlencode(query, quote_via=parse.quote)
