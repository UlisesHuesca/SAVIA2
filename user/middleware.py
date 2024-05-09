# myapp/middleware.py

from django.utils.deprecation import MiddlewareMixin
import logging

logger = logging.getLogger(__name__)

class LogUserAccessMiddleware(MiddlewareMixin):
    def process_request(self, request):
        user = request.user if request.user.is_authenticated else 'Anonymous'
        message = f"{request.method} {request.get_full_path()} by {user}"
        logger.info(message)
