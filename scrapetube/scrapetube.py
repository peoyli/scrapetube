import json
import time
from typing import Generator

import requests
from typing_extensions import Literal

type_property_map = {
    "videos": "videoRenderer",
    "streams": "videoRenderer",
    "shorts": "reelWatchEndpoint"
}

def get_channel(
    channel_id: str = None,
    channel_url: str = None,
    channel_username: str = None,
    limit: int = None,
    sleep: float = 1,
    proxies: dict = None,
    sort_by: Literal["newest", "oldest", "popular"] = "newest",
    content_type: Literal["videos", "shorts", "streams"] = "videos",
) -> Generator[dict, None, None]:

    """Get videos for a channel.

    Parameters:
        channel_id (``str``, *optional*):
            The channel id from the channel you want to get the videos for.
            If you prefer to use the channel url instead, see ``channel_url`` below.

        channel_url (``str``, *optional*):
            The url to the channel you want to get the videos for.
            Since there is a few type's of channel url's, you can use the one you want
            by passing it here instead of using ``channel_id``.

        channel_username (``str``, *optional*):
            The username from the channel you want to get the videos for.
            Ex. ``LinusTechTips`` (without the @).
            If you prefer to use the channel url instead, see ``channel_url`` above.

        limit (``int``, *optional*):
            Limit the number of videos you want to get.

        sleep (``int``, *optional*):
            Seconds to sleep between API calls to youtube, in order to prevent getting blocked.
            Defaults to 1.

        proxies (``dict``, *optional*):
            A dictionary with the proxies you want to use. Ex:
            ``{'https': 'http://username:password@101.102.103.104:3128'}``

        sort_by (``str``, *optional*):
            In what order to retrieve to videos. Pass one of the following values.
            ``"newest"``: Get the new videos first.
            ``"oldest"``: Get the old videos first.
            ``"popular"``: Get the popular videos first. Defaults to "newest".

        content_type (``str``, *optional*):
            In order to get content type. Pass one of the following values.
            ``"videos"``: Videos
            ``"shorts"``: Shorts
            ``"streams"``: Streams
    """

    base_url = ""
    if channel_url:
        base_url = channel_url
    elif channel_id:
        base_url = f"https://www.youtube.com/channel/{channel_id}"
    elif channel_username:
        base_url = f"https://www.youtube.com/@{channel_username}"

    url = "{base_url}/{content_type}?view=2".format(
        base_url=base_url,
        content_type=content_type,
    )
    api_endpoint = "https://www.youtube.com/youtubei/v1/browse"
    videos = get_videos(url, api_endpoint, "contents", type_property_map[content_type], limit, sleep, proxies, sort_by, content_type)
    for video in videos:
        yield video

def get_playlist(
    playlist_id: str, limit: int = None, sleep: int = 1, proxies: dict = None
) -> Generator[dict, None, None]:

    """Get videos for a playlist.

    Parameters:
        playlist_id (``str``):
            The playlist id from the playlist you want to get the videos for.

        limit (``int``, *optional*):
            Limit the number of videos you want to get.

        sleep (``int``, *optional*):
            Seconds to sleep between API calls to youtube, in order to prevent getting blocked.
            Defaults to 1.

        proxies (``dict``, *optional*):
            A dictionary with the proxies you want to use. Ex:
            ``{'https': 'http://username:password@101.102.103.104:3128'}``
    """

    url = f"https://www.youtube.com/playlist?list={playlist_id}"
    api_endpoint = "https://www.youtube.com/youtubei/v1/browse"

    # YouTube migrated playlist pages from the old "playlistVideoListRenderer"
    # container to "itemSectionRenderer" wrapping richItemRenderer/lockupViewModel
    # nodes. The old selector no longer matches anything on current pages.
    videos = get_videos(
        url, api_endpoint, "itemSectionRenderer", "playlistVideoRenderer", limit, sleep, proxies
    )
    for video in videos:
        yield video

