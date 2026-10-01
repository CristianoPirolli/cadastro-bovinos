# Cadastro Bovino em Django

Aplicação web em Django para cadastro de animais bovinos e controle de vacinas.

## Como executar

1. Instale as dependências:
   ```bash
   pip install django
   ```
2. Crie o banco de dados e execute o servidor de desenvolvimento:
   ```bash
   python manage.py migrate
   python manage.py runserver
   ```

A aplicação permite cadastrar animais com sexo, idade, data de nascimento, número do brinco e número do brinco da mãe. Cada animal pode registrar diversas **pesagens**, informando data e peso em quilogramas; a idade na data da pesagem é calculada automaticamente. O peso aceita ponto ou vírgula como separador decimal. Cada animal também pode ter múltiplas vacinas associadas com nome, data de aplicação e, opcionalmente, uma segunda dose com data correspondente.

Os registros de animais podem ser consultados, editados e removidos, assim como as vacinas associadas a cada um.

A idade é calculada automaticamente a partir da data de nascimento informada e exibida em anos e meses de forma discreta no formulário.
Ao cadastrar vacinas, o campo de nome oferece uma lista pré-definida com imunizações bovinas comuns.

As páginas utilizam Bootstrap responsivo, ajustando-se automaticamente para uso confortável em dispositivos móveis.

## Novidades

- **Login obrigatório**: todas as páginas exigem autenticação. Crie usuários em `/admin/` ou com `python manage.py createsuperuser`.
- **Busca e filtro** por nº do brinco (do animal ou da mãe) e por sexo, com paginação.
- **Resumo** na lista: total de animais, machos, fêmeas e segundas doses futuras.
- **Ganho médio diário (GMD)** e último peso na página do animal.
- **Validações**: brinco único, nascimento não futuro, pesagem não anterior ao nascimento, peso maior que zero.
- Testes: `python manage.py test`.

## Desenvolvimento local

Defina `DEBUG=true` (sem `DATABASE_URL` usa SQLite). Em produção são obrigatórios `SECRET_KEY` e `DATABASE_URL`.
