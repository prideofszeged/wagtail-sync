from wagtail import hooks
from wagtail.admin.menu import MenuItem
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


@hooks.register('register_admin_menu_item')
def register_sync_menu_item():
    return MenuItem(
        _('Sync'),
        reverse('sync:dashboard'),
        icon_name='cog',
        order=900  # This will place it near the end of the menu
    ) 