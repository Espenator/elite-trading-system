import json
import asyncio
from typing import Dict, Any

class ApexOrchestrator:
    def __init__(self, llm_client, redis_pubsub):
        self.llm = llm_client
        self.redis = redis_pubsub

    async def generate_tot_hypotheses(self, macro_data: str) -> str:
        """Step 1: Generate 3 divergent market theories."""
        prompt = f"""
You are a quantitative macro strategist. Analyze this live data stream: {macro_data}
Generate 3 distinct, divergent theories for the current market regime.
Format strictly as:
THEORY 1 (Bullish/Reversal): [Your logic]
THEORY 2 (Bearish/Capitulation): [Your logic]
THEORY 3 (Noise/Chop): [Your logic]
"""
        return await self.llm.generate(prompt)

    async def evaluate_tot_hypotheses(self, macro_data: str, theories: str) -> Dict[str, Any]:
        """Step 2: Act as the judge and output the final JSON regime."""
        prompt = f"""
You are the Chief Risk Officer. Review the live data: {macro_data}
Review the 3 proposed theories: {theories}
Critique the theories mathematically against the data. Select the highest probability regime.
You must output ONLY valid JSON matching this schema:
{{
"Market_Regime": "string", "Directional_Bias": "string", "Conviction": int_1_to_100, "Winning_Theory": "string"
}}
"""
        response = await self.llm.generate(prompt)
        try:
            return json.loads(response[response.find("{"):response.rfind("}")+1])
        except json.JSONDecodeError:
            return {"Market_Regime": "Unknown", "Directional_Bias": "Neutral", "Conviction": 0}

    async def process_market_cycle(self, incoming_redis_payload: str):
        """Main loop triggered by Redis bridge."""
        theories = await self.generate_tot_hypotheses(incoming_redis_payload)
        final_regime = await self.evaluate_tot_hypotheses(incoming_redis_payload, theories)
        await self.redis.publish("channel_swarm_ops", json.dumps(final_regime))
        return final_regime