import logging
import requests
import http.client

# Enable verbose logging for HTTP requests
http.client.HTTPConnection.debuglevel = 1

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True

print("=== Testing pnsea ===")
try:
    from pnsea import NSE
    nse = NSE()
    print("Calling nse.equity.info('TCS')")
    data = nse.equity.info("TCS")
    print(f"Success! Data keys: {data.keys()}")
except Exception as e:
    print(f"PNSEA Error: {e}")

print("\n=== Testing nsepython ===")
try:
    from nsepython import nse_eq
    print("Calling nse_eq('TCS')")
    data = nse_eq("TCS")
    print(f"Success! Data keys: {data.keys()}")
except Exception as e:
    print(f"NSEPYTHON Error: {e}")
