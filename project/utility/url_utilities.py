from urllib import parse


class UrlUtilities:

    @staticmethod
    def encode_query_url(query):
        return parse.urlencode(query, quote_via=parse.quote)

    @staticmethod
    def extract_part_from_url(url, part_name, init_slash_off=False):
        """Extract scheme, netloc, path, query or fragment from url"""
        parsed = parse.urlsplit(url)
        parsed = getattr(parsed, part_name)

        if init_slash_off:
            parsed = parsed[1:]

        return parsed
