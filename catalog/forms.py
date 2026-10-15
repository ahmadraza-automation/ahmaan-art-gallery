from django import forms

from .models import ArtworkOffer, NotifyRequest, Review

MAX_REVIEW_PHOTO_SIZE = 8 * 1024 * 1024
REVIEW_PHOTO_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
REVIEW_PHOTO_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
REVIEW_PHOTO_FORMATS = {'JPEG', 'PNG', 'WEBP'}


class NotifyRequestForm(forms.ModelForm):
    class Meta:
        model = NotifyRequest
        fields = ('channel', 'email', 'whatsapp')
        widgets = {
            'email': forms.EmailInput(attrs={'autocomplete': 'email'}),
            'whatsapp': forms.TelInput(attrs={'autocomplete': 'tel'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        channel = cleaned_data.get('channel')
        if channel == NotifyRequest.Channel.EMAIL and not cleaned_data.get('email'):
            self.add_error('email', 'Enter an email address for email updates.')
        if channel == NotifyRequest.Channel.WHATSAPP and not cleaned_data.get('whatsapp'):
            self.add_error('whatsapp', 'Enter a WhatsApp number for WhatsApp updates.')
        return cleaned_data


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ('name', 'rating', 'text', 'photo')
        widgets = {
            'name': forms.TextInput(attrs={'autocomplete': 'name'}),
            'rating': forms.Select(choices=[(rating, f'{rating} / 5') for rating in range(5, 0, -1)]),
            'text': forms.Textarea(attrs={'rows': 4, 'maxlength': 2000}),
        }

    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if photo and photo.size > MAX_REVIEW_PHOTO_SIZE:
            raise forms.ValidationError('Review photos must be 8 MB or smaller.')
        if photo:
            extension = photo.name.rsplit('.', 1)[-1].lower() if '.' in photo.name else ''
            image_format = getattr(getattr(photo, 'image', None), 'format', None)
            if extension not in REVIEW_PHOTO_EXTENSIONS or photo.content_type not in REVIEW_PHOTO_TYPES or image_format not in REVIEW_PHOTO_FORMATS:
                raise forms.ValidationError('Upload a JPG, JPEG, PNG, or WebP review photo.')
        return photo


class ArtworkOfferForm(forms.ModelForm):
    website = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = ArtworkOffer
        fields = ('name', 'phone', 'email', 'offer_price')
        widgets = {
            'name': forms.TextInput(attrs={'autocomplete': 'name'}),
            'phone': forms.TelInput(attrs={'autocomplete': 'tel'}),
            'email': forms.EmailInput(attrs={'autocomplete': 'email'}),
            'offer_price': forms.NumberInput(attrs={'min': '0', 'step': '1000'}),
        }

    def clean_website(self):
        value = self.cleaned_data.get('website', '')
        if value:
            raise forms.ValidationError('Unable to submit this offer.')
        return value
