from decimal import Decimal


SIZE_MULTIPLIERS = {
	'small': Decimal('0.75'),
	'medium': Decimal('1.00'),
	'large': Decimal('1.50'),
}


def artwork_price(artwork, size):
	if artwork.price is None:
		return None
	return (artwork.price * SIZE_MULTIPLIERS.get(size, Decimal('1.00'))).quantize(Decimal('0.01'))