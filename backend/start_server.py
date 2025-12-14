#!/usr/bin/env python
"""
Start the Elite Trading System backend server.

Usage:
    python start_server.py          # Development mode with auto-reload
    python start_server.py --prod   # Production mode
"""
import argparse
import uvicorn


def main():
    parser = argparse.ArgumentParser(description="Start Elite Trading System API server")
    parser.add_argument(
        "--prod", 
        action="store_true", 
        help="Run in production mode (no auto-reload)"
    )
    parser.add_argument(
        "--host", 
        default="0.0.0.0", 
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=8000, 
        help="Port to bind to (default: 8000)"
    )
    
    args = parser.parse_args()
    is_dev = not args.prod
    
    print("=" * 50)
    print("  Elite Trading System API Server")
    print("=" * 50)
    print(f"  Host: {args.host}")
    print(f"  Port: {args.port}")
    print(f"  Mode: {'Production' if args.prod else 'Development'}")
    print(f"  Docs: http://localhost:{args.port}/docs")
    print(f"  WebSocket: ws://localhost:{args.port}/ws")
    print("=" * 50)
    
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=is_dev,
        log_level="info"
    )


if __name__ == "__main__":
    main()