def get_search(
    query: str,
    limit: int = None,
    sleep: int = 1,
    sort_by: Literal["relevance", "upload_date", "view_count", "rating"] = "relevance",
    results_type: Literal["video", "channel", "playlist", "movie"] = "video",
    proxies: dict = None,
) -> Generator[dict, None, None]:

    """Search youtube and get videos.

    Parameters:
        query (``str``):
            The term you want to search for.

        limit (``int``, *optional*):
            Limit the number of videos you want to get.

        sleep (``int``, *optional*):
            Seconds to sleep between API calls to youtube, in order to prevent getting blocked.
            Defaults to 1.

        sort_by (``str``, *optional*):
            In what order to retrieve to videos. Pass one of the following values.
            ``"relevance"``: Get the new videos in order of relevance.
            ``"upload_date"``: Get the new videos first.
            ``"view_count"``: Get the popular videos first.
            ``"rating"``: Get videos with more likes first.
            Defaults to "relevance".

        results_type (``str``, *optional*):
            What type you want to search for. Pass one of the following values:
            ``"video"|"channel"|"playlist"|"movie"``. Defaults to "video".

        proxies (``dict``, *optional*):
            A dictionary with the proxies you want to use. Ex:
            ``{'https': 'http://username:password@101.102.103.104:3128'}``
    """

    sort_by_map = {
        "relevance": "A",
        "upload_date": "I",
        "view_count": "M",
        "rating": "E",
    }

    results_type_map = {
        "video": ["B", "videoRenderer"],
        "channel": ["C", "channelRenderer"],
        "playlist": ["D", "playlistRenderer"],
        "movie": ["E", "videoRenderer"],
    }

    param_string = f"CA{sort_by_map[sort_by]}SAhA{results_type_map[results_type][0]}"
    url = f"https://www.youtube.com/results?search_query={query}&sp={param_string}"
    api_endpoint = "https://www.youtube.com/youtubei/v1/search"
    videos = get_videos(
        url, api_endpoint, "contents", results_type_map[results_type][1], limit, sleep, proxies
    )
    for video in videos:
        yield video

def get_video(
    id: str,
) -> dict:

    """Get a single video.

    Parameters:
        id (``str``):
            The video id from the video you want to get.
    """

    session = get_session()
    url = f"https://www.youtube.com/watch?v={id}"
    html = get_initial_data(session, url)
    client = json.loads(
        get_json_from_html(html, "INNERTUBE_CONTEXT", 2, '"}},') + '"}}'
    )["client"]
    session.headers["X-YouTube-Client-Name"] = "1"
    session.headers["X-YouTube-Client-Version"] = client["clientVersion"]
    data = json.loads(
        get_json_from_html(html, "var ytInitialData = ", 0, "};") + "}"
    )
    return next(search_dict(data, "videoPrimaryInfoRenderer"))

def get_videos(
    url: str, api_endpoint: str, selector_list: str, selector_item: str, limit: int, sleep: float, proxies: dict = None, sort_by: str = None, content_type: str = None
) -> Generator[dict, None, None]:
    session = get_session(proxies)
    is_first = True
    quit_it = False
    count = 0
    while True:
        if is_first:
            html = get_initial_data(session, url)
            client = json.loads(
                get_json_from_html(html, "INNERTUBE_CONTEXT", 2, '"}},') + '"}}'
            )["client"]
            api_key = get_json_from_html(html, "innertubeApiKey", 3)
            session.headers["X-YouTube-Client-Name"] = "1"
            session.headers["X-YouTube-Client-Version"] = client["clientVersion"]
            data = json.loads(
                get_json_from_html(html, "var ytInitialData = ", 0, "};") + "}"
            )

            # Do not parse the channel Home page when the requested tab does not exist.
            if content_type:
                tabs = next(search_dict(data, "tabs"), [])
                tab_urls = [
                    tab.get("tabRenderer", {})
                    .get("endpoint", {})
                    .get("commandMetadata", {})
                    .get("webCommandMetadata", {})
                    .get("url", "")
                    for tab in tabs
                ]
                if not any(tab_url.endswith("/" + content_type) for tab_url in tab_urls):
                    return

            data = next(search_dict(data, selector_list), None)
            next_data = get_next_data(data, sort_by)
            is_first = False
            if sort_by and sort_by != "newest":
                continue
        else:
            data = get_ajax_data(session, api_endpoint, api_key, next_data, client)
            next_data = get_next_data(data)

        for result in get_videos_items(data, selector_item):
            try:
                count += 1
                yield result
                if count == limit:
                    quit_it = True
                    break
            except GeneratorExit:
                quit_it = True
                break

        if not next_data or quit_it:
            break

        time.sleep(sleep)

    session.close()

