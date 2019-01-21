# okapi

A set of tools to help you wrap REST-like web APIs.
Originally built to help one of the internal project,
but it's started to be used in multiple projects so packaging it
makes the most sense.

Initially, I didn't plan to create this from scratch,
knowing there must be similar library that does this.
But I didn't find any, probably due to my bad Google keyword...

After reading this very recent reddit's [post](https://www.reddit.com/r/Python/comments/ahlqau/announcement_of_anyapi_a_python_library_to_help/),
turns out there's already some libraries that does this (well duh).
There's a "what differs this from..." section below.

## Quick Example

```python
from okapi import APIClient, Resource

space_x_api_client = APIClient(
    host='https://api.spacexdata.com',
    version='v3'
)

# -s REST Resource plural will be appended automatically
# -es ending not supported yet, thus you need to customize
# it yourself like the Launch above
dragons = space_x_api_client.dragon.list()

print(dragons)
# [{'pressurized_capsule': {'payload_volume': {'cubic_feet': 388 ....

dragon = space_x_api_client.dragon.get(dragons[1]['id'])

print(dragon)
# {'pressurized_capsule': {'payload_volume': {'cubic_feet': 388 ....

# Another example, with customized Resource
class Launch(Resource):
    # provides the path for the resource
    path = 'launches'

    def list(self, *args, **kwargs):
        # do something here
        pass

class SpaceXAPIClient(APIClient):
    # customized resources is listed here
    resources = [
        Launch
    ]

space_x_api_client = SpaceXAPIClient(
    host='https://api.spacexdata.com',
    version='v3'
)

launches = space_x_api_client.launch.list()

print(launches)
```

## What differs this from other libraries?

Disclaimer, this only from my quick glance looking from various
similar projects. So my points below are arguably weak.

- okapi tries to automate every things possible for the least amount of
code
- it tries conceptualize REST resources correctly as opposed to just
HTTP methods or generic methods
- the only apparent advantage I see is better namespacing and closer
resemblance to REST terminology.


## Compatibility

Tested with Py 2.7 and 3.4

## Testing

Run in your terminal

    pytest
