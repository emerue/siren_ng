from django.db import connection


def haversine_query(table, lat_field, lng_field, incident_lat, incident_lng,
                    radius_km, extra_filters='', extra_params=None, limit=10):
    """
    Returns rows from `table` within radius_km of (incident_lat, incident_lng).
    Ordered by distance ascending (nearest first).

    Args:
        table:          database table name e.g. 'responders_responder'
        lat_field:      latitude column name e.g. 'home_lat'
        lng_field:      longitude column name e.g. 'home_lng'
        incident_lat:   float latitude of the reference point
        incident_lng:   float longitude of the reference point
        radius_km:      maximum distance in kilometres
        extra_filters:  additional SQL e.g. "AND status = 'VERIFIED'"
        extra_params:   list of params for extra_filters placeholders
        limit:          max number of results

    Returns:
        List of dicts. Each dict has all table columns plus 'distance_km'.
    """
    base_params = [incident_lat, incident_lng, incident_lat]
    filter_params = extra_params or []
    params = base_params + filter_params + [radius_km]

    sql = f"""
        SELECT *,
          (6371 * acos(
            LEAST(1.0,
              cos(radians(%s)) * cos(radians({lat_field})) *
              cos(radians({lng_field}) - radians(%s)) +
              sin(radians(%s)) * sin(radians({lat_field}))
            )
          )) AS distance_km
        FROM {table}
        WHERE (1=1) {extra_filters}
        HAVING distance_km <= %s
        ORDER BY distance_km ASC
        LIMIT {limit}
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def point_to_line_distance(point_lat, point_lng, a_lat, a_lng, b_lat, b_lng):
    """
    Returns approximate distance in km from a point to the line segment A-B.
    Used by Commute Shield to check if an incident is on a commuter's route.
    This is a flat-earth approximation — accurate enough for Lagos corridor checks.
    """
    import math

    def to_rad(d): return d * math.pi / 180
    R = 6371.0

    # Convert to approximate x/y in km
    lat0 = (a_lat + b_lat) / 2
    dx = math.cos(to_rad(lat0))

    ax, ay = a_lng * dx, a_lat
    bx, by = b_lng * dx, b_lat
    px, py = point_lng * dx, point_lat

    # Vector AB
    abx, aby = bx - ax, by - ay
    ab_len_sq = abx * abx + aby * aby

    if ab_len_sq == 0:
        # A and B are same point
        return math.sqrt((px - ax) ** 2 + (py - ay) ** 2) * 111.0

    # Project P onto AB
    t = max(0, min(1, ((px - ax) * abx + (py - ay) * aby) / ab_len_sq))
    closest_x = ax + t * abx
    closest_y = ay + t * aby

    dist_deg = math.sqrt((px - closest_x) ** 2 + (py - closest_y) ** 2)
    return dist_deg * 111.0  # degrees to km (rough)
