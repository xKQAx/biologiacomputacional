"""Marca las cuentas que desactivó el panel.

El alta pública sigue inactiva sin esta marca, y por eso el correo
de activación no reabre una cuenta cerrada desde Cuentas.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("identity", "0012_unique_user_email_ci"),
    ]

    operations = [
        migrations.AddField(
            model_name="profileadditionalinfo",
            name="suspendida",
            field=models.BooleanField(default=False),
        ),
    ]
