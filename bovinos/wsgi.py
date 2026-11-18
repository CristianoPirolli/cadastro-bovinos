import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bovinos.settings')

application = get_wsgi_application()

# Na Vercel não há etapa de deploy para rodar comandos: aplica migrações e
# garante o administrador no cold start, qualquer que seja o entrypoint usado.
if os.environ.get('VERCEL'):
    from bovinos.bootstrap import run

    run()
