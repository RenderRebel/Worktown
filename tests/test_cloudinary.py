import unittest
from unittest.mock import patch
from api.routes.users import delete_old_cloudinary_image

class TestCloudinaryCleanup(unittest.TestCase):

    @patch("api.routes.users.cloudinary.uploader.destroy")
    def test_delete_old_image_with_version(self, mock_destroy):
        """Verify parsing when URL includes a version tag (v[digits])."""
        url = "https://res.cloudinary.com/ddi9i7twc/image/upload/v162243432/profile_pics/worker_abc.jpg"
        delete_old_cloudinary_image(url)
        mock_destroy.assert_called_once_with("profile_pics/worker_abc")

    @patch("api.routes.users.cloudinary.uploader.destroy")
    def test_delete_old_image_without_version(self, mock_destroy):
        """Verify parsing when URL does not include a version tag."""
        url = "https://res.cloudinary.com/ddi9i7twc/image/upload/profile_pics/provider_xyz.png"
        delete_old_cloudinary_image(url)
        mock_destroy.assert_called_once_with("profile_pics/provider_xyz")

    @patch("api.routes.users.cloudinary.uploader.destroy")
    def test_delete_old_image_deep_folders(self, mock_destroy):
        """Verify parsing with deep nested folders."""
        url = "http://res.cloudinary.com/somecloud/image/upload/folder1/folder2/folder3/pic.jpeg"
        delete_old_cloudinary_image(url)
        mock_destroy.assert_called_once_with("folder1/folder2/folder3/pic")

    @patch("api.routes.users.cloudinary.uploader.destroy")
    def test_delete_old_image_non_cloudinary(self, mock_destroy):
        """Verify that non-Cloudinary URLs are ignored and destroy is not called."""
        url = "https://example.com/some/random/image.jpg"
        delete_old_cloudinary_image(url)
        mock_destroy.assert_not_called()

    @patch("api.routes.users.cloudinary.uploader.destroy")
    def test_delete_old_image_empty_or_none(self, mock_destroy):
        """Verify that None or empty strings are safely ignored."""
        delete_old_cloudinary_image("")
        delete_old_cloudinary_image(None)
        mock_destroy.assert_not_called()
