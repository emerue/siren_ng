"""
All outbound WhatsApp message strings.
Every message the system sends comes through here.
"""
from django.conf import settings

SITE_URL = getattr(settings, 'SITE_URL', 'https://siren.ng')


def received_ack():
    return (
        "Received — verifying now.\n"
        "Usually takes under 90 seconds.\n"
        "I will update you immediately."
    )


def verified_notification(incident):
    type_label = incident.incident_type or 'Incident'
    zone = incident.zone_name or incident.address_text or 'Lagos'
    tracking_url = f"{SITE_URL}/track/{incident.id}"
    return (
        f"✅ VERIFIED — {type_label}, {zone}\n\n"
        f"Severity: {incident.severity}\n\n"
        f"👤 Community responder notified\n"
        f"🏥 Nearest clinic alerted\n\n"
        f"Track and support this incident:\n"
        f"{tracking_url}\n\n"
        f"Are you safe? Reply SAFE or HELP"
    )


def rejected_notification(reason):
    msg = (
        "Your report could not be verified as an emergency.\n\n"
    )
    if reason:
        msg += f"Reason: {reason}\n\n"
    msg += (
        "If you believe this is wrong, send a new message with more details.\n"
        "For life-threatening emergencies, call 767 (Lagos State Emergency)."
    )
    return msg


def verifying_notification(incident):
    tracking_url = f"{SITE_URL}/track/{incident.id}"
    return (
        f"Your report is being reviewed by the community.\n\n"
        f"We need a few more details or vouches to verify it.\n"
        f"We will update you immediately.\n\n"
        f"Track status: {tracking_url}"
    )


def resolution_closure(incident):
    zone = incident.zone_name or incident.address_text or 'the scene'
    type_label = incident.incident_type or 'Incident'
    naira = incident.total_donations_naira
    return (
        f"✅ RESOLVED — {type_label} contained, {zone}\n\n"
        f"Community raised ₦{naira:,.0f} for those affected.\n\n"
        f"Your report helped coordinate this response. Thank you."
    )


def responder_notification(responder, incident, distance_km):
    type_label = incident.incident_type or 'Incident'
    location = incident.address_text or incident.zone_name or 'Nearby'
    dist_str = f"{distance_km:.0f}m" if distance_km < 1 else f"{distance_km:.1f}km"
    return (
        f"🚨 INCIDENT NEAR YOU\n\n"
        f"{type_label}\n"
        f"{dist_str} from you — {location}\n\n"
        f"Your skills are needed.\n"
        f"Will you respond?\n\n"
        f"Reply YES or NO\n"
        f"(3 minutes to accept)"
    )


def responder_directions(responder, incident):
    location = incident.address_text or incident.zone_name or 'the scene'
    maps_url = ""
    if incident.location_lat and incident.location_lng:
        maps_url = f"\nMaps: https://maps.google.com/?q={incident.location_lat},{incident.location_lng}"
    return (
        f"Thank you {responder.name}.\n\n"
        f"Head to {location}{maps_url}\n\n"
        f"You are the nearest responder.\n\n"
        f"Reply ONSCENE when you arrive\n"
        f"Reply HELP if you need backup"
    )


def responder_onscene_ack(responder, incident):
    naira = incident.total_donations_naira
    return (
        f"✅ Logged — {responder.name} on scene.\n\n"
        f"Community has raised ₦{naira:,.0f} in responder appreciation.\n"
        f"Reply DONE when finished."
    )


def responder_done_ack(incident):
    naira = incident.total_donations_naira
    tracking_url = f"{SITE_URL}/track/{incident.id}"
    return (
        f"✅ Thank you for responding.\n\n"
        f"Community raised ₦{naira:,.0f} for this incident.\n\n"
        f"Full incident summary:\n{tracking_url}"
    )


def org_notification(org, incident, distance_km):
    type_label = incident.incident_type or 'Incident'
    location = incident.address_text or incident.zone_name or 'Nearby'
    dist_str = f"{distance_km:.0f}m" if distance_km < 1 else f"{distance_km:.1f}km"
    return (
        f"🔴 VERIFIED INCIDENT NEARBY\n\n"
        f"{type_label}\n"
        f"{dist_str} from your location — {location}\n\n"
        f"Can you receive?\n\n"
        f"Reply ACCEPT — capacity available\n"
        f"Reply DECLINE — cannot receive now\n"
        f"Reply CALL — need more information"
    )


def org_accept_ack(org, incident):
    naira = incident.total_donations_naira
    return (
        f"✅ Logged — {org.name} accepting.\n\n"
        f"Responder on scene directed to your location.\n"
        f"Community raised ₦{naira:,.0f} for victim relief.\n"
        f"Update us if capacity changes."
    )


