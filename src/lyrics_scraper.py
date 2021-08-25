import re
import unicodedata
from string import punctuation

from bs4 import BeautifulSoup

excluded_terms = ['track\\s?list', 'album art(work)?', 'liner notes',
                     'booklet', 'credits', 'interview', 'skit',
                     'instrumental', 'setlist']

def url(search_response, track_name):
    """
    Gets the track's URL out of a given search response
    """
    def _clean_str(s):
        punctuation_ = punctuation + "’" + "\u200b"
        string = s.translate(str.maketrans('', '', punctuation_)).strip().lower()
        return unicodedata.normalize("NFKC", string)

    def _result_is_lyrics(result):
        """
        Returns whether or not the result from Genius actually refers to valid song lyrics.
        """
        if (result['lyrics_state'] != 'complete'
                or result.get('instrumental')):
            return False

        expression = r"".join(["({})|".format(term) for term in excluded_terms])
        expression = expression.strip('|')
        regex = re.compile(expression, re.IGNORECASE)
        return not regex.search(_clean_str(result['title']))

    def _get_item_from_search_response(response, track_title, type_, result_type):
        """
        Gets the desired item from the search results.
        """
        # Convert list to dictionary
        top_hits = response['sections'][0]['hits']

        # Check rest of results if top hit wasn't the search type
        sections = sorted(response['sections'],
                          key=lambda sect: sect['type'] == type_)

        hits = [hit for hit in top_hits if hit['type'] == type_]
        hits.extend([hit for section in sections
                     for hit in section['hits']
                     if hit['type'] == type_])

        for hit in hits:
            item = hit['result']
            if _clean_str(item[result_type]) == _clean_str(track_title) and _result_is_lyrics(item):
                return item            

        # If none of the results matched,return None
        return None
        # return hits[0]['result'] if hits else None

    result = _get_item_from_search_response(search_response,
                                            track_name,
                                            type_="song",
                                            result_type="title")
    if result is None:
        return None
    else:
        return result['url']


def lyrics(raw_lyrics_page, remove_section_headers=False, verbose=False):
        """
        Uses BeautifulSoup to scrape song info off of a Genius song HTML page

        """

        # Scrape the song lyrics from the HTML
        html = BeautifulSoup(raw_lyrics_page.replace('<br/>', '\n'), "html.parser")

        # Determine the class of the div
        div = html.find("div", class_=re.compile("^lyrics$|Lyrics__Root"))
        if div is None:
            if verbose:
                print("Couldn't find the lyrics section. "
                      "Please report this if the song has lyrics.\n"
                      "Song: {}".format(html.name))
            return None

        lyrics = div.get_text()

        # Remove unwanted HTML leftovers
        if lyrics.endswith('URLCopyEmbedCopy'):
            lyrics = re.sub(r'\d*EmbedShare|URLCopyEmbedCopy', '', lyrics).strip()

        # Remove [Verse], [Bridge], etc.
        if remove_section_headers:
            lyrics = re.sub(r'(\[.*?\])*', '', lyrics)
            lyrics = re.sub('\n{2}', '\n', lyrics)  # Gaps between verses
        return lyrics.strip("\n")
