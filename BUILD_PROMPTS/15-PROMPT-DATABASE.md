# PROMPT 15: DATABASE ARCHITECTURE AND PERSISTENCE
## Historical Data and Analysis

Store all trades, signals, patterns for analysis and learning.

REQUIREMENTS:
1. PostgreSQL schema
2. Tables: trades, signals, positions, patterns, approvals
3. Indexes on critical fields
4. Migration scripts
5. Repository pattern for data access
6. Transaction handling

DELIVERABLES: database_service.py, schema.sql, migrations folder, repository.py

Copy to Claude and ask: "Please write complete, production-ready code. Include ALL files, ALL functions, ALL imports. No TODOs."
