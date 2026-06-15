"""pages package"""
from pages.home import HomeFrame
from pages.login import LoginFrame
from pages.register import RegisterFrame
from pages.feed import FeedFrame
from pages.search import SearchFrame
from pages.profile import ProfileFrame
from pages.friends import FriendsFrame

__all__ = [
    "HomeFrame",
    "LoginFrame",
    "RegisterFrame",
    "FeedFrame",
    "SearchFrame",
    "ProfileFrame",
    "FriendsFrame",
]