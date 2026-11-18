import os

from bovinos.wsgi import application


def _bootstrap():
    """Aplica migrações e cria o superusuário inicial no cold start da Vercel.

    A Vercel não executa comandos de deploy para funções Python, então o banco
    é preparado aqui. Ambas as operações são idempotentes.
    """
    if os.environ.get('SKIP_AUTO_MIGRATE', '').lower() == 'true':
        return

    from django.core.management import call_command

    call_command('migrate', interactive=False, verbosity=0)

    username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
    password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
    if username and password:
        from django.contrib.auth import get_user_model

        User = get_user_model()
        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(
                username=username,
                email=os.environ.get('DJANGO_SUPERUSER_EMAIL', ''),
                password=password,
            )


_bootstrap()

app = application
