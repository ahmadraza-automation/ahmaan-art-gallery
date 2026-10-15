from django import forms
from django.contrib.auth import get_user_model

from .models import ArtworkCategory, ContactInquiry, Order

MAX_PUBLIC_IMAGE_UPLOAD_SIZE = 8 * 1024 * 1024
PUBLIC_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
PUBLIC_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
PUBLIC_IMAGE_FORMATS = {'JPEG', 'PNG', 'WEBP'}


class ContactInquiryForm(forms.ModelForm):
    website = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'honeypot-field', 'tabindex': '-1', 'autocomplete': 'off'}))

    class Meta:
        model = ContactInquiry
        fields = ('name', 'email', 'subject', 'message')
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Your name', 'autocomplete': 'name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'you@example.com', 'autocomplete': 'email'}),
            'subject': forms.TextInput(attrs={'placeholder': 'What would you like to know?'}),
            'message': forms.Textarea(attrs={'placeholder': 'Write your message', 'rows': 5}),
        }


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ('customer_name', 'customer_email', 'customer_phone', 'delivery_address', 'size', 'frame', 'custom_additions')
        widgets = {
            'customer_name': forms.TextInput(attrs={'autocomplete': 'name'}),
            'customer_email': forms.EmailInput(attrs={'autocomplete': 'email'}),
            'customer_phone': forms.TelInput(attrs={'autocomplete': 'tel'}),
            'delivery_address': forms.Textarea(attrs={'autocomplete': 'street-address', 'rows': 3}),
            'custom_additions': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Optional changes or additions'}),
        }


class CommissionRequestForm(forms.ModelForm):
    art_category = forms.ChoiceField(choices=())
    website = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'honeypot-field', 'tabindex': '-1', 'autocomplete': 'off'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['art_category'].choices = [('', 'Select an artwork type')] + list(
            ArtworkCategory.objects.filter(is_active=True).values_list('slug', 'name')
        )

    def clean_client_image(self):
        image = self.cleaned_data.get('client_image')
        if image and image.size > MAX_PUBLIC_IMAGE_UPLOAD_SIZE:
            raise forms.ValidationError('Reference images must be 8 MB or smaller.')
        if image:
            extension = image.name.rsplit('.', 1)[-1].lower() if '.' in image.name else ''
            image_format = getattr(getattr(image, 'image', None), 'format', None)
            if extension not in PUBLIC_IMAGE_EXTENSIONS or image.content_type not in PUBLIC_IMAGE_TYPES or image_format not in PUBLIC_IMAGE_FORMATS:
                raise forms.ValidationError('Upload a JPG, JPEG, PNG, or WebP reference image.')
        return image

    class Meta:
        model = Order
        fields = (
            'customer_name', 'customer_email', 'customer_phone', 'delivery_address',
            'art_category', 'requested_title', 'size', 'frame', 'custom_additions', 'client_image',
        )
        labels = {
            'art_category': 'Type of artwork',
            'requested_title': 'Artwork or idea',
            'client_image': 'Reference image (optional)',
        }
        widgets = {
            'customer_name': forms.TextInput(attrs={'autocomplete': 'name'}),
            'customer_email': forms.EmailInput(attrs={'autocomplete': 'email'}),
            'customer_phone': forms.TelInput(attrs={'autocomplete': 'tel'}),
            'delivery_address': forms.Textarea(attrs={'autocomplete': 'street-address', 'rows': 3}),
            'requested_title': forms.TextInput(attrs={'placeholder': 'What would you like created?'}),
            'custom_additions': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Describe the subject, style, colours, or other details'}),
        }


class CheckoutForm(forms.Form):
    customer_name = forms.CharField(max_length=120, label='Full name', widget=forms.TextInput(attrs={'autocomplete': 'name'}))
    customer_email = forms.EmailField(label='Email', widget=forms.EmailInput(attrs={'autocomplete': 'email'}))
    customer_phone = forms.CharField(max_length=30, label='Phone', widget=forms.TelInput(attrs={'autocomplete': 'tel'}))
    delivery_address = forms.CharField(label='Delivery address', widget=forms.Textarea(attrs={'autocomplete': 'street-address', 'rows': 3}))


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ('first_name', 'last_name', 'email')
        widgets = {
            'first_name': forms.TextInput(attrs={'autocomplete': 'given-name'}),
            'last_name': forms.TextInput(attrs={'autocomplete': 'family-name'}),
            'email': forms.EmailInput(attrs={'autocomplete': 'email'}),
        }