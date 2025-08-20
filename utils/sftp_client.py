# utils/sftp_client.py
import paramiko
from typing import Iterator, Tuple, Optional

class SFTPReader:
    """
    Lector SFTP por streaming (no descarga a disco).
    Uso:
        with SFTPReader(host, port, user, pwd) as s:
            for fname, data in s.iter_json_files("ruta/remota"):
                ...
    """
    def __init__(self, host: str, port: int, username: str, password: str):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self._client = None
        self._sftp = None

    def __enter__(self):
        self._client = paramiko.Transport((self.host, self.port))
        self._client.connect(username=self.username, password=self.password)
        self._sftp = paramiko.SFTPClient.from_transport(self._client)
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if self._sftp: self._sftp.close()
        finally:
            if self._client: self._client.close()

    def iter_json_files(self, remote_dir: str) -> Iterator[Tuple[str, bytes]]:
        for f in self._sftp.listdir_attr(remote_dir):
            if f.filename.lower().endswith(".json"):
                with self._sftp.open(f"{remote_dir}/{f.filename}", "rb") as fh:
                    yield f.filename, fh.read()
