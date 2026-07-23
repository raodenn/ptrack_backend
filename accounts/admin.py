from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser
from .forms import CustomUserCreationForm, CustomUserChangeForm
class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser

    list_display = ['email', 'username', 'birthday', 'phone_number', 'is_staff', 'is_active']
    list_filter = ['email', 'is_staff', 'is_active']

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'birthday', 'phone_number', 'password1', 'password2', 'is_staff', 'is_active')}
        ),
    )
    fieldsets = (
        (None, {'fields': ('email', 'username', 'birthday', 'phone_number', 'password')}),
        ('Permissions', {'fields': ('is_staff', 'is_active')}),
    )

    search_fields = ('email','username')
    ordering = ('email','username')

admin.site.register(CustomUser, CustomUserAdmin)

