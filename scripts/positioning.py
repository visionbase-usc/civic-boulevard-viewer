"""Reproduce coarse two-view annotations; these are NOT surveyed coordinates.

Google Maps URL heading is clockwise from north; fov is horizontal:
https://developers.google.com/maps/documentation/urls/get-started
Camera/georeferencing/panorama calibration error is unknown. Human target pixels
are retained in position-reviews.json. Round to five decimals for display only;
that rounding is not an accuracy claim. Position precision limitations are separate from unresolved evidence status.
"""
import math

def intersect_rays(rays):
    assert len(rays)==2
    lon0,lat0=121.522,25.048
    scale=111320*math.cos(math.radians(lat0))
    v=[]
    for r in rays:
        lon,lat=r['camera'];half=r['imageWidth']/2
        heading=math.radians(r['heading'])+math.atan((r['targetX']-half)/half*math.tan(math.radians(r['fov']/2)))
        v.append(((lon-lon0)*scale,(lat-lat0)*111320,math.sin(heading),math.cos(heading)))
    a,b=v;det=a[2]*b[3]-a[3]*b[2]
    assert abs(det)>.1, 'Rays too parallel for coarse intersection'
    t=((b[0]-a[0])*b[3]-(b[1]-a[1])*b[2])/det
    u=((b[0]-a[0])*a[3]-(b[1]-a[1])*a[2])/det
    assert 0<t<100 and 0<u<100, 'Target must lie ahead of both cameras within 100m'
    return [round(lon0+(a[0]+t*a[2])/scale,5),round(lat0+(a[1]+t*a[3])/111320,5)]
