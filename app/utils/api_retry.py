import time
import functools
import googlemaps.exceptions

def gmaps_retry(max_retries=2, backoff_factor=1.5):
    """
    Retry decorator, specifically for catching and retrying Google Maps API 
    transient network errors and API exceptions.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = 1
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except (googlemaps.exceptions.TransportError, googlemaps.exceptions.ApiError, googlemaps.exceptions.Timeout) as e:
                    if attempt == max_retries:
                        raise e  # Reached max retries, propagate exception
                    print(f"[gmaps_retry] Google Maps API Error: {e}. Retrying {attempt+1}/{max_retries} in {delay}s...")
                    time.sleep(delay)
                    delay *= backoff_factor
        return wrapper
    return decorator
