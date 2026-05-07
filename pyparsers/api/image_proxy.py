from __future__ import annotations

import aiohttp
import logging
from fastapi import HTTPException, Response
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

async def proxy_image_handler(url: str):
    """
    Проксирует изображение по указанному URL.
    """
    if not url:
        raise HTTPException(status_code=400, detail="Missing 'url' parameter")

    async with aiohttp.ClientSession() as session:
        try:
            # Некоторые сайты могут блокировать запросы без User-Agent или с необычным User-Agent
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            }
            
            async with session.get(url, headers=headers, timeout=30) as response:
                if response.status != 200:
                    logger.warning(f"Failed to fetch image from {url}: status {response.status}")
                    raise HTTPException(status_code=response.status, detail=f"Failed to fetch image: source returned {response.status}")
                
                content = await response.read()
                
                # Копируем важные заголовки
                res_headers = {}
                if "Content-Type" in response.headers:
                    res_headers["Content-Type"] = response.headers["Content-Type"]
                if "Cache-Control" in response.headers:
                    res_headers["Cache-Control"] = response.headers["Cache-Control"]
                else:
                    # По умолчанию кэшируем на 30 дней, как в конфиге nginx из документации
                    res_headers["Cache-Control"] = "public, max-age=2592000"
                
                return Response(content=content, headers=res_headers)
                
        except aiohttp.ClientError as e:
            logger.error(f"Network error while proxying image {url}: {e}")
            raise HTTPException(status_code=502, detail=f"Bad Gateway: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error while proxying image {url}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
