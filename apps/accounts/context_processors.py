from apps.billing.services import get_credit_balance


def credit_balance(request):
    if request.user.is_authenticated and request.user.email:
        return {"current_credit_balance": get_credit_balance(request.user.email)}
    return {"current_credit_balance": None}