def get_session(proxies: dict = None) -> requests.Session:
    session = requests.Session()
    if proxies:
        session.proxies.update(proxies)
    session.headers[
        "User-Agent"
    ] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    session.headers["Accept-Language"] = "en"
    return session

def get_initial_data(session: requests.Session, url: str) -> str:
    session.cookies.set("CONSENT", "YES+cb", domain=".youtube.com")
    response = session.get(url, params={"ucbcb":1})
    html = response.text
    return html

def get_ajax_data(
    session: requests.Session,
    api_endpoint: str,
    api_key: str,
    next_data: dict,
    client: dict,
) -> dict:
    data = {
        "context": {"clickTracking": next_data["click_params"], "client": client},
        "continuation": next_data["token"],
    }
    response = session.post(api_endpoint, params={"key": api_key}, json=data)
    return response.json()

def get_json_from_html(html: str, key: str, num_chars: int = 2, stop: str = '"') -> str:
    pos_begin = html.find(key) + len(key) + num_chars
    pos_end = html.find(stop, pos_begin)
    return html[pos_begin:pos_end]

def get_next_data(data: dict, sort_by: str = None) -> dict:
    # Youtube, please don't change the order of these
    sort_by_map = {
        "newest": 0,
        "popular": 1,
        "oldest": 2,
    }
    if sort_by and sort_by != "newest":
        endpoint = next(
            search_dict(data, "feedFilterChipBarRenderer"), None)["contents"][sort_by_map[sort_by]]["chipCloudChipRenderer"]["navigationEndpoint"]
    else:
        endpoint = next(search_dict(data, "continuationEndpoint"), None)

    if not endpoint:
        return None

    token = endpoint["continuationCommand"]["token"]
    next_data = {
        "token": token,
        "click_params": {"clickTrackingParams": endpoint["clickTrackingParams"]},
    }

    return next_data

def search_dict(partial: dict, search_key: str) -> Generator[dict, None, None]:
    stack = [partial]
    while stack:
        current_item = stack.pop(0)
        if isinstance(current_item, dict):
            for key, value in current_item.items():
                if key == search_key:
                    yield value
                else:
                    stack.append(value)
        elif isinstance(current_item, list):
            for value in current_item:
                stack.append(value)

def parse_rich_item_new_format(rich_item: dict) -> dict:
    """Parse richItemRenderer wrapper (used on channel pages)."""
    content = rich_item.get("content", {})
    lockup_view = content.get("lockupViewModel", {})
    if lockup_view:
        return parse_lockup_view_model(lockup_view)
    return None

