from django.db import migrations, models
from django.utils.text import slugify


def generate_slugs(apps, schema_editor):
    """Generate slug dari nama untuk record yang sudah ada."""
    JenisDokumen = apps.get_model('ppid_dokumen', 'JenisDokumen')
    for obj in JenisDokumen.objects.all():
        obj.slug = slugify(obj.nama)
        obj.save(update_fields=['slug'])


class Migration(migrations.Migration):

    dependencies = [
        ('ppid_dokumen', '0007_alter_cdnfile_file_path'),
    ]

    operations = [
        # Step 1: Add slug field (nullable, no unique)
        migrations.AddField(
            model_name='jenisdokumen',
            name='slug',
            field=models.SlugField(
                verbose_name='Slug URL',
                max_length=100,
                default='',
                help_text='URL-friendly identifier, contoh: wajib-berkala. Otomatis di-generate jika kosong.',
            ),
            preserve_default=False,
        ),
        # Step 2: Populate slugs
        migrations.RunPython(generate_slugs, migrations.RunPython.noop),
        # Step 3: Make unique
        migrations.AlterField(
            model_name='jenisdokumen',
            name='slug',
            field=models.SlugField(
                verbose_name='Slug URL',
                max_length=100,
                unique=True,
                default='',
                help_text='URL-friendly identifier, contoh: wajib-berkala. Otomatis di-generate jika kosong.',
            ),
        ),
    ]
