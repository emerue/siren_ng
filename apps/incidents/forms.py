from django import forms
from django.core.exceptions import ValidationError

from .models import IncidentMedia

MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB


class CameraFileInput(forms.ClearableFileInput):
    """File input that prompts mobile browsers to offer the rear camera."""

    def __init__(self, attrs=None):
        defaults = {
            'accept': 'image/*,video/*',
            'capture': 'environment',
        }
        if attrs:
            defaults.update(attrs)
        super().__init__(attrs=defaults)


class IncidentMediaAdminForm(forms.ModelForm):
    """
    Inline form for adding media to an incident from the Django admin.

    Supports three workflows:
      1. Upload a file (image or video) -> goes to Supabase Storage
      2. Paste an external URL -> stored directly as public_url
      3. Existing record display (neither field required on edit)

    At least one of upload_file or external_url must be provided on new records.
    """

    upload_file = forms.FileField(
        required=False,
        widget=CameraFileInput,
        label='Upload file',
        help_text='Image or video - max 20 MB. On mobile, tapping this may open the camera.',
    )
    external_url = forms.URLField(
        required=False,
        max_length=1000,
        label='Or paste URL',
        help_text='Direct link to an image or video hosted elsewhere.',
    )
    caption = forms.CharField(
        required=False,
        max_length=500,
        widget=forms.TextInput(attrs={'style': 'width:100%'}),
    )

    class Meta:
        model = IncidentMedia
        fields = ['media_type', 'upload_file', 'external_url', 'caption']

    def clean_upload_file(self):
        f = self.cleaned_data.get('upload_file')
        if f and f.size > MAX_UPLOAD_BYTES:
            raise ValidationError(
                f'File too large ({f.size // (1024*1024)} MB). Maximum is 20 MB.'
            )
        return f

    def clean(self):
        cleaned = super().clean()
        upload_file = cleaned.get('upload_file')
        external_url = cleaned.get('external_url')

        if not self.instance.pk:
            if not upload_file and not external_url:
                raise ValidationError(
                    'Provide either a file upload or an external URL.'
                )

        if upload_file and external_url:
            raise ValidationError(
                'Provide a file upload OR a URL, not both.'
            )

        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)

        upload_file = self.cleaned_data.get('upload_file')
        external_url = self.cleaned_data.get('external_url')
        caption = self.cleaned_data.get('caption', '')

        if upload_file:
            from services.media_service import upload_incident_media
            incident_id = (
                instance.incident_id
                or getattr(instance, '_incident_id_for_save', None)
                or 'pending'
            )
            result = upload_incident_media(upload_file, incident_id)
            instance.public_url   = result['url']
            instance.storage_path = result['storage_path']
            instance.file_size    = result['file_size_kb']
            instance.media_type   = result['media_type']

        elif external_url:
            instance.public_url   = external_url
            instance.storage_path = ''
            instance.file_size    = None
            if not instance.media_type or instance.media_type == 'url':
                ext = external_url.rsplit('.', 1)[-1].lower() if '.' in external_url else ''
                if ext in ('jpg', 'jpeg', 'png', 'webp', 'gif', 'avif'):
                    instance.media_type = 'image'
                elif ext in ('mp4', 'mov', 'webm', 'avi'):
                    instance.media_type = 'video'
                else:
                    instance.media_type = 'url'

        instance.caption = caption

        if commit:
            instance.save()
        return instance
