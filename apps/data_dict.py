import ee
import geemap.colormaps as cm

DATA = {
    "STRM": {
        "id": ee.Image("CGIAR/SRTM90_V4"),
        "vis": {"min": 0, "max": 4000, "palette": cm.get_palette("terrain", 15)},
    },
    "NASA SRTM": {
        "id": ee.Image("USGS/SRTMGL1_003").select("elevation"),
        "vis": {"min": 0, "max": 4000, "palette": cm.get_palette("terrain", 15)},
    },
}
