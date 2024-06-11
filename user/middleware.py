# myapp/middleware.py

from django.utils.deprecation import MiddlewareMixin
import logging
from django.http import HttpResponseNotFound
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

class LogUserAccessMiddleware(MiddlewareMixin):
    def process_request(self, request):
        user = request.user if request.user.is_authenticated else 'Anonymous'
        message = f"{request.method} {request.get_full_path()} by {user}"
        logger.info(message)


class Handle404Middleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if response.status_code == 404 and not request.path.startswith('/RH/'):
            user = request.user if request.user.is_authenticated else 'Anonymous'
            logger.warning(f'404 Not Found: {request.path} by {user}')
            context = {'request_path': request.path}
            content = render_to_string('partials/404.html', context, request)
            return HttpResponseNotFound(content)
        return response