import copy
import logging

from .endpoint import Endpoint, api
from .exceptions import MissingRequiredFieldError
from tableauserverclient.server import RequestFactory
from tableauserverclient.models import SiteItem, PaginationItem

from tableauserverclient.helpers.logging import logger

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..request_options import RequestOptions


class Sites(Endpoint):
    @property
    def baseurl(self) -> str:
        return f"{self.parent_srv.baseurl}/sites"

    # Gets all sites
    @api(version="2.0")
    def get(self, req_options: Optional["RequestOptions"] = None) -> tuple[list[SiteItem], PaginationItem]:
        logger.info("Querying all sites on site")
        logger.info("Requires Server Admin permissions")
        url = self.baseurl
        server_response = self.get_request(url, req_options)
        pagination_item = PaginationItem.from_response(server_response.content, self.parent_srv.namespace)
        all_site_items = SiteItem.from_response(server_response.content, self.parent_srv.namespace)
        return all_site_items, pagination_item

    # Gets 1 site by id
    @api(version="2.0")
    def get_by_id(self, site_id: str) -> SiteItem:
        if not site_id:
            error = "Site ID undefined."
            raise ValueError(error)
        if not site_id == self.parent_srv.site_id:
            error = "You can only retrieve the site for which you are currently authenticated."
            raise ValueError(error)

        logger.info(f"Querying single site (ID: {site_id})")
        url = f"{self.baseurl}/{site_id}"
        server_response = self.get_request(url)
        return SiteItem.from_response(server_response.content, self.parent_srv.namespace)[0]

    # Gets 1 site by name
    @api(version="2.0")
    def get_by_name(self, site_name: str) -> SiteItem:
        if not site_name:
            error = "Site Name undefined."
            raise ValueError(error)
        print("Note: You can only work with the site for which you are currently authenticated")
        logger.info(f"Querying single site (Name: {site_name})")
        url = f"{self.baseurl}/{site_name}?key=name"
        print(self.baseurl, url)
        server_response = self.get_request(url)
        return SiteItem.from_response(server_response.content, self.parent_srv.namespace)[0]

    # Gets 1 site by content url
    @api(version="2.0")
    def get_by_content_url(self, content_url: str) -> SiteItem:
        if content_url is None:
            error = "Content URL undefined."
            raise ValueError(error)
        if not self.parent_srv.baseurl.index(content_url) > 0:
            error = "You can only work with the site you are currently authenticated for"
            raise ValueError(error)

        logger.info(f"Querying single site (Content URL: {content_url})")
        logger.debug("Querying other sites requires Server Admin permissions")
        url = f"{self.baseurl}/{content_url}?key=contentUrl"
        server_response = self.get_request(url)
        return SiteItem.from_response(server_response.content, self.parent_srv.namespace)[0]

    # Update site
    @api(version="2.0")
    def update(self, site_item: SiteItem) -> SiteItem:
        if not site_item.id:
            error = "Site item missing ID."
            raise MissingRequiredFieldError(error)
        print(self.parent_srv.site_id, site_item.id)
        if not site_item.id == self.parent_srv.site_id:
            error = "You can only update the site you are currently authenticated for"
            raise ValueError(error)

        if site_item.admin_mode:
            if site_item.admin_mode == SiteItem.AdminMode.ContentOnly and site_item.user_quota:
                error = "You cannot set admin_mode to ContentOnly and also set a user quota"
                raise ValueError(error)

        url = f"{self.baseurl}/{site_item.id}"
        update_req = RequestFactory.Site.update_req(site_item, self.parent_srv)
        server_response = self.put_request(url, update_req)
        logger.info(f"Updated site item (ID: {site_item.id})")
        update_site = copy.copy(site_item)
        return update_site._parse_common_tags(server_response.content, self.parent_srv.namespace)

    # Delete 1 site object
    @api(version="2.0")
    def delete(self, site_id: str) -> None:
        if not site_id:
            error = "Site ID undefined."
            raise ValueError(error)
        url = f"{self.baseurl}/{site_id}"
        if not site_id == self.parent_srv.site_id:
            error = "You can only delete the site you are currently authenticated for"
            raise ValueError(error)
        self.delete_request(url)
        self.parent_srv._clear_auth()
        logger.info(f"Deleted single site (ID: {site_id}) and signed out")

    # Create new site
    @api(version="2.0")
    def create(self, site_item: SiteItem) -> SiteItem:
        if site_item.admin_mode:
            if site_item.admin_mode == SiteItem.AdminMode.ContentOnly and site_item.user_quota:
                error = "You cannot set admin_mode to ContentOnly and also set a user quota"
                raise ValueError(error)

        url = self.baseurl
        create_req = RequestFactory.Site.create_req(site_item, self.parent_srv)
        server_response = self.post_request(url, create_req)
        new_site = SiteItem.from_response(server_response.content, self.parent_srv.namespace)[0]
        logger.info(f"Created new site (ID: {new_site.id})")
        return new_site

    @api(version="3.5")
    def encrypt_extracts(self, site_id: str) -> None:
        if not site_id:
            error = "Site ID undefined."
            raise ValueError(error)
        url = f"{self.baseurl}/{site_id}/encrypt-extracts"
        empty_req = RequestFactory.Empty.empty_req()
        self.post_request(url, empty_req)

    @api(version="3.5")
    def decrypt_extracts(self, site_id: str) -> None:
        if not site_id:
            error = "Site ID undefined."
            raise ValueError(error)
        url = f"{self.baseurl}/{site_id}/decrypt-extracts"
        empty_req = RequestFactory.Empty.empty_req()
        self.post_request(url, empty_req)

    @api(version="3.5")
    def re_encrypt_extracts(self, site_id: str) -> None:
        if not site_id:
            error = "Site ID undefined."
            raise ValueError(error)
        url = f"{self.baseurl}/{site_id}/reencrypt-extracts"

        empty_req = RequestFactory.Empty.empty_req()
        self.post_request(url, empty_req)
