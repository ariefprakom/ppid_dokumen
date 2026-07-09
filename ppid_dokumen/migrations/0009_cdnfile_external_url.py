from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ppid_dokumen', '0008_jenisdokumen_slug'),
    ]

    operations = [
        migrations.AddField(
            model_name='cdnfile',
            name='external_url',
            field=models.URLField(
                verbose_name='URL Eksternal',
                max_length=500,
                blank=True,
                help_text='Isi URL jika dokumen tersimpan di luar CDN (Google Drive, dsb). Kosongkan jika upload file.',
            ),
        ),
    ]
