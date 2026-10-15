# Timing model

## Fields

- `#event_time`: event occurrence time stored by AE.
- `#server_time`: time the server received the event, expressed in the deployment-local time zone.
- `#dw_create_time`: time the row was written to the warehouse; this is not the event occurrence time.
- `#zone_offset`: event-side UTC offset metadata used to judge whether event-time samples have sufficient time-zone information.

## Time-zone normalization

Use the user-confirmed `--server-zone-offset` as the common server time zone for `#server_time` and `#dw_create_time`. The checker must stop when it is unknown; never assume UTC+8.

Normalize event time before subtraction:

```sql
date_add(
  'minute',
  cast((<server_offset> - "#zone_offset") * 60 as bigint),
  "#event_time"
)
```

Then calculate:

```sql
date_diff('second', <normalized_event_time>, "#server_time")
date_diff('second', "#server_time", "#dw_create_time")
date_diff('second', <normalized_event_time>, "#dw_create_time")
```

Do not use absolute values for negative results.

By default, null or out-of-range event offsets are excluded from upload and end-to-end segments. When the user supplies the actual offset for null rows, normalize with `coalesce("#zone_offset", <provided>)` and record it. Invalid non-null values remain excluded.

The expected threshold is the user-confirmed `--expected-seconds`. The one-hour boundary is a separate severity observation.