def subscription_alert(subscription, incident, distance_km):
    type_label = incident.incident_type or 'Incident'
    location = incident.address_text or incident.zone_name or 'Nearby'
    dist_str = f"{distance_km:.1f}km" if distance_km >= 0.1 else f"{int(distance_km*1000)}m"
    tracking_url = f"{SITE_URL}/track/{incident.id}"
    return (
        f"🔴 SIREN ALERT — {subscription.label}\n\n"
        f"{type_label}\n"
        f"Severity: {incident.severity}\n"
        f"Location: {location}\n"
        f"Distance from {subscription.label}: {dist_str}\n\n"
        f"Community is responding.\n"
        f"People are contributing resources.\n\n"
        f"Full details and support options:\n"
        f"{tracking_url}\n\n"
        f"Reply STOP {subscription.label} to pause alerts for this location."
    )


def subscription_saved(label, location_type, radius_km):
    type_display = {
        'HOME': 'Home', 'SCHOOL': 'School/Child location',
        'LAND': 'Land/Property', 'OFFICE': 'Office',
        'FAMILY': 'Family member location', 'OTHER': 'Other',
    }.get(location_type, location_type)
    radius_display = f"{int(radius_km * 1000)}m" if radius_km < 1 else f"{radius_km:.0f}km"
    return (
        f"✅ Saved — {label} ({type_display})\n\n"
        f"I will alert you when a verified incident happens within {radius_display}.\n\n"
        f"To see all your saved locations: reply MY ALERTS\n"
        f"To save another location: reply WATCH\n"
        f"To stop alerts for this location: reply STOP {label}"
    )


def vouch_confirmed(incident):
    tracking_url = f"{SITE_URL}/track/{incident.id}"
    return (
        f"✅ Your vouch has been counted for this incident.\n\n"
        f"See the live update: {tracking_url}"
    )


def donation_thank_you(donor_name, amount_naira, fund_choice, incident):
    fund_display = {
        'VICTIM': 'Victim Relief',
        'RESPONDER': 'First Responder Appreciation',
        'PLATFORM': 'Emergency Response Fund',
    }.get(fund_choice, fund_choice)
    tracking_url = f"{SITE_URL}/track/{incident.id}"
    name_str = f" {donor_name}" if donor_name else ""
    return (
        f"✅ Thank you{name_str}. Your ₦{amount_naira:,.0f} donation to {fund_display} "
        f"has been received.\n\n"
        f"{tracking_url}"
    )


def resource_board_summary(incident, resources):
    tracking_url = f"{SITE_URL}/track/{incident.id}"
    if not resources:
        return (
            f"There is an active incident near you.\n\n"
            f"See full details and help coordinate:\n"
            f"{tracking_url}"
        )
    lines = ["There is an active incident near you.\n\nPeople are coordinating resources:"]
    icons = {
        'TRANSPORT': '🚗', 'EQUIPMENT': '🪜', 'MEDICAL': '💊',
        'FOOD_WATER': '🍶', 'MANPOWER': '👐', 'OTHER': '📦',
    }
    for r in resources[:3]:
        icon = icons.get(r.get('category', ''), '📦')
        label = r.get('label', '')
        st = r.get('status', 'NEEDED')
        lines.append(f"{icon} {label} — {st}")
    lines.append(f"\nTo see the full board and contribute:\n{tracking_url}")
    return "\n".join(lines)


# ── WATCH flow prompts ─────────────────────────────────────────────────────────

def watch_ask_label():
    return (
        "I will alert you when emergencies happen near locations you care about.\n\n"
        "What do you want to call this location?\n"
        "Examples: My house, Timi school, Ogun land, Mama's compound"
    )


def watch_ask_type(label):
    return (
        f"What type of location is '{label}'?\n\n"
        "Reply with a number:\n"
        "1. Home\n"
        "2. School / Child location\n"
        "3. Land / Property\n"
        "4. Office\n"
        "5. Family member location\n"
        "6. Other"
    )


def watch_ask_location(label):
    return (
        f"Now share the location of {label}.\n\n"
        "Tap the paperclip icon in WhatsApp,\n"
        "select Location, then share it here."
    )


def watch_ask_radius():
    return (
        "How far away should an incident be to alert you?\n\n"
        "1. 500 metres\n"
        "2. 1 km\n"
        "3. 2 km\n"
        "4. 5 km"
    )


def show_subscriptions_message(subscriptions):
    if not subscriptions:
        return (
            "You have no saved locations.\n\n"
            "Reply WATCH to save a location and get alerts."
        )
    lines = ["Your saved locations:\n"]
    for i, sub in enumerate(subscriptions, 1):
        status = "✅ Active" if sub.is_active else "⏸ Paused"
        lines.append(f"{i}. {sub.label} — {status} ({sub.alert_radius_km}km radius)")
    lines.append("\nTo stop alerts: reply STOP [location name]")
    lines.append("To add a new location: reply WATCH")
    return "\n".join(lines)


def stop_confirmed(label):
    return (
        f"✅ Alerts paused for '{label}'.\n\n"
        "Reply WATCH to save a new location.\n"
        "Reply MY ALERTS to see all your locations."
    )


