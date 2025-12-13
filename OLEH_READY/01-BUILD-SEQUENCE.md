# BUILD SEQUENCE GUIDE FOR OLEH
## Step-by-Step Saturday-Sunday Build Instructions

Total Build Time: 15-18 hours
Start: Saturday 9:00 AM
End: Sunday 8:00 PM
Go Live: Monday 2:00 PM

## HOW TO USE THE PROMPTS

For EACH prompt:
1. Open the prompt file from /BUILD_PROMPTS/
2. Copy ENTIRE text (do not edit)
3. Paste into Claude Opus 4.5 new chat
4. Say: "Please write complete, production-ready code. Include ALL files, ALL functions, ALL imports. No TODOs, no placeholders."
5. Wait: Claude completes in 5-10 minutes
6. Copy ALL files Claude provides
7. Save to directories per system architecture
8. Git commit with message
9. Move to next prompt

## SATURDAY BUILD SEQUENCE

9:00 AM - Prompts 1, 2, 3 (PARALLEL)
- Open 3 separate Claude conversations
- Prompt 1 to /backend/app/core/
- Prompt 2 to /frontend/src/
- Prompt 3 to /backend/app/core/
- Merge all code by 12 PM

1:00 PM - Prompts 4, 5, 6 (PARALLEL)
- Open 3 separate Claude conversations
- All go to /backend/app/services/
- Merge all code by 4 PM

5:00 PM - Prompts 7, 8, 8B (SEQUENTIAL)
- Prompt 7 (risk validation)
- Prompt 8 (sizing) depends on 7
- Prompt 8B (trailing stops) depends on 8
- Done by 8 PM

## SUNDAY BUILD SEQUENCE

9:00 AM - Prompts 9, 10 (SEQUENTIAL)
- Prompt 9 (Alpaca trading engine)
- Prompt 10 (order manager) depends on 9

12:00 PM - Prompts 11, 12, 13, 14, 15 (PARALLEL)
- Open 5 separate Claude conversations
- All complete by 3 PM

3:00 PM - 5:00 PM
- Code review and integration testing
- Verify all 15 connected

5:00 PM - 8:00 PM
- Deploy to paper trading
- Ready for live Monday

Build it. ROCKET
