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
