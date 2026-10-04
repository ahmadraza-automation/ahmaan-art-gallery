from django import forms

from accounts.models import SavedAddress
from orders.models import GiftCard, Order


class CheckoutForm(forms.Form):
	customer_name = forms.CharField(max_length=140, label='Full name', widget=forms.TextInput(attrs={'autocomplete': 'name'}))
	customer_email = forms.EmailField(label='Email', widget=forms.EmailInput(attrs={'autocomplete': 'email'}))
	customer_phone = forms.CharField(max_length=32, label='Phone', widget=forms.TelInput(attrs={'autocomplete': 'tel'}))
	delivery_address = forms.CharField(label='Address', widget=forms.Textarea(attrs={'autocomplete': 'street-address', 'rows': 3}))
	city = forms.CharField(max_length=100, label='City')
	payment_method = forms.ChoiceField(choices=Order.PaymentMethod.choices, widget=forms.RadioSelect, initial=Order.PaymentMethod.COD)
	coupon_code = forms.CharField(max_length=40, required=False, label='Discount code')
	gift_card_code = forms.CharField(max_length=40, required=False, label='Gift card code')
	customer_note = forms.CharField(max_length=1000, required=False, label='Order note', widget=forms.Textarea(attrs={'rows': 3}))
	payment_proof = forms.ImageField(required=False, label='Payment screenshot', help_text='JPEG, PNG or WebP; maximum 5 MB.')

	def __init__(self, *args, user=None, payment_choices=None, **kwargs):
		super().__init__(*args, **kwargs)
		self.user = user
		if payment_choices is not None:
			self.fields['payment_method'].choices = payment_choices
		self.fields['saved_address'] = forms.ChoiceField(required=False, label='Use a saved address', choices=[('', 'Enter a new address')])
		if user and user.is_authenticated:
			self.fields['saved_address'].choices += [
				(str(address.pk), f'{address.label} · {address.city}')
				for address in SavedAddress.objects.filter(user=user)
			]
		else:
			self.fields.pop('saved_address')

	def clean_coupon_code(self):
		return self.cleaned_data['coupon_code'].strip().upper()

	def clean_gift_card_code(self):
		return self.cleaned_data['gift_card_code'].strip().upper()

	def clean_payment_proof(self):
		proof = self.cleaned_data.get('payment_proof')
		if not proof:
			return proof
		if proof.size > 5 * 1024 * 1024:
			raise forms.ValidationError('Payment screenshots must be 5 MB or smaller.')
		if proof.content_type not in ('image/jpeg', 'image/png', 'image/webp'):
			raise forms.ValidationError('Upload a JPEG, PNG, or WebP screenshot.')
		return proof

	def clean(self):
		cleaned_data = super().clean()
		method = cleaned_data.get('payment_method')
		if method in (Order.PaymentMethod.BANK_TRANSFER, Order.PaymentMethod.JAZZCASH, Order.PaymentMethod.EASYPAISA) and not cleaned_data.get('payment_proof'):
			self.add_error('payment_proof', 'Upload your payment screenshot to continue.')
		return cleaned_data


class OrderTrackingForm(forms.Form):
	order_id = forms.CharField(max_length=24, label='Order ID')
	phone = forms.CharField(max_length=32, label='Phone number', widget=forms.TelInput(attrs={'autocomplete': 'tel'}))


class SavedAddressForm(forms.ModelForm):
	class Meta:
		model = SavedAddress
		fields = ('label', 'recipient_name', 'phone', 'address_line1', 'address_line2', 'city', 'postal_code', 'is_default')


class GiftCardRequestForm(forms.ModelForm):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['recipient_email'].required = True

	class Meta:
		model = GiftCard
		fields = ('amount', 'recipient_name', 'recipient_email', 'message')
		widgets = {
			'recipient_name': forms.TextInput(attrs={'autocomplete': 'name'}),
			'recipient_email': forms.EmailInput(attrs={'autocomplete': 'email'}),
			'message': forms.Textarea(attrs={'rows': 3, 'maxlength': 280}),
		}