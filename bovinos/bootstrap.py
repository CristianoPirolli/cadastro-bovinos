import os


def run():
    """Aplica migrações e cria o superusuário inicial no cold start da Vercel.

    A Vercel não executa comandos de deploy para funções Python, então o banco
    é preparado aqui. Ambas as operações são idempotentes.
    """
    if os.environ.get('SKIP_AUTO_MIGRATE', '').lower() == 'true':
        return

    from django.core.management import call_command

    call_command('migrate', interactive=False, verbosity=0)

    username = (os.environ.get('DJANGO_SUPERUSER_USERNAME') or '').strip()
    password = (os.environ.get('DJANGO_SUPERUSER_PASSWORD') or '').strip()
    if not (username and password):
        print('[bootstrap] DJANGO_SUPERUSER_USERNAME/PASSWORD não definidos; nenhum admin criado')
        return

    from django.contrib.auth import get_user_model

    User = get_user_model()
    user, created = User.objects.get_or_create(username=username)
    # As variáveis de ambiente são a fonte da verdade para este administrador:
    # se a senha mudar na Vercel, ela é aplicada no próximo deploy.
    if created or not user.check_password(password) or not (user.is_superuser and user.is_active):
        user.is_staff = user.is_superuser = user.is_active = True
        user.set_password(password)
        user.save()
        print(f'[bootstrap] admin "{username}" {"criado" if created else "atualizado"}')
    else:
        print(f'[bootstrap] admin "{username}" já existe e está ok')

