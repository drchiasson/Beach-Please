import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

REQUEST_TIMEOUT = 10  # seconds, applied to all outbound HTTP requests

_retry = Retry(
    total=3,  # retries on top of the original attempt, so up to 4 tries total
    backoff_factor=1,  # ~1s, 2s, 4s between attempts
    status_forcelist=[429, 500, 502, 503, 504],
)
_adapter = HTTPAdapter(max_retries=_retry)

# Shared across all outbound HTTP calls so transient timeouts/5xx responses
# (api.weather.gov in particular is prone to these) don't fail a whole run.
session = requests.Session()
session.mount("https://", _adapter)
session.mount("http://", _adapter)
