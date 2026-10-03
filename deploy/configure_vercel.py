"""Send server configuration through stdin; never print secret values."""
import os
import secrets
import subprocess
from urllib.parse import quote

from boli_zero.config import ROOT, load_dotenv

load_dotenv()
load_dotenv(ROOT / '.env.hosted')
password = os.environ.get('BOLI_INVITE_PASSWORD')
if not password:
    password = secrets.token_urlsafe(24)
    with (ROOT / '.env.hosted').open('a') as file:
        file.write('\nBOLI_INVITE_PASSWORD=' + password + '\n')
    (ROOT / '.env.hosted').chmod(0o600)
values = {'BOLI_INVITE_PASSWORD': password, 'BOLI_BUDGET_INR': '25', 'BOLI_CLAUDE_BUDGET_USD': '.25'}
# Only sent when set, so re-running this script never lowers a spend figure that was already configured.
for name in ('GNANI_API_KEY', 'GNANI_BASE_URL', 'GNANI_AUTH_HEADER', 'ANTHROPIC_API_KEY', 'BOLI_PRIOR_GNANI_SPEND_INR'):
    if os.environ.get(name):
        values[name] = os.environ[name]
database_password = os.environ.get('DATABASE_PASSWORD')
if database_password and not os.environ.get('DATABASE_URL'):
    # User and host come from the pooler settings of your own Postgres project; none are stored in this repository.
    user, host = os.environ.get('DATABASE_USER'), os.environ.get('DATABASE_HOST')
    if not (user and host):
        raise SystemExit('Set DATABASE_USER and DATABASE_HOST (your Postgres pooler settings) next to DATABASE_PASSWORD in .env.hosted.')
    os.environ['DATABASE_URL'] = f'postgresql://{user}:{quote(database_password, safe="")}@{host}:5432/postgres?sslmode=require'
    # Store connection locally without printing it, for bootstrap and live checks.
    with (ROOT / '.env.hosted').open('a') as file:
        file.write('\nDATABASE_URL=' + os.environ['DATABASE_URL'] + '\n')
if os.environ.get('DATABASE_URL'):
    values['DATABASE_URL'] = os.environ['DATABASE_URL']
for name, value in values.items():
    result = subprocess.run(['npx', '--yes', 'vercel@latest', 'env', 'add', name, 'preview', '--sensitive', '--force', '--yes'],
                            input=value, text=True, capture_output=True, cwd=ROOT)
    if result.returncode:
        raise SystemExit('Could not configure ' + name + '; no secret values were printed.')
    print(name + ': configured', flush=True)
print('Database configured.' if values.get('DATABASE_URL') else 'Database password still required before the conversation service can work.')
