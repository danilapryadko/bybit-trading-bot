# Backup of Fly.io Secrets Configuration
**Date:** 2025-08-15
**Application:** bybit-danila-bot

## Current Secrets (DO NOT COMMIT TO GIT)

```
NAME                     DIGEST           CREATED AT 
BYBIT_API_KEY            7b5ec00b50dc9a81 9h6m ago  
BYBIT_API_SECRET         7b5ec00b50dc9a81 9h6m ago  
BYBIT_MAINNET_API_KEY    3ea15a73ded3d590 4h17m ago 
BYBIT_MAINNET_API_SECRET 2188a18f47e58c4d 4h17m ago 
DATABASE_URL             d6b4dd77a7d3c639 4h33m ago 
TELEGRAM_ALLOWED_USERS   66b2412960aaf960 9h7m ago  
TELEGRAM_BOT_TOKEN       ec92330c30f590e0 9h7m ago  
USE_MAINNET              d8c5ac2e11c8e492 4h0m ago
```

## Notes:
- These secrets need to be copied to the new microservices
- telegram-bot service needs: TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_USERS, DATABASE_URL, BYBIT_* keys
- graphql-api service needs: DATABASE_URL, BYBIT_* keys, USE_MAINNET