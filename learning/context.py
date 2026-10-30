from .views import role


def ui(request):
    return {"role": role(request.user) if request.user.is_authenticated else None}
