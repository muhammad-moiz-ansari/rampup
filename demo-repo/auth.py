"""Protected authentication module. Do not modify for the inventory exercise."""


def authenticated_subject(claims):
    return claims['sub']
