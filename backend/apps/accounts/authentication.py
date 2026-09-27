from rest_framework.authentication import SessionAuthentication as _SessionAuthentication


class SessionAuthentication(_SessionAuthentication):
    """Session auth that keeps DRF's 401 for "no session" instead of 403.

    DRF's stock SessionAuthentication has no `authenticate_header`, so it
    downgrades NotAuthenticated (401) to PermissionDenied (403). This
    project's contract (plan.md section 3) reserves 401 for "no session /
    bad credentials" and 403 for "authenticated but wrong role/state", so
    we restore the standard header instead.
    """

    def authenticate_header(self, request):
        return "Session"
