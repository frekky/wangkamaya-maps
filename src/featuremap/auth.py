""" Allow user objects to have associated API keys, enabling passwordless "login" """

from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django import forms
from django.contrib.auth.decorators import user_passes_test
from django.contrib import auth
from django.utils.translation import gettext as _
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.db import models
from functools import wraps

from .models import UserWithToken

import random, base64, logging


logger = logging.getLogger(__name__)

class TokenWidget(forms.Widget):
    class Media:
        js = ('script/jquery-3.5.1.min.js', 'script/token_widget.js', )
    template_name = 'widgets/token.html'


class UserWithTokenCreationForm(UserCreationForm):
    class Meta:
        model = UserWithToken
        fields = ('username', 'email', 'login_token')
        widgets = {
            'login_token': TokenWidget,
        }

class UserWithTokenChangeForm(UserChangeForm):
    class Meta:
        model = UserWithToken
        fields = ('username', 'email', 'login_token')
        widgets = {
            'login_token': TokenWidget,
        }

class UserWithTokenAdmin(UserAdmin):
    readonly_fields = ('token_login_enabled', 'sample_random_token')
    #fields = ['login_token']
    list_display = ('username', 'token_login_enabled', 'first_name', 'last_name', 'is_staff')
    add_form = UserWithTokenCreationForm
    form = UserWithTokenChangeForm
    model = UserWithToken
    fieldsets = (
        (None, {'fields': ('username', 'password', 'login_token', 'token_login_enabled', 'sample_random_token')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', ),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                # default fields for User
                'username', 'password1', 'password2',
                # extra fields for token login
                'login_token', 'token_login_enabled', 'sample_random_token'
            ),
        }),
    )

    def token_login_enabled(self, instance):
        if instance.login_token:
            login_url = reverse('featuremap:map_login', kwargs={'login_token': instance.login_token})
            return mark_safe(_('<b>Yes</b> (login using token <a href="%s">here</a>)') % login_url)
        return _('No')

    token_login_enabled.short_description = _("Is token-based passwordless login enabled")

    def sample_random_token(self, instance):
        rand_token = base64.b64encode(random.randbytes(36), altchars=b'__').decode('ascii')
        return mark_safe('<code>%s</code>' % rand_token)

    sample_random_token.short_description = _("Random key for pasting into Login Token")


def token_login_view(request, *args, **kwargs):
    token = kwargs.get('login_token', None) or request.headers.get('Authorization', None)
    if token:
        try:
            user = UserWithToken.objects.get(
                login_token__exact = token,
                login_token__isnull = False
            )

            # set user as logged in for the current session
            auth.login(request, user)
            return HttpResponseRedirect(reverse('featuremap:map'))

        except UserWithToken.DoesNotExist:
            logger.error('Bad login token attempt: "%s"' % token)
        except UserWithToken.MultipleObjectsReturned:
            logger.error('Duplicate login_token on UserWithToken objects: "%s"' % token)

    return HttpResponseForbidden()

# decorator for function
def login_or_token_required(view_func):
    decorator = user_passes_test(
        lambda u: u.is_authenticated # or u
    )

    wrapped_view_func = decorator(view_func)

    @wraps(wrapped_view_func)
    def _get_token_wrapped_view_func(request, *args, **kwargs):
        if request.user:
            return wrapped_view_func(request, *args, **kwargs)
        token = kwargs.get('login_token', None) or request.headers.get('Authorization', None)
        if token:
            try:
                user = UserWithToken.objects.get(
                    login_token__exact = token,
                    login_token__isnull = False
                )

                request.user = user
                return wrapped_view_func(request, *args, **kwargs)
            except UserWithToken.DoesNotExist:
                logger.error('Bad login token attempt: "%s"' % token)
            except UserWithToken.MultipleObjectsReturned:
                logger.error('Duplicate login_token on UserWithToken objects: "%s"' % token)

    return _get_token_wrapped_view_func