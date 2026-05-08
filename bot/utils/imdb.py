"""IMDb lookup utilities. Falls back to a stub if imdbpy is not available."""
import logging
import asyncio

logger = logging.getLogger(__name__)

try:
    import imdb as imdbpy
    _ia = imdbpy.Cinemagoer()
    IMDB_AVAILABLE = True
except Exception:
    IMDB_AVAILABLE = False
    _ia = None
    logger.warning("IMDbPY not available, using stub responses")


STUB_MOVIE = {
    "title": "Sample Movie",
    "year": "2024",
    "rating": "N/A",
    "votes": "N/A",
    "genres": "Drama, Action",
    "director": "Unknown Director",
    "cast": "Actor One, Actor Two, Actor Three",
    "plot": "IMDb is not configured. This is a stub response.",
    "poster": None,
    "url": "https://www.imdb.com",
}


async def search_imdb(query: str, results: int = 5) -> list:
    """Search IMDb and return list of movie info dicts."""
    if not IMDB_AVAILABLE:
        stub = dict(STUB_MOVIE)
        stub["title"] = query.title()
        return [stub]
    loop = asyncio.get_event_loop()
    try:
        movies = await loop.run_in_executor(None, lambda: _ia.search_movie(query))
        if not movies:
            stub = dict(STUB_MOVIE)
            stub["title"] = query.title()
            return [stub]
        out = []
        for m in movies[:results]:
            info = await get_imdb_info(m.movieID)
            out.append(info)
        return out if out else [STUB_MOVIE]
    except Exception as e:
        logger.error("IMDb search error: %s", e)
        return [STUB_MOVIE]


async def get_imdb_info(movie_id: str) -> dict:
    """Fetch full details for a movie ID."""
    if not IMDB_AVAILABLE:
        return STUB_MOVIE
    loop = asyncio.get_event_loop()
    try:
        movie = await loop.run_in_executor(None, lambda: _ia.get_movie(movie_id))
        genres = ", ".join(movie.get("genres", [])[:3]) or "N/A"
        director = ", ".join(str(d) for d in movie.get("directors", [])[:2]) or "N/A"
        cast = ", ".join(str(a) for a in movie.get("cast", [])[:5]) or "N/A"
        poster = movie.get("full-size cover url") or movie.get("cover url")
        rating = str(movie.get("rating", "N/A"))
        votes = str(movie.get("votes", "N/A"))
        return {
            "title": movie.get("title", "Unknown"),
            "year": str(movie.get("year", "N/A")),
            "rating": rating,
            "votes": votes,
            "genres": genres,
            "director": director,
            "cast": cast,
            "plot": (movie.get("plot outline") or movie.get("plot", [""])[0] or "N/A")[:300],
            "poster": poster,
            "url": f"https://www.imdb.com/title/tt{movie_id}/",
        }
    except Exception as e:
        logger.error("IMDb fetch error for %s: %s", movie_id, e)
        return STUB_MOVIE
