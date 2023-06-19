from django.contrib import admin
from api.models import User, TagType, WorkType, NotificationType, OurchiveSetting, ContentPage, Tag, Invitation, AttributeType, AttributeValue
from django.contrib.auth.admin import UserAdmin
from django.db import models
from django.forms.widgets import Input
from django.core.mail import send_mail
from django.conf import settings


class RichTextEditorWidget(Input):
    template_name = "admin/rich_text_widget.html"


class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'text', 'display_text', 'tag_type')
    search_fields = ('text', 'tag_type__label')


class AttributeValueAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'display_name', 'attribute_type')
    search_fields = ('name', 'attribute_type__name')


class AttributeTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'display_name', 'allow_on_work', 'allow_on_user', 'allow_on_chapter', 'allow_on_bookmark', 'allow_multiselect')
    search_fields = ('name', 'display_name')


@admin.action(description="Approve selected invitations")
def approve_invitations(modeladmin, request, queryset):
    for invitation in queryset:
        if not invitation.token_used:
            send_mail(
                "Your Ourchive invitation",
                f"Your invite request has been approved. Click this link to register: {settings.API_PROTOCOL}{invitation.register_link}",
                settings.DEFAULT_FROM_EMAIL,
                [invitation.email],
                fail_silently=False,
            )
            invitation.approved = True
            invitation.save()


class InvitationAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'approved', 'join_reason', 'token_expiration', 'token_used')
    search_fields = ('text', 'tag_type__label')
    actions = [approve_invitations]


class ContentPageAdmin(admin.ModelAdmin):
    change_form_template = "admin/rich_text_content_page.html"
    formfield_overrides = {
        models.TextField: {"widget": RichTextEditorWidget},
    }
    readonly_fields = ["id"]
    list_display = ('name', 'id', 'order')


admin.site.register(TagType)
admin.site.register(WorkType)
admin.site.register(NotificationType)
admin.site.register(OurchiveSetting)
admin.site.register(ContentPage, ContentPageAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(Invitation, InvitationAdmin)
admin.site.register(AttributeType, AttributeTypeAdmin)
admin.site.register(AttributeValue, AttributeValueAdmin)
admin.site.register(User, UserAdmin)
