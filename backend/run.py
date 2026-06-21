import sys

import uvicorn

# On Windows, psycopg's async driver requires a SelectorEventLoop, but uvicorn
# hardcodes the ProactorEventLoop there; force the loop via main:selector_event_loop.
# On Linux (Railway) the default loop is already selector-based.
_LOOP = "main:selector_event_loop" if sys.platform == "win32" else "auto"


def main() -> None:
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, loop=_LOOP)


if __name__ == "__main__":
    main()
