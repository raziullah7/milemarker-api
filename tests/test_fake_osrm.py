"""Tests for the stand-in routing server (scripts/fake_osrm.py) and for reading
ROUTING_SERVERS from the environment (config/settings.py).

The stand-in runs as its own process on a free local port, as it does in the end-to-end
stack, and the tests talk to it over HTTP. Case numbers are those of docs/test-cases.md.
"""

import gzip
import importlib.util
import shutil
import socket
import subprocess
import sys
from pathlib import Path

import httpx
import pytest
from django.core.exceptions import ImproperlyConfigured

from tests.conftest import FIXTURES, load_road_answer
from trips.services import routing

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "fake_osrm.py"

DAL_HOU = "-96.80439,32.790439;-95.3657,29.7652"
HOU_DAL = "-95.3657,29.7652;-96.80439,32.790439"
TEMPLATE = "{base}/route/v1/driving/{{coords}}?overview=full&geometries=geojson"


def _free_port() -> int:
    """A port nothing listens on right now."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _start(*args, cwd=REPO):
    """Run the stand-in with `args`; returns the process once it says it is listening."""
    process = subprocess.Popen(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd,
        stdout=subprocess.PIPE,
        text=True,
    )
    # The first line is printed once the socket is bound and listening.
    assert process.stdout.readline().startswith("listening"), "the stand-in did not start"
    return process


def _stop(process):
    """End the stand-in and close its pipe."""
    process.terminate()
    process.wait(timeout=10)
    process.stdout.close()


@pytest.fixture(scope="module")
def base():
    """The address of a stand-in serving the recorded roads, on a free port."""
    port = _free_port()
    process = _start("--host", "127.0.0.1", "--port", str(port))
    yield f"http://127.0.0.1:{port}"
    _stop(process)


@pytest.fixture(autouse=True)
def _clean_log(request):
    """Each test that uses the stand-in starts with an empty request log."""
    if "base" in request.fixturenames:
        httpx.post(request.getfixturevalue("base") + "/_reset")


def recording_bytes(name: str) -> bytes:
    """A recorded answer, unpacked, exactly as stored."""
    return gzip.decompress((FIXTURES / "roads" / f"{name}.json.gz").read_bytes())


def test_si01_a_recorded_pair_returns_its_recording_byte_for_byte(base):
    response = httpx.get(f"{base}/route/v1/driving/{DAL_HOU}?overview=full&geometries=geojson")
    assert response.status_code == 200
    assert response.content == recording_bytes("dal_hou")


def test_si02_the_second_public_path_is_served_too(base):
    response = httpx.get(f"{base}/routed-car/route/v1/driving/{DAL_HOU}")
    assert response.status_code == 200
    assert response.content == recording_bytes("dal_hou")


def test_si03_the_reverse_of_a_recorded_pair_is_not_a_road(base):
    response = httpx.get(f"{base}/route/v1/driving/{HOU_DAL}")
    assert response.status_code == 400
    assert response.json()["code"] == "NoRoute"


def test_si04_a_pair_far_from_every_recording_is_not_a_road(base):
    response = httpx.get(f"{base}/route/v1/driving/0,0;1,1")
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "NoRoute"
    assert body["message"]


def test_si05_both_ends_must_lie_within_30_miles(base):
    finish = "-95.3657,29.7652"
    near = httpx.get(f"{base}/route/v1/driving/-96.797185,33.197306;{finish}")
    far = httpx.get(f"{base}/route/v1/driving/-96.797185,33.226252;{finish}")
    assert near.status_code == 200
    assert near.content == recording_bytes("dal_hou")
    assert far.status_code == 400
    assert far.json()["code"] == "NoRoute"


@pytest.mark.parametrize(
    "path",
    [
        "/route/v1/driving/abc",
        "/route/v1/driving/-96.80439,32.790439",
        "/route/v1/driving/-96.80439,32.790439;north,south",
    ],
)
def test_si06_a_malformed_request_is_an_invalid_url(base, path):
    response = httpx.get(base + path)
    assert response.status_code == 400
    assert response.json()["code"] == "InvalidUrl"


def test_si07_the_request_log_and_its_reset(base):
    # With the query the API sends, which the log leaves out (row 22; review 10R, R10-06).
    query = "?overview=full&geometries=geojson"
    httpx.get(f"{base}/route/v1/driving/{DAL_HOU}{query}")
    httpx.get(f"{base}/route/v1/driving/{HOU_DAL}{query}")
    log = httpx.get(f"{base}/_requests").json()

    assert log["count"] == 2
    first, second = log["requests"]
    assert first["path"] == f"/route/v1/driving/{DAL_HOU}"
    assert second["path"] == f"/route/v1/driving/{HOU_DAL}"
    assert {k: first[k] for k in ("start", "finish", "matched", "status")} == {
        "start": [-96.80439, 32.790439],
        "finish": [-95.3657, 29.7652],
        "matched": "dal_hou",
        "status": 200,
    }
    assert {k: second[k] for k in ("start", "finish", "matched", "status")} == {
        "start": [-95.3657, 29.7652],
        "finish": [-96.80439, 32.790439],
        "matched": None,
        "status": 400,
    }

    assert httpx.post(f"{base}/_reset").status_code == 200
    assert httpx.get(f"{base}/_requests").json() == {"count": 0, "requests": []}


def test_si08_health_answers_200_and_is_not_a_route_request(base):
    assert httpx.get(f"{base}/_health").status_code == 200
    assert httpx.get(f"{base}/_requests").json()["count"] == 0


def test_si12_an_unknown_path_is_an_invalid_url(base):
    """Review 10R, finding R10-11. The real server answers a path it does not serve with
    400 InvalidUrl, which the routing client treats as a wrong request (no second server),
    where a 404 would send it to the second server."""
    response = httpx.get(f"{base}/nothing")
    assert response.status_code == 400
    assert response.json()["code"] == "InvalidUrl"


def test_si09_the_routing_client_reads_the_stand_in_through_the_setting(base, settings):
    settings.ROUTING_SERVERS = [TEMPLATE.format(base=base)]
    route = routing.fetch_route((32.790439, -96.80439), (29.7652, -95.3657))

    expected = load_road_answer("dal_hou")["routes"][0]["distance"] / routing.METRES_PER_MILE
    assert route.distance_miles == expected
    assert route.calls == 1
    assert httpx.get(f"{base}/_requests").json()["count"] == 1


def test_the_routing_client_reads_a_missing_road_as_no_road(base, settings):
    settings.ROUTING_SERVERS = [TEMPLATE.format(base=base)]
    with pytest.raises(routing.NoRoute):
        routing.fetch_route((29.7652, -95.3657), (32.790439, -96.80439))


def test_si10_recordings_are_found_in_the_folder_not_named_in_the_code(tmp_path):
    shutil.copy(FIXTURES / "roads" / "dal_hou.json.gz", tmp_path / "x.json.gz")
    port = _free_port()
    process = _start("--host", "127.0.0.1", "--port", str(port), "--roads", str(tmp_path))
    try:
        url = f"http://127.0.0.1:{port}/route/v1/driving/"
        found = httpx.get(url + DAL_HOU)
        other = httpx.get(url + "-73.996705,40.74838;-118.247896,33.973093")
        assert found.status_code == 200
        assert found.content == recording_bytes("dal_hou")
        assert other.status_code == 400
        assert other.json()["code"] == "NoRoute"
        assert (
            httpx.get(f"http://127.0.0.1:{port}/_requests").json()["requests"][0]["matched"] == "x"
        )
    finally:
        _stop(process)


def test_si11_the_defaults_are_port_5000_everywhere_and_the_recorded_roads():
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", 5000)) == 0:
            pytest.skip("port 5000 is already in use on this machine")
    process = _start()
    try:
        response = httpx.get(f"http://127.0.0.1:5000/route/v1/driving/{DAL_HOU}")
        assert response.status_code == 200
        assert response.content == recording_bytes("dal_hou")
    finally:
        _stop(process)


# --- ROUTING_SERVERS from the environment (CF-08, CF-09, CF-34, CF-35) ----------------------

PUBLIC = [
    "https://router.project-osrm.org/route/v1/driving/{coords}?overview=full&geometries=geojson",
    "https://routing.openstreetmap.de/routed-car/route/v1/driving/{coords}?overview=full&geometries=geojson",
]
LOCAL_1 = "http://127.0.0.1:5000/route/v1/driving/{coords}?overview=full&geometries=geojson"
LOCAL_2 = (
    "http://127.0.0.1:5001/routed-car/route/v1/driving/{coords}?overview=full&geometries=geojson"
)


def _load_settings(monkeypatch, value):
    """Run config/settings.py afresh with ROUTING_SERVERS set to `value` (None: unset).

    A separate module object, so the settings the rest of the suite uses are untouched."""
    if value is None:
        monkeypatch.delenv("ROUTING_SERVERS", raising=False)
    else:
        monkeypatch.setenv("ROUTING_SERVERS", value)
    spec = importlib.util.spec_from_file_location(
        "settings_under_test", REPO / "config" / "settings.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.ROUTING_SERVERS


def test_cf08_unset_gives_the_public_servers_and_a_value_replaces_them(monkeypatch):
    assert _load_settings(monkeypatch, None) == PUBLIC
    assert _load_settings(monkeypatch, LOCAL_1) == [LOCAL_1]
    assert _load_settings(monkeypatch, f"{LOCAL_1},{LOCAL_2}") == [LOCAL_1, LOCAL_2]


def test_cf09_an_entry_without_coords_stops_the_settings_loading(monkeypatch):
    bad = "http://127.0.0.1:5000/route/v1/driving/?overview=full"
    for value in (bad, f"{LOCAL_1},{bad}"):
        with pytest.raises(ImproperlyConfigured) as error:
            _load_settings(monkeypatch, value)
        assert "ROUTING_SERVERS" in str(error.value)
        assert bad in str(error.value)


def test_cf34_entries_are_trimmed_and_empty_ones_dropped(monkeypatch):
    value = f" {LOCAL_1} , ,{LOCAL_2} "
    assert _load_settings(monkeypatch, value) == [LOCAL_1, LOCAL_2]


def test_cf37_more_than_two_servers_stops_the_settings_loading(monkeypatch):
    """Review 10R, finding R10-03. The client tries each server once, so a third entry
    would allow a third routing call; NFR-2 allows two at most."""
    local_3 = LOCAL_1.replace("5000", "5002")
    with pytest.raises(ImproperlyConfigured) as error:
        _load_settings(monkeypatch, f"{LOCAL_1},{LOCAL_2},{local_3}")
    assert "ROUTING_SERVERS" in str(error.value)
    assert "3" in str(error.value)


def test_cf35_empty_or_blank_counts_as_unset_but_commas_only_is_refused(monkeypatch):
    assert _load_settings(monkeypatch, "") == PUBLIC
    assert _load_settings(monkeypatch, "   ") == PUBLIC
    with pytest.raises(ImproperlyConfigured) as error:
        _load_settings(monkeypatch, " , ")
    assert "ROUTING_SERVERS" in str(error.value)
