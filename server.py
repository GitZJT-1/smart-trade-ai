"""
Foreign Trade Assistant — standalone FastAPI server.

Start:
    python server.py
    python server.py --port 8080

引导逻辑在 trade.bootstrap 中，app factory 在 trade.app 中。
"""

from trade.app import main
from trade.bootstrap import setup

setup()
main()
