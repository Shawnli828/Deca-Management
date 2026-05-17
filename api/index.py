from urllib.parse import parse_qs, urlencode, urlparse

from server import ManagementTableHandler


class handler(ManagementTableHandler):
    def _rewrite_vercel_path(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        routed_path = query.pop("path", [""])[0]

        if parsed.path.endswith("/api/index.py") and routed_path:
            next_path = f"/api/{routed_path}"
            next_query = urlencode(query, doseq=True)
            self.path = f"{next_path}?{next_query}" if next_query else next_path

    def do_GET(self):
        self._rewrite_vercel_path()
        super().do_GET()

    def do_POST(self):
        self._rewrite_vercel_path()
        super().do_POST()
