
import json
import socket
import ssl
import http.client
import time
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "proxies.json"

def check_proxy(proxy):
    domain = proxy.get("domain", "")
    port = int(proxy.get("port", 443))

    result = {
        "endpoint_status": "offline",
        "tls_valid": False,
        "http_status": None,
        "latency_ms": None,
        "checked_at": datetime.now(timezone.utc).isoformat()
    }

    if (
        not domain
        or "://" in domain
        or "/" in domain
        or not re.fullmatch(r"[A-Za-z0-9.-]+", domain)
        or not 1 <= port <= 65535
    ):
        return result

    connection = None
    started = time.monotonic()

    try:
        socket.getaddrinfo(
            domain,
            port,
            type=socket.SOCK_STREAM
        )

        context = ssl.create_default_context()

        connection = http.client.HTTPSConnection(
            domain,
            port,
            context=context,
            timeout=12
        )

        connection.request(
            "GET",
            "/",
            headers={
                "User-Agent": "NovixProxy-Monitor/1.0",
                "Connection": "close"
            }
        )

        response = connection.getresponse()
        response.read(1024)

        result["endpoint_status"] = "online"
        result["tls_valid"] = True
        result["http_status"] = response.status
        result["latency_ms"] = round(
            (time.monotonic() - started) * 1000
        )

    except Exception as error:
        print(f"Check failed for {domain}: {error}")

    finally:
        if connection:
            connection.close()

    return result


def main():
    with DATA_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    proxies = data.get("proxies", [])

    for proxy in proxies:
        result = check_proxy(proxy)
        proxy.update(result)

        print(
            f"{proxy.get('domain')}: "
            f"{result['endpoint_status']}"
        )

    data["updated_at"] = datetime.now(
        timezone.utc
    ).isoformat()

    with DATA_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
        file.write("\n")

    print("Novix Proxy monitoring completed.")


if __name__ == "__main__":
    main()
