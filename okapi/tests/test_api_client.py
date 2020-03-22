import pytest

from okapi import APIClient, Resource
from okapi.exceptions import BadRequestError


def test_api_client():
    class Launch(Resource):
        # provides the path for the resource
        path = 'launches'

        def list(self, *args, **kwargs):
            # do something here
            return 'a'

    class SpaceXAPIClient(APIClient):
        resources = [
            Launch
        ]

    space_x_api_client = SpaceXAPIClient(
        host='https://api.spacexdata.com',
        version='v3'
    )
    dragons = space_x_api_client.dragon.list()

    assert dragons

    dragon = space_x_api_client.dragon.get(dragons[0]['id'])

    assert dragon

    launches = space_x_api_client.launch.list()

    assert launches == 'a'


def test_api_client_exception():
    """Test invalid Resource name"""
    space_x_api_client = APIClient(
        host='https://api.spacexdata.com',
        version='v3'
    )
    with pytest.raises(BadRequestError):
        dragoons = space_x_api_client.dragoon.list()
