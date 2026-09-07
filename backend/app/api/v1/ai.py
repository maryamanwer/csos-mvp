import httpx
import ollama
from fastapi import APIRouter, Depends
from app.core.security import get_current_user
from app.core.config import settings
router = APIRouter(prefix='/ai', tags=['ai'])
@router.get('/models')
def models(user=Depends(get_current_user)):
    installed = []
    status = 'unavailable'
    if settings.AI_PROVIDER == 'ollama':
        try:
            result = ollama.Client(host=settings.OLLAMA_BASE_URL, timeout=5).list()
            installed = [m['name'] for m in result.get('models', [])]
            status = 'ready'
        except (httpx.HTTPError, ollama.ResponseError, ConnectionError): pass
    return {'provider': settings.AI_PROVIDER, 'status': status, 'default': settings.AI_DEFAULT_MODEL,
            'enabled': list(settings.available_ai_models), 'installed': installed}
