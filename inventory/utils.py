from functools import wraps
from django.shortcuts import redirect, render

def permission_required(permission_name):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.session.get('is_logged_in'):
                return redirect('login')
            
            user_role = request.session.get('user_role', '')
            # Admin has all permissions
            if user_role == 'Admin':
                return view_func(request, *args, **kwargs)
            
            user_permissions = request.session.get('user_permissions', [])
            if permission_name in user_permissions:
                return view_func(request, *args, **kwargs)
            else:
                return render(request, 'dashboard.html', {'error': f'You do not have permission to {permission_name.replace("_", " ")}.'})
        return _wrapped_view
    return decorator
