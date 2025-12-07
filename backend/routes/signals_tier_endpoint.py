
@router.get("/tiers/{tier}/count", response_model=dict)
async def get_tier_count(tier: str):
    """Get count of signals by tier"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM signals WHERE tier = ?", (tier,))
        count = cursor.fetchone()[0]
        return {"tier": tier, "count": count, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    finally:
        conn.close()
