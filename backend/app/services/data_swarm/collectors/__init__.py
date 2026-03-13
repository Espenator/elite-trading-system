"""Data swarm collectors — Alpaca, Unusual Whales, FinViz Elite."""

from app.services.data_swarm.collectors.base_collector import BaseCollector
from app.services.data_swarm.collectors.alpaca_stream import AlpacaStreamCollector
from app.services.data_swarm.collectors.alpaca_rest import AlpacaRestCollector
from app.services.data_swarm.collectors.alpaca_futures import AlpacaFuturesCollector
from app.services.data_swarm.collectors.uw_websocket import UWWebSocketCollector
from app.services.data_swarm.collectors.uw_rest import UWRestCollector
from app.services.data_swarm.collectors.uw_flow import UWFlowCollector
from app.services.data_swarm.collectors.finviz_screener import FinvizScreenerCollector
from app.services.data_swarm.collectors.finviz_futures import FinvizFuturesCollector

COLLECTOR_REGISTRY = {
    "alpaca_stream": AlpacaStreamCollector,
    "alpaca_rest": AlpacaRestCollector,
    "alpaca_futures": AlpacaFuturesCollector,
    "uw_websocket": UWWebSocketCollector,
    "uw_rest": UWRestCollector,
    "uw_flow": UWFlowCollector,
    "finviz_screener": FinvizScreenerCollector,
    "finviz_futures": FinvizFuturesCollector,
}

__all__ = [
    "BaseCollector",
    "AlpacaStreamCollector",
    "AlpacaRestCollector",
    "AlpacaFuturesCollector",
    "UWWebSocketCollector",
    "UWRestCollector",
    "UWFlowCollector",
    "FinvizScreenerCollector",
    "FinvizFuturesCollector",
    "COLLECTOR_REGISTRY",
]