def parse_lockup_view_model(lockup_view: dict) -> dict:
    """Parse a lockupViewModel dict directly (used by both channels and playlists)."""
    try:
        # Try the simple, direct approach first, get videoId from contentId
        video_id = lockup_view.get("contentId")
        content_type = lockup_view.get("contentType", "")

        # Only proceed if this is actually a video
        if content_type and content_type != "LOCKUP_CONTENT_TYPE_VIDEO":
            return None

        # Fallback: search for watchEndpoint if still no videoId
        if not video_id:
            for endpoint in search_dict(lockup_view, "watchEndpoint"):
                video_id = endpoint.get("videoId")
                if video_id:
                    break

        if not video_id:
            return None

        metadata = lockup_view.get("metadata", {})
        lockup_metadata = metadata.get("lockupMetadataViewModel", {})

        # Extract title
        title = lockup_metadata.get("title", {}).get("content", "")

        # Extract thumbnail URL
        thumbnail_url = None
        content_image = lockup_view.get("contentImage", {})
        sources = content_image.get("thumbnailViewModel", {}).get("image", {}).get("sources", [])
        if sources:
            thumbnail_url = sources[-1].get("url")

        # Extract metadata rows (channel name, views, upload time)
        channel_name = None
        views = None
        upload_time = None

        meta_rows = lockup_metadata.get("metadata", {}).get("contentMetadataViewModel", {}).get("metadataRows", [])

        if len(meta_rows) == 1:
            # Channel pages: single row is views/upload only, no channel name
            parts = meta_rows[0].get("metadataParts", [])
            if len(parts) > 0:
                views = parts[0].get("text", {}).get("content", "")
            if len(parts) > 1:
                upload_time = parts[1].get("text", {}).get("content", "")
        elif len(meta_rows) >= 2:
            # Playlists: row 0 = channel name, row 1 = views/upload
            parts0 = meta_rows[0].get("metadataParts", [])
            if parts0:
                channel_name = parts0[0].get("text", {}).get("content", "")

            parts1 = meta_rows[1].get("metadataParts", [])
            if len(parts1) > 0:
                views = parts1[0].get("text", {}).get("content", "")
            if len(parts1) > 1:
                upload_time = parts1[1].get("text", {}).get("content", "")

        result = {
            "videoId": video_id,
            "title": {"simpleText": title},
        }

        if thumbnail_url:
            result["thumbnail"] = {"thumbnails": [{"url": thumbnail_url}]}
        if channel_name:
            result["shortBylineText"] = {"simpleText": channel_name}
        if views:
            result["viewCountText"] = {"simpleText": views}
        if upload_time:
            result["publishedTimeText"] = {"simpleText": upload_time}

        return result

    except (KeyError, TypeError, AttributeError, IndexError):
        pass

    return None

def parse_shorts_lockup_format(rich_item: dict) -> dict:
    """Parse shortsLockupViewModel format (Shorts)."""
    try:
        content = rich_item.get("content", {})
        shorts_lockup = content.get("shortsLockupViewModel", {})

        if not shorts_lockup:
            return None

        video_id = None
        for endpoint in search_dict(shorts_lockup, "reelWatchEndpoint"):
            video_id = endpoint.get("videoId")
            if video_id:
                break

        if not video_id:
            return None

        overlay_metadata = shorts_lockup.get("overlayMetadata", {})
        title = overlay_metadata.get("primaryText", {}).get("content", "")
        views = overlay_metadata.get("secondaryText", {}).get("content", "")

        return {
            "videoId": video_id,
            "title": {"simpleText": title},
            "viewCountText": {"simpleText": views},
            "isShort": True,
        }

    except (KeyError, TypeError, AttributeError):
        pass

    return None

def get_videos_items(data: dict, selector: str) -> Generator[dict, None, None]:
    """Get video items, handling both old and new YouTube formats."""

    if selector in ("videoRenderer", "playlistVideoRenderer"):
        rich_items = list(search_dict(data, "richItemRenderer"))
        yielded_any = False

        if rich_items:
            for rich_item in rich_items:
                video_data = parse_rich_item_new_format(rich_item)
                if video_data:
                    yielded_any = True
                    yield video_data
                    continue
                video_data = parse_shorts_lockup_format(rich_item)
                if video_data:
                    yielded_any = True
                    yield video_data

        if yielded_any:
            return

        lockup_items = list(search_dict(data, "lockupViewModel"))
        if lockup_items:
            for lockup_view in lockup_items:
                video_data = parse_lockup_view_model(lockup_view)
                if video_data:
                    yielded_any = True
                    yield video_data

        if yielded_any:
            return

        for video in search_dict(data, selector):
            yield video
    else:
        for item in search_dict(data, selector):
            yield item
