from django import forms

from catalog.models import Artwork
from .models import ConsultationRequest, CustomerReview, DesignerInquiry


class CustomerReviewForm(forms.ModelForm):
	website = forms.CharField(required=False, widget=forms.HiddenInput)

	class Meta:
		model = CustomerReview
		fields = ('name', 'city', 'rating', 'title', 'text', 'artwork')
		widgets = {
			'name': forms.TextInput(attrs={'autocomplete': 'name'}),
			'city': forms.TextInput(attrs={'autocomplete': 'address-level2'}),
			'rating': forms.Select(choices=[(rating, f'{rating} / 5') for rating in range(5, 0, -1)]),
			'title': forms.TextInput(attrs={'maxlength': 160}),
			'text': forms.Textarea(attrs={'rows': 4, 'maxlength': 2000}),
			'artwork': forms.Select(),
		}

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['artwork'].queryset = Artwork.objects.order_by('title')
		self.fields['artwork'].required = False
		self.fields['artwork'].empty_label = 'Optional: choose an artwork'

	def clean_website(self):
		value = self.cleaned_data.get('website', '')
		if value:
			raise forms.ValidationError('Unable to submit this review.')
		return value


class ConsultationRequestForm(forms.ModelForm):
	website = forms.CharField(required=False, widget=forms.HiddenInput)

	class Meta:
		model = ConsultationRequest
		fields = ('name', 'phone', 'email', 'message')
		widgets = {
			'name': forms.TextInput(attrs={'autocomplete': 'name'}),
			'phone': forms.TextInput(attrs={'autocomplete': 'tel'}),
			'email': forms.EmailInput(attrs={'autocomplete': 'email'}),
			'message': forms.Textarea(attrs={'rows': 5, 'maxlength': 1500}),
		}

	def clean_website(self):
		value = self.cleaned_data.get('website', '')
		if value:
			raise forms.ValidationError('Unable to submit this request.')
		return value


class DesignerInquiryForm(forms.ModelForm):
	website = forms.CharField(required=False, widget=forms.HiddenInput)

	class Meta:
		model = DesignerInquiry
		fields = ('name', 'company', 'email', 'phone', 'project_type', 'message')
		widgets = {
			'name': forms.TextInput(attrs={'autocomplete': 'name'}),
			'company': forms.TextInput(attrs={'autocomplete': 'organization'}),
			'email': forms.EmailInput(attrs={'autocomplete': 'email'}),
			'phone': forms.TelInput(attrs={'autocomplete': 'tel'}),
			'project_type': forms.TextInput(attrs={'placeholder': 'Residential, hospitality, office...'}),
			'message': forms.Textarea(attrs={'rows': 5, 'maxlength': 3000}),
		}

	def clean_website(self):
		value = self.cleaned_data.get('website', '')
		if value:
			raise forms.ValidationError('Unable to submit this inquiry.')
		return value
