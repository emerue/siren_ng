"""
One-shot patch script for Tier 1 fixes.
Run from project root: python _apply_patches.py
Then delete both _apply_patches.py and _tasks_patch.py before committing.
"""
import pathlib
import shutil

BASE = pathlib.Path(__file__).parent


def patch_tasks():
    src = BASE / '_tasks_patch.py'
    dst = BASE / 'apps' / 'incidents' / 'tasks.py'
    shutil.copy2(src, dst)
    print(f"[OK] {dst}")


def patch_views():
    path = BASE / 'apps' / 'incidents' / 'views.py'
    src = path.read_text(encoding='utf-8')

    old = '    incident.save()\n    return Response({"status": incident.status})\n\n\n@api_view(["GET"])\n@permission_classes([AllowAny])\ndef list_media'
    new = '    incident.save()\n    from apps.whatsapp.tasks import notify_reporter_resolved\n    notify_reporter_resolved.delay(str(incident.id))\n    return Response({"status": incident.status})\n\n\n@api_view(["GET"])\n@permission_classes([AllowAny])\ndef list_media'

    if 'notify_reporter_resolved' in src:
        print('[SKIP] views.py already patched')
        return

    if old not in src:
        print('[WARN] views.py pattern not found — check manually')
        return

    path.write_text(src.replace(old, new, 1), encoding='utf-8')
    print(f"[OK] {path}")


def patch_admin():
    path = BASE / 'apps' / 'incidents' / 'admin.py'
    src = path.read_text(encoding='utf-8')

    if 'notify_reporter_resolved' in src:
        print('[SKIP] admin.py already patched')
        return

    old = (
        '    def mark_resolved(self, req, qs):\n'
        '        from .tasks import _transition\n'
        '        for incident in qs:\n'
        '            if incident.status != "RESOLVED":\n'
        '                _transition(incident, "RESOLVED", "admin", "Resolved via admin panel")\n'
        '                incident.save()\n'
        '    mark_resolved.short_description = "Mark selected as RESOLVED (with audit log)"'
    )
    new = (
        '    def mark_resolved(self, req, qs):\n'
        '        from .tasks import _transition\n'
        '        from django.utils import timezone\n'
        '        from apps.whatsapp.tasks import notify_reporter_resolved\n'
        '        for incident in qs:\n'
        '            if incident.status != "RESOLVED":\n'
        '                _transition(incident, "RESOLVED", "admin", "Resolved via admin panel")\n'
        '                incident.resolved_at = timezone.now()\n'
        '                incident.save()\n'
        '                notify_reporter_resolved.delay(str(incident.id))\n'
        '    mark_resolved.short_description = "Mark selected as RESOLVED (with audit log)"'
    )

    if old not in src:
        print('[WARN] admin.py pattern not found — check manually')
        return

    path.write_text(src.replace(old, new, 1), encoding='utf-8')
    print(f"[OK] {path}")


if __name__ == '__main__':
    patch_tasks()
    patch_views()
    patch_admin()
    print('\nDone. Delete _apply_patches.py and _tasks_patch.py before committing.')
