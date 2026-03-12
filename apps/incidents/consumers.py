import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


class IncidentConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add('incidents', self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard('incidents', self.channel_name)

    async def incident_update(self, event):
        await self.send(text_data=json.dumps(event))


def broadcast_update(incident):
    """
    Called synchronously from tasks._transition() to push incident
    state to all connected WebSocket clients.
    """
    channel_layer = get_channel_layer()
    payload = {
        'type': 'incident.update',
        'incident_id': str(incident.id),
        'status': incident.status,
        'incident_type': incident.incident_type,
        'severity': incident.severity,
        'zone_name': incident.zone_name,
        'lat': incident.location_lat,
        'lng': incident.location_lng,
        'vouch_count': incident.vouch_count,
        'total_donations_naira': incident.total_donations_naira,
        'resource_count': incident.resources.count() if hasattr(incident, 'resources') else 0,
        'updated_at': incident.updated_at.isoformat() if incident.updated_at else None,
    }
    async_to_sync(channel_layer.group_send)('incidents', payload)
