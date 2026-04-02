from prometheus_client import Counter, Histogram

# Track business events
ORDERS_CREATED = Counter(
    "marketo_orders_created_total",
    "Total number of orders successfully created",
)

REGISTRATIONS = Counter(
    "marketo_user_registrations_total",
    "Total number of user registrations",
)

CACHE_HITS = Counter(
    "marketo_cache_hits_total",
    "Total number of Redis cache hits",
    ["resource"],  # label: product, order, user, etc.
)

CACHE_MISSES = Counter(
    "marketo_cache_misses_total",
    "Total number of Redis cache misses",
    ["resource"],
)

PRODUCT_SEARCH_LATENCY = Histogram(
    "marketo_product_search_duration_seconds",
    "Time spent on product full-text search queries",
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
)
