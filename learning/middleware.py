from django.shortcuts import redirect


class ForcePasswordChangeMiddleware:
    """Пока пользователь не сменил временный пароль — пускаем только на страницу смены пароля."""
    ALLOWED = ("/password-change/", "/logout/", "/i18n/", "/static/", "/media/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        u = request.user
        if u.is_authenticated and not u.is_superuser and getattr(getattr(u, "profile", None), "must_change_password", False):
            if not request.path.startswith(self.ALLOWED):
                return redirect("password_change")
        return self.get_response(request)
