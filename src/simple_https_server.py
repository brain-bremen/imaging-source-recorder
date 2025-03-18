from http.server import BaseHTTPRequestHandler, HTTPServer
import json


class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers["Content-Length"])
        post_data = self.rfile.read(content_length)

        if self.path == "/start_recording":
            data = json.loads(post_data)
            file_name = data.get("file_name")
            frame_rate = data.get("frame_rate", None)
            triggered_mode = data.get("triggered_mode", False)
            self.server.recorder.start_recording(file_name, frame_rate, triggered_mode)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Recording started")
        elif self.path == "/stop_recording":
            self.server.recorder.stop_recording()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Recording stopped")
        else:
            self.send_response(404)
            self.end_headers()


def run_http_server(recorder, port=8000):
    server_address = ("", port)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    httpd.recorder = recorder
    httpd.serve_forever()
