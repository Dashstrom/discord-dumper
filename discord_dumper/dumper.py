"""PArse websocket."""

import base64
import logging
import pathlib
import re
import shutil
import zlib
from concurrent.futures import ProcessPoolExecutor
from typing import Any, Dict, Optional, Union
from urllib.error import HTTPError
from urllib.parse import parse_qs, unquote, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen

import orjson

AUTHORIZED_EXTENSIONS = (
    ".webp",
    ".png",
    ".jpeg",
    ".jpeg",
    ".svg",
    ".ico",
    ".gif",
)
logger = logging.getLogger(__name__)
ALPHANUM = re.compile(r"[^a-z0-9]+")
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)
OK = 200


class SecurityError(Exception):
    pass


def get_image_path(url: str) -> pathlib.Path:
    """Get image paths."""
    image_root = pathlib.Path("images").resolve()
    parsed_url = urlparse(url)
    url_path = unquote(parsed_url.path).lstrip("/")
    path = image_root / url_path
    if parsed_url.query:
        path = path.parent / unquote(parsed_url.query) / path.name
    path = path.resolve()
    if image_root not in path.parents:
        error_message = (
            f"Attempted path traversal with {url!r} " f"resulting at {path!r}"
        )
        raise SecurityError(error_message)
    if path.suffix not in AUTHORIZED_EXTENSIONS:
        error_message = (
            f"Invalid extension for {url!r} resulting as {path.suffix}"
        )
        raise SecurityError(error_message)
    return pathlib.Path("images") / path.relative_to(image_root)


def fetch_and_save_image(url: str) -> int:
    """FEtch and save url."""
    req = Request(url)  # noqa: S310
    req.add_header("User-Agent", USER_AGENT)
    try:
        with urlopen(req) as res:  # noqa: S310
            path = pathlib.Path("discord") / get_image_path(url)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("wb") as output:
                shutil.copyfileobj(res, output)
                return res.status  # type: ignore[no-any-return]
    except HTTPError as e:
        return getattr(e, "status", -1)


def dump(  # noqa: C901, PLR0912, PLR0915
    path: Union[str, pathlib.Path],
    *,
    images: Optional[bool] = None,
    pretty: Optional[bool] = None,
    fetch: Optional[bool] = None,
) -> None:
    """Dump file."""
    if images is None:
        images = True
    if pretty is None:
        pretty = True
    if fetch is None:
        fetch = False
    options: Dict[str, Any] = {}
    if pretty:
        options["option"] = orjson.OPT_INDENT_2
    root = pathlib.Path("discord")
    shutil.rmtree(root, ignore_errors=True)
    content = pathlib.Path(path).read_text("utf-8").strip()
    obj = orjson.loads(content)
    inflator = zlib.decompressobj()
    events = []
    urls = []
    for entry in obj["log"]["entries"]:
        url: str = entry["request"]["url"]
        if (
            url
            == "wss://gateway.discord.gg/?encoding=json&v=9&compress=zlib-stream"
        ):
            pathlib.Path("discord.json")
            for message in entry["_webSocketMessages"]:
                message_data = message["data"]
                if message["type"] != "send":
                    data = base64.b64decode(message_data)
                    message_data = orjson.loads(inflator.decompress(data))
                else:
                    message_data = orjson.loads(message_data)
                events.append(message_data)
        elif entry["response"]["content"]["mimeType"].startswith("image/"):
            if not url.startswith("https://cdn.discordapp.com/"):
                continue
            image_path = root / get_image_path(url)
            text = entry["response"]["content"].get("text", None)
            if text is None:
                logger.warning("No data for %s", url)
                continue
            if entry["response"]["content"].get("encoding") == "base64":
                data = base64.b64decode(text)
            else:
                data = text.encode("utf-8")
            image_path.parent.mkdir(parents=True, exist_ok=True)
            image_path.write_bytes(data)
            if fetch:
                parsed_url = urlparse(url)
                if not parsed_url.path.startswith("/badge-icons/"):
                    query = parse_qs(parsed_url.query)
                    query["size"] = ["4096"]
                    for key, value in query.items():
                        if len(value) == 1:
                            query[key] = value[0]  # type: ignore[assignment]
                    parts = list(parsed_url)
                    parts[4] = urlencode(query)
                    size_url = urlunparse(parts)
                    urls.append(size_url)
    if fetch:
        with ProcessPoolExecutor() as pool:
            for url, status in zip(urls, pool.map(fetch_and_save_image, urls)):
                if status == OK:
                    logger.debug("Fetched %s", url)
                else:
                    logger.warning("Error %d on %s", status, url)
    events_path = root / pathlib.Path("events.json")
    events_path.write_bytes(orjson.dumps(events, **options))
    for event in events:
        if event.get("t") == "READY":
            for key in (
                "guilds",
                "users",
                "private_channels",
            ):
                for obj in event["d"][key]:
                    obj_path = root / key / f'{obj["id"]}.json'
                    obj_path.parent.mkdir(exist_ok=True, parents=True)
                    obj_path.write_bytes(orjson.dumps(obj, **options))
            for obj in event["d"]["connected_accounts"]:
                name = f'{obj["type"]}/{obj["id"]}.json'
                obj_path = root / "connected_accounts" / name
                obj_path.parent.mkdir(exist_ok=True, parents=True)
                obj_path.write_bytes(orjson.dumps(obj, **options))
    logger.warning(
        "Don't send your files without verification, "
        "they can contains you credentials.",
    )
