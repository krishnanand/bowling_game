# Generated by Django 2.0.6 on 2018-07-17 13:33

import django.core.validators
from django.db import migrations, models
import functools
import game.models


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gameregistration',
            name='game_id',
            field=models.CharField(default=functools.partial(game.models.random_string, *(), **{'char_length': 16}), help_text='Unique bowling game id', max_length=16, primary_key=True, serialize=False, validators=[django.core.validators.MinLengthValidator(16)]),
        ),
        migrations.AlterField(
            model_name='scoreperframe',
            name='frame_version',
            field=models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)]),
        ),
    ]
