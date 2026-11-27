from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

GIF_PATH = Path("/dev/shm/oledstatuspi.gif")


class OledHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.serve_gif(send_body=True)

    def do_HEAD(self):
        self.serve_gif(send_body=False)

    def serve_gif(self, send_body):
        if self.path.partition("?")[0] != "/oledstatuspi.gif":
            self.send_error(404)
            return
        try:
            frame = GIF_PATH.read_bytes()
        except OSError:
            self.send_error(503, "OLED frame unavailable")
            return
        if not frame.startswith((b"GIF87a", b"GIF89a")) or not frame.endswith(b";"):
            self.send_error(503, "OLED frame incomplete")
            return
        self.send_response(200)
        self.send_header("Content-Type", "image/gif")
        self.send_header("Content-Length", str(len(frame)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if send_body:
            self.wfile.write(frame)

    def log_request(self, code="-", size="-"):
        if code != 200:
            super().log_request(code, size)


if __name__ == "__main__":
    with ThreadingHTTPServer(("0.0.0.0", 8766), OledHandler) as server:
        server.serve_forever()
