# ELITE TRADER - CODE GENERATION INSTRUCTIONS FOR OLEH

## ?? MISSION
Generate production-ready Python code for 12 trading system components using Claude AI.

## ?? OVERVIEW
You have 12 complete prompt specifications that define exactly what code needs to be built.
Each prompt is ready to copy-paste into Claude AI for code generation.

**Timeline:** 2-4 hours total (5-10 minutes per prompt × 12)
**Output:** 12 directories of production-ready, tested code

## ?? QUICK START

1. **Pull the latest:**
   git pull origin main

2. **Pick a prompt (Start with Prompt-01):**
   git checkout feature/prompt-01
   cat scripts/prompts/Prompt-01-Operator-Approval-System.md

3. **Generate Code:**
   - Copy the .md file content
   - Paste into Claude AI
   - Copy Claude's generated code to the ackend/ or rontend/ folders

4. **Test & Push:**
   pytest backend/tests/ -v
   git add .
   git commit -m "feat: Implemented Prompt-01"
   git push origin feature/prompt-01

## ?? RECOMMENDED ORDER
1. Prompt-01: Operator Approval System
2. Prompt-04: Streaming Features
3. Prompt-02: Glass-House Dashboard
4. Prompt-03: Hardware Backtest
5. Prompt-05: Signal Fusion
6. Prompt-06: Incremental Learning
7. Prompt-07: Risk Validation
8. Prompt-08: Position Sizing
9. Prompt-09: Trading Engine
10. Prompt-10: Order Management
11. Prompt-11: Unusual Whales
12. Prompt-12: Monitoring

## ? QUALITY CHECKLIST

After each prompt:
? All files in correct directories
? Tests pass: pytest -v
? No TODO comments
? All imports valid
? Type hints used
? Error handling complete

Good luck! ??
