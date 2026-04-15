from .models import User


def current_user(request):
    user_id = request.session.get("user_id")

    if user_id:
        try:
            user = User.objects.get(id=user_id)
            return {"user": user}
        except User.DoesNotExist:
            pass

    return {"user": None}