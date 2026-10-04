from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import SavedAddress
from orders.forms import SavedAddressForm


@login_required
def saved_addresses(request):
	form = SavedAddressForm(request.POST or None)
	if request.method == 'POST' and form.is_valid():
		address = form.save(commit=False)
		address.user = request.user
		address.save()
		messages.success(request, 'Your delivery address has been saved.')
		return redirect('accounts:addresses')
	return render(request, 'accounts/addresses.html', {
		'form': form,
		'addresses': request.user.saved_gallery_addresses.all(),
	})


@login_required
@require_POST
def delete_saved_address(request, address_id):
	address = get_object_or_404(SavedAddress, pk=address_id, user=request.user)
	address.delete()
	messages.success(request, 'The saved address has been removed.')
	return redirect('accounts:addresses')
