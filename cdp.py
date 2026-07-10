#!/usr/bin/env python3
"""Small CDP client for the Chrome profile PinForge drives on port 9224.
Talks to Chrome directly over the websocket so file uploads and clicks land
the way Pinterest/Gumroad's React UI actually expects them to."""
import json, time, urllib.request
from websocket import create_connection

PORT = 9224


def tabs():
    raw = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json", timeout=5).read()
    return [t for t in json.loads(raw) if t.get("type") == "page"]


class Tab:
    def __init__(self, ws_url):
        self.ws = create_connection(ws_url, max_size=None, timeout=20)
        self.ws.settimeout(20)  # never block forever on recv
        self._id = 0
        self.send("Page.enable")
        self.send("Runtime.enable")
        self.send("DOM.enable")

    @classmethod
    def attach(cls, url_contains):
        for t in tabs():
            if url_contains in t.get("url", ""):
                return cls(t["webSocketDebuggerUrl"])
        raise RuntimeError(f"No tab matching {url_contains!r}. Tabs: {[t.get('url') for t in tabs()]}")

    @classmethod
    def open(cls, url):
        req = urllib.request.Request(f"http://127.0.0.1:{PORT}/json/new?{url}", method="PUT")
        t = json.loads(urllib.request.urlopen(req, timeout=8).read())
        time.sleep(2)
        return cls(t["webSocketDebuggerUrl"])

    def send(self, method, **params):
        self._id += 1
        mid = self._id
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})

    def eval(self, expr, await_promise=False):
        r = self.send("Runtime.evaluate", expression=expr, returnByValue=True,
                      awaitPromise=await_promise, userGesture=True)
        res = r.get("result", {})
        if res.get("type") == "object" and "value" not in res:
            return res
        return res.get("value")

    def navigate(self, url, wait=3):
        self.send("Page.navigate", url=url)
        time.sleep(wait)

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass


if __name__ == "__main__":
    import sys
    match = sys.argv[1] if len(sys.argv) > 1 else "pinterest.com"
    expr = sys.argv[2] if len(sys.argv) > 2 else "document.title"
    t = Tab.attach(match)
    print(json.dumps(t.eval(expr), indent=2, default=str))
