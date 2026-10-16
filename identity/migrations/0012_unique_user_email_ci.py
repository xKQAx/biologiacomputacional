"""Un correo, una cuenta, sin volver User un modelo propio.

El índice es parcial: varias cuentas sin correo no chocan.
lower() sirve igual en SQLite y en Postgres.
"""

from django.db import migrations

CREATE_INDEX = """
CREATE UNIQUE INDEX IF NOT EXISTS auth_user_email_ci_uniq
ON auth_user (lower(email))
WHERE email <> '';
"""

DROP_INDEX = "DROP INDEX IF EXISTS auth_user_email_ci_uniq;"

NORMALIZE_EMAILS = """
UPDATE auth_user
SET email = lower(trim(email))
WHERE email IS NOT NULL AND email <> '';
"""


class Migration(migrations.Migration):

    dependencies = [
        ("identity", "0011_remove_additionaluserinfo_profile_picture_and_more"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunSQL(NORMALIZE_EMAILS, migrations.RunSQL.noop),
        migrations.RunSQL(CREATE_INDEX, DROP_INDEX),
    ]