def stop_not_found(label):
    return (
        f"No saved location found with the name '{label}'.\n\n"
        "Reply MY ALERTS to see your saved locations."
    )


def registration_instructions(reg_type):
    if reg_type == 'responder':
        return (
            "To register as a community responder:\n\n"
            "Visit siren.ng/join or reply with:\n"
            "Your full name, skill (MEDICAL/FIRE/WATER/STRUCTURAL/ELECTRICAL/FIRST_AID), "
            "and your area.\n\n"
            "Example: John Adeyemi | MEDICAL | Surulere\n\n"
            "All responders are manually verified before activation."
        )
    return (
        "To register your organisation:\n\n"
        "Visit siren.ng/join or reply with:\n"
        "Organisation name, type (HOSPITAL/AMBULANCE/PHARMACY/etc), and address.\n\n"
        "We will contact you within 24 hours."
    )


def commute_type_question():
    return (
        "Saved! Is this a single location or your daily commute?\n\n"
        "Reply POINT to finish here\n"
        "Reply COMMUTE to also set up your commute route"
    )


def commute_setup_home_prompt():
    return (
        "Commute Shield monitors the route between your home and office "
        "during morning and evening peak hours.\n\n"
        "Share your HOME location first."
    )


def commute_setup_office_prompt():
    return "Got it. Now share your OFFICE location."


def commute_shield_saved(sub):
    return (
        f"✅ Commute Shield is active — {sub.label}\n\n"
        f"I will alert you when a verified incident (wire down, accident, flood) "
        f"falls within {sub.commute_buffer_km}km of your route "
        f"between 6-10am and 4-8pm.\n\n"
        f"You will also get a route briefing every morning at 6:30am.\n\n"
        f"Reply MY COMMUTE any time for today's status."
    )


def my_impact_link(phone_hash):
    return (
        f"See your full community impact, safety scores, and trend charts:\n\n"
        f"{SITE_URL}/my-impact?phone_hash={phone_hash}"
    )


def guardian_closure(incident, sub):
    return (
        f"Update on {sub.label} area:\n\n"
        f"The {incident.incident_type} has been resolved.\n"
        f"{incident.donation_count} community members donated.\n\n"
        f"Your watch on this location helps keep Lagos safe.\n\n"
        f"See your impact: {SITE_URL}/my-impact"
    )


# -- v5 Commute Shield templates -----------------------------------------------

def commute_type_question():
    return (
        "Is this a single location or do you also want to monitor\n"
        "your daily commute (Home to Office)?\n\n"
        "Reply POINT to finish here\n"
        "Reply COMMUTE to also set up your commute route"
    )


def commute_setup_home_prompt():
    return (
        "Commute Shield monitors the route between your home and office\n"
        "during morning and evening peak hours.\n\n"
        "Share your HOME location first."
    )


def commute_setup_office_prompt():
    return "Got it. Now share your OFFICE location."


def commute_shield_saved(sub):
    return (
        f"Commute Shield is active.\n\n"
        f"I will alert you when a verified incident (wire down, accident, flood)\n"
        f"falls within {sub.commute_buffer_km}km of your {sub.label} corridor\n"
        f"between 6-10am and 4-8pm.\n\n"
        f"You will also get a route briefing every morning at 6:30am.\n\n"
        f"Reply MY COMMUTE any time for today's status.\n"
        f"Reply STOP COMMUTE to pause."
    )


def commute_shield_alert(incident, sub, distance_km):
    type_labels = {
        'RTA': 'Road Accident', 'HAZARD': 'Downed wire / road hazard',
        'FLOOD': 'Flooding', 'FIRE': 'Fire', 'EXPLOSION': 'Explosion',
        'COLLAPSE': 'Building Collapse', 'DROWNING': 'Drowning',
    }
    tracking_url = f"{SITE_URL}/track/{incident.id}"
    return (
        f"COMMUTE SHIELD -- {type_labels.get(incident.incident_type, incident.incident_type)}"
        f" on your route\n\n"
        f"{incident.address_text or incident.zone_name}\n"
        f"Severity: {incident.severity}\n"
        f"Distance from your corridor: {distance_km:.1f}km\n\n"
        f"Reply NEED RIDE to connect with people offering transport.\n\n"
        f"Full update: {tracking_url}"
    )


def guardian_closure(incident, sub):
    zone = incident.zone_name or incident.address_text or 'the area'
    type_label = incident.incident_type or 'Incident'
    naira = incident.total_donations_naira
    return (
        f"Update on {sub.label} area:\n\n"
        f"The {type_label} at {zone} has been resolved.\n"
        f"Community contributed \u20a6{naira:,.0f}.\n\n"
        f"Your watch on this location was part of what made this possible.\n\n"
        f"See your full impact: siren.ng/my-impact"
    )


def my_impact_link(phone_hash):
    return (
        f"See your full community impact:\n\n"
        f"{SITE_URL}/my-impact?phone_hash={phone_hash}"
    )
