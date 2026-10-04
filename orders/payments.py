from dataclasses import dataclass

from orders.models import Order


@dataclass(frozen=True)
class PaymentInstructions:
	method: str
	label: str
	requires_proof: bool
	account_title: str = ''
	institution: str = ''
	account_number: str = ''
	extra: str = ''
	message: str = ''


class PaymentProvider:
	method = ''
	label = ''
	requires_proof = False

	def instructions(self, site_settings):
		return PaymentInstructions(self.method, self.label, self.requires_proof)


class CashOnDeliveryProvider(PaymentProvider):
	method = Order.PaymentMethod.COD
	label = 'Cash on delivery'

	def instructions(self, site_settings):
		return PaymentInstructions(self.method, self.label, False, message='Pay the courier when your order arrives.')


class BankTransferProvider(PaymentProvider):
	method = Order.PaymentMethod.BANK_TRANSFER
	label = 'Bank transfer'
	requires_proof = True

	def instructions(self, site_settings):
		return PaymentInstructions(
			self.method, self.label, True, site_settings.bank_account_title,
			site_settings.bank_name, site_settings.bank_account_number,
			site_settings.bank_iban, site_settings.payment_instructions,
		)


class JazzCashProvider(PaymentProvider):
	method = Order.PaymentMethod.JAZZCASH
	label = 'JazzCash'
	requires_proof = True

	def instructions(self, site_settings):
		return PaymentInstructions(
			self.method, self.label, True, site_settings.jazzcash_account_title,
			'JazzCash', site_settings.jazzcash_number, '', site_settings.payment_instructions,
		)


class EasypaisaProvider(PaymentProvider):
	method = Order.PaymentMethod.EASYPAISA
	label = 'Easypaisa'
	requires_proof = True

	def instructions(self, site_settings):
		return PaymentInstructions(
			self.method, self.label, True, site_settings.easypaisa_account_title,
			'Easypaisa', site_settings.easypaisa_number, '', site_settings.payment_instructions,
		)


PAYMENT_PROVIDERS = {
	provider.method: provider()
	for provider in (CashOnDeliveryProvider, BankTransferProvider, JazzCashProvider, EasypaisaProvider)
}


def get_payment_provider(method):
	return PAYMENT_PROVIDERS.get(method, PAYMENT_PROVIDERS[Order.PaymentMethod.COD])
