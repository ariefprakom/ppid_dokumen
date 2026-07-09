from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ppid_dokumen', '0009_cdnfile_external_url'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cdnactivitylog',
            name='action',
            field=models.CharField(
                verbose_name='Aksi',
                max_length=20,
                choices=[
                    ('upload', 'Upload'),
                    ('upload_link', 'Upload Link'),
                    ('rename', 'Rename'),
                    ('delete', 'Hapus'),
                    ('set_jenis', 'Set Jenis Dokumen'),
                ],
            ),
        ),
    ]
