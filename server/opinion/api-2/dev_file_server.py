"""
Simple HTTP server for file uploads in dev mode.
Run separately from Azure Functions to avoid body size issues.

Usage: python dev_file_server.py
Runs on port 7072
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import os
import json

PORT = 7072
LOCAL_STORAGE_PATH = os.environ.get("LOCAL_STORAGE_PATH", "/Users/jbenjamin/Web-Dev-Projects/Alchemy/server/opinion/api-2/.local_storage")


class FileUploadHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "PUT, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Local-Path, X-Filename")
        self.end_headers()

    def do_PUT(self):
        """Handle file upload"""
        try:
            # Get headers
            local_path = self.headers.get("X-Local-Path")
            filename = self.headers.get("X-Filename", "unknown")
            content_length = int(self.headers.get("Content-Length", 0))

            print(f"Receiving: {filename} ({content_length} bytes) -> {local_path}")

            if not local_path:
                self._send_error(400, "X-Local-Path header required")
                return

            # Read body
            file_data = self.rfile.read(content_length)
            print(f"Read {len(file_data)} bytes")

            # Ensure directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            # Save file
            with open(local_path, "wb") as f:
                f.write(file_data)

            print(f"Saved to {local_path}")

            # Send success response
            self._send_json(200, {
                "success": True,
                "localPath": local_path,
                "filename": filename,
                "size": len(file_data)
            })

        except Exception as e:
            print(f"Error: {e}")
            self._send_error(500, str(e))

    def do_POST(self):
        """Also handle POST for compatibility"""
        self.do_PUT()

    def _send_json(self, status, data):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _send_error(self, status, message):
        self._send_json(status, {"error": message})

    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {args[0]}")


def main():
    os.makedirs(LOCAL_STORAGE_PATH, exist_ok=True)
    server = HTTPServer(("", PORT), FileUploadHandler)
    print(f"Dev file server running on http://localhost:{PORT}")
    print(f"Storage path: {LOCAL_STORAGE_PATH}")
    server.serve_forever()


if __name__ == "__main__":
    main()
