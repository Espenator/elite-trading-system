"""
YouTube Knowledge API — transcript ingestion and extracted algo ideas.
GET /api/v1/youtube-knowledge returns videos and ML features (stub until service is wired).
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def get_youtube_knowledge():
    """
    Return ingested videos and extracted ML features.
    Frontend: YouTube Knowledge page; expects videos[] and features[].
    """
    return {
        "videos": [
            {
                "id": 1,
                "title": "S&P 500 Sector Rotation Strategy",
                "channel": "Trading Alpha",
                "addedAt": "2h ago",
                "concepts": ["sector rotation", "momentum"],
                "ideasCount": 3,
            },
            {
                "id": 2,
                "title": "Options Greeks Explained",
                "channel": "Options Lab",
                "addedAt": "5h ago",
                "concepts": ["delta", "gamma", "IV"],
                "ideasCount": 5,
            },
            {
                "id": 3,
                "title": "Macro Monday: Fed and Rates",
                "channel": "Macro Edge",
                "addedAt": "1d ago",
                "concepts": ["Fed", "rates", "regime"],
                "ideasCount": 2,
            },
        ],
        "features": [
            {"id": 1, "name": "sector_rotation_score", "source": "S&P 500 Sector Rotation Strategy", "addedAt": "2h ago"},
            {"id": 2, "name": "iv_regime_filter", "source": "Options Greeks Explained", "addedAt": "5h ago"},
        ],
    }
